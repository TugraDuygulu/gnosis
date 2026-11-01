"""Native student registration and narrowly scoped active enrollment."""

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Exists, F, OuterRef

from core.models import CourseOffering, Enrollment, Program, Student


class StudentRegistrationForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ("full_name", "student_number", "program")
        labels = {"full_name": "Full name", "student_number": "Student number"}
        help_texts = {"student_number": "Use the unique student number, including any leading zeros."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["program"].queryset = Program.objects.order_by("code", "pk")


def available_offerings(student):
    existing = Enrollment.objects.filter(student=student, offering_id=OuterRef("pk"))
    repeated = Enrollment.objects.filter(
        student=student, status="active",
        offering__course_id=OuterRef("course_id"),
        offering__po_framework_id=OuterRef("po_framework_id"),
    )
    return CourseOffering.objects.filter(
        po_framework__program_id=student.program_id,
        curriculum__course_id=F("course_id"),
    ).annotate(
        already_enrolled=Exists(existing), repeated_course=Exists(repeated),
    ).filter(already_enrolled=False, repeated_course=False).select_related(
        "course", "curriculum", "po_framework",
    ).order_by("-year", "term", "course__code", "section", "pk")


class OfferingChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return (f"{obj} · {obj.course.title} · Framework v{obj.po_framework.version_number} "
                f"· {obj.status}")


class StudentEnrollmentForm(forms.Form):
    offering = OfferingChoiceField(
        queryset=CourseOffering.objects.none(), label="Course offering",
        error_messages={"invalid_choice": "Choose an available offering. Existing enrollments, "
                        "incompatible programs and repeated active courses cannot be added."},
    )

    def __init__(self, student, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["offering"].queryset = available_offerings(student)


@transaction.atomic
def enroll_student(student_id, offering_id):
    # Serialize native intake for the same student; DB uniqueness remains the
    # final duplicate guard. SQLite lock conflicts are handled by the view.
    student = Student.objects.select_for_update().get(pk=student_id)
    CourseOffering.objects.select_for_update().get(pk=offering_id)
    if not available_offerings(student).filter(pk=offering_id).exists():
        raise ValidationError(
            "This offering is no longer available for this student. "
            "Reload and review their current enrollments and program."
        )
    return Enrollment.objects.create(student=student, offering_id=offering_id, status="active")
