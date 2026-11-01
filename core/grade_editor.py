"""One enrollment's grade form and transactional, optimistic updates."""

import hashlib
import json
from decimal import Decimal

from django import forms
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Assessment, CourseOffering, Enrollment, Grade
from core.grade_history import grade_state, record_grade_change


SALT = "gnosis.enrollment-grade-editor.v1"
STALE_MESSAGE = (
    "Grades or course settings changed since you opened this page. "
    "Nothing was saved. Reload grades and review the latest values."
)


def snapshot(enrollment, *, lock=False):
    assessments = Assessment.objects.filter(
        offering_id=enrollment.offering_id
    ).order_by("pk")
    grades = Grade.objects.filter(enrollment=enrollment).order_by("pk")
    if lock:
        assessments = assessments.select_for_update()
        grades = grades.select_for_update()
    assessments = list(assessments)
    grades = {grade.assessment_id: grade for grade in grades}
    payload = {
        "enrollment": [enrollment.pk, enrollment.student_id,
                       enrollment.offering_id, enrollment.status],
        "assessments": [(a.pk, a.name, str(a.max_score)) for a in assessments],
        "grades": [(g.pk, g.assessment_id, str(g.score)) for g in grades.values()],
    }
    revision = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
    return assessments, grades, revision


class EnrollmentGradeForm(forms.Form):
    revision = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, assessments, grades, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for assessment in assessments:
            grade = grades.get(assessment.pk)
            self.fields[f"score_{assessment.pk}"] = forms.DecimalField(
                label=assessment.name,
                required=False,
                min_value=Decimal("0"),
                max_value=assessment.max_score,
                max_digits=7,
                decimal_places=2,
                initial=grade.score if grade else None,
                help_text=f"Out of {assessment.max_score}. Leave blank if ungraded.",
                widget=forms.NumberInput(attrs={"step": "0.01"}),
            )

    def clean(self):
        cleaned = super().clean()
        expected = set(self.fields)
        submitted = {key for key in self.data if key.startswith("score_")}
        if submitted != expected - {"revision"} or any(
            len(self.data.getlist(key)) != 1 for key in expected
        ):
            raise ValidationError(
                "The submitted form is incomplete or contains unexpected grades. "
                "Nothing was saved. Reload grades and try again."
            )
        return cleaned


def revision_token(enrollment, user, revision):
    return signing.dumps(
        [enrollment.pk, user.pk, revision], salt=SALT
    )


@transaction.atomic
def save_grades(enrollment_id, user, form):
    # Parent locks serialize this editor on databases supporting row locks.
    # SQLite instead rejects competing snapshot writes; the view handles that.
    enrollment = Enrollment.objects.get(pk=enrollment_id)
    CourseOffering.objects.select_for_update().get(pk=enrollment.offering_id)
    enrollment = Enrollment.objects.select_for_update().get(pk=enrollment_id)
    assessments, grades, revision = snapshot(enrollment, lock=True)
    try:
        expected = signing.loads(form.cleaned_data["revision"], salt=SALT, max_age=7200)
    except signing.BadSignature:
        raise ValidationError(
            "This editing session is invalid or expired. Nothing was saved. "
            "Reload grades before trying again."
        )
    if expected != [enrollment.pk, user.pk, revision]:
        raise ValidationError(STALE_MESSAGE)

    for assessment in assessments:
        score = form.cleaned_data[f"score_{assessment.pk}"]
        grade = grades.get(assessment.pk)
        if grade is None:
            if score is not None:
                grade = Grade.objects.create(
                    enrollment=enrollment, assessment=assessment, score=score
                )
                record_grade_change(user, grade, None, source="native editor", operation="create")
        elif score != grade.score:
            before = grade_state(grade)
            # Compare-and-swap also detects an intervening Admin grade edit.
            updated = Grade.objects.filter(pk=grade.pk, score=grade.score).update(
                score=score
            )
            if updated != 1:
                raise ValidationError(STALE_MESSAGE)
            grade.score = score
            record_grade_change(user, grade, before, source="native editor", operation="change")
