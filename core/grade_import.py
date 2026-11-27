"""Instructor-scoped CSV preview and atomic confirmation for one offering."""

import csv
import hashlib
import json
import uuid
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal

from django import forms
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.core.exceptions import PermissionDenied, ValidationError

from core.access import INSTRUCTOR, role_for
from core.grade_editor import write_grade
from core.grade_history import history_key
from core.models import Assessment, CourseOffering, Enrollment, Grade, GradeImportReceipt

MAX_BYTES = 1_000_000
MAX_ROWS = 100
ASSESSMENT_ID = re.compile(r"[1-9][0-9]{0,18}")
HEADER = ["student_number", "assessment_id", "score"]


@dataclass(frozen=True)
class Problem:
    line: int | None
    field: str
    code: str


@dataclass(frozen=True)
class PreviewRow:
    line: int
    student_number: str
    enrollment_id: int
    assessment_id: int
    previous: Decimal | None
    proposed: Decimal | None
    action: str


@dataclass
class Preview:
    rows: list[PreviewRow] = field(default_factory=list)
    errors: list[Problem] = field(default_factory=list)
    confirmation_token: str | None = None
    _state: str = field(default="", repr=False, compare=False)


def preview_grades(*, user, offering_id, upload):
    """Read a binary stream from its beginning. Caller owns its lifecycle."""
    actor, offering = _assigned_actor(user, offering_id)
    data = upload.read(MAX_BYTES + 1)
    preview = _validate(data, offering)
    if not preview.errors:
        payload = {
            "actor": actor.pk, "offering": offering_id, "nonce": uuid.uuid4().hex,
            "file": hashlib.sha256(data).hexdigest(), "state": preview._state,
        }
        preview.confirmation_token = _signer(actor).sign_object(payload)
    return preview


def _assigned_actor(user, offering_id, *, lock=False):
    if not user.is_authenticated:
        raise PermissionDenied
    accounts = get_user_model().objects
    offerings = CourseOffering.objects
    if lock:
        accounts = accounts.select_for_update()
        offerings = offerings.select_for_update()
    actor = accounts.filter(pk=user.pk).first()
    if actor is None or role_for(actor) != INSTRUCTOR:
        raise PermissionDenied
    offering = offerings.filter(pk=offering_id, instructor__user_id=actor.pk).first()
    if offering is None:
        raise PermissionDenied
    return actor, offering


def _signer(actor):
    # An account-specific secret also invalidates tokens after a password change.
    return signing.TimestampSigner(key=actor.get_session_auth_hash(),
                                   salt="gnosis.grade-import.v1", fallback_keys=[])


def _validate(data, offering, *, changes=None):
    lock = changes is not None
    if len(data) > MAX_BYTES:
        return Preview(errors=[Problem(None, "file", "too_large")])
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return Preview(errors=[Problem(None, "file", "encoding")])

    reader = csv.reader(io.StringIO(content, newline=""), strict=True)
    result = Preview()
    records = []
    line = 1
    try:
        if next(reader, None) != HEADER:
            return Preview(errors=[Problem(1, "header", "invalid_header")])
        while True:
            line = reader.line_num + 1
            cells = next(reader, None)
            if cells is None:
                break
            if len(records) == MAX_ROWS:
                return Preview(errors=[Problem(line, "file", "too_many_rows")])
            records.append((line, cells))
    except csv.Error:
        return Preview(errors=[Problem(line, "file", "malformed_csv")])
    if not records:
        return Preview(errors=[Problem(None, "file", "empty")])

    numbers = {cells[0] for _, cells in records if len(cells) == 3}
    ids = {int(cells[1]) for _, cells in records if len(cells) == 3
           and ASSESSMENT_ID.fullmatch(cells[1]) and int(cells[1]) <= 2**63 - 1}
    roster = Enrollment.objects.filter(offering_id=offering.pk, student__student_number__in=numbers)
    assessments = Assessment.objects.filter(offering_id=offering.pk, pk__in=ids)
    if lock:
        roster = roster.select_for_update()
        assessments = assessments.select_for_update()
    enrollments = {e.student.student_number: e for e in
                   roster.select_related("student").order_by("pk")}
    assessments = {a.pk: a for a in assessments.order_by("pk")}
    grades = Grade.objects.filter(enrollment_id__in=[e.pk for e in enrollments.values()],
                                 assessment_id__in=assessments)
    if lock:
        grades = grades.select_for_update()
    grades = {(g.enrollment_id, g.assessment_id): g for g in grades.order_by("pk")}
    # Also catch an audited edit that changed a score and then restored it.
    keys = [history_key(e.pk) for e in enrollments.values()]
    last_events = list(LogEntry.objects.filter(object_repr__in=keys).values("object_repr")
                       .annotate(last=Max("pk")).order_by("object_repr")
                       .values_list("object_repr", "last"))
    revision = [last_events, [offering.pk, offering.course_id, offering.curriculum_id,
                 offering.instructor_id, offering.year, offering.term, offering.section,
                 offering.status, offering.po_framework_id]]

    seen = set()
    for line, cells in records:
        if len(cells) != 3:
            result.errors.append(Problem(line, "row", "column_count"))
            continue
        number, identifier, raw = cells
        first_error = len(result.errors)
        enrollment = enrollments.get(number)
        if enrollment is None:
            result.errors.append(Problem(line, "student_number", "unknown_student"))
        key = (number, identifier)
        if key in seen:
            result.errors.append(Problem(line, "row", "duplicate"))
        seen.add(key)
        if not ASSESSMENT_ID.fullmatch(identifier) or int(identifier) > 2**63 - 1:
            result.errors.append(Problem(line, "assessment_id", "invalid_id"))
            continue
        assessment = int(identifier)
        if assessment not in assessments:
            result.errors.append(Problem(line, "assessment_id", "unknown_assessment"))
            continue
        value = None
        if raw:
            if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", raw):
                result.errors.append(Problem(line, "score", "invalid_decimal"))
                continue
            try:
                value = forms.DecimalField(min_value=0, max_value=assessments[assessment].max_score,
                                           max_digits=7, decimal_places=2).clean(raw)
            except ValidationError as error:
                result.errors.append(Problem(line, "score", error.error_list[0].code))
                continue
        if len(result.errors) == first_error:
            item = assessments[assessment]
            grade = grades.get((enrollment.pk, assessment))
            previous = grade.score if grade else None
            revision.append([number, enrollment.pk, enrollment.student_id, enrollment.status,
                             item.pk, item.name, str(item.max_score), str(item.course_grade_weight),
                             grade.pk if grade else None, str(previous)])
            action = "keep" if value is None or value == previous else "set"
            if changes is not None and action == "set":
                changes.append((enrollment, item, grade, value))
            result.rows.append(PreviewRow(line, number, enrollment.pk, assessment,
                                          previous, value, action))
    result._state = hashlib.sha256(json.dumps(revision).encode()).hexdigest()
    return result


def confirm_grades(*, user, offering_id, upload, token):
    """Confirm the same file and return the number of changed grade cells."""
    actor, _ = _assigned_actor(user, offering_id)
    if not isinstance(token, str) or len(token) > 2048:
        raise ValidationError("Invalid confirmation.", code="invalid_token")
    try:
        payload = _signer(actor).unsign_object(token, max_age=7200)
    except signing.SignatureExpired as exc:
        raise ValidationError("Preview expired.", code="expired") from exc
    except signing.BadSignature as exc:
        raise ValidationError("Invalid confirmation.", code="invalid_token") from exc
    data = upload.read(MAX_BYTES + 1)
    if (payload["actor"] != actor.pk or payload["offering"] != offering_id
            or len(data) > MAX_BYTES or payload["file"] != hashlib.sha256(data).hexdigest()):
        raise ValidationError("Preview does not match this request.", code="invalid_token")

    with transaction.atomic():
        # First SQL operation is a write. SQLite serializes writers from here;
        # the unique nonce also covers successful all-unchanged confirmations.
        try:
            with transaction.atomic():
                GradeImportReceipt.objects.create(nonce=payload["nonce"])
        except IntegrityError as exc:
            if GradeImportReceipt.objects.filter(nonce=payload["nonce"]).exists():
                raise ValidationError("Preview already confirmed.", code="replayed") from exc
            raise
        current_actor, offering = _assigned_actor(user, offering_id, lock=True)
        if current_actor.password != actor.password:
            raise ValidationError("Account changed. Preview again.", code="stale")
        changes = []
        current = _validate(data, offering, changes=changes)
        if current.errors or current._state != payload["state"]:
            raise ValidationError("Grades or settings changed. Preview again.", code="stale")
        for enrollment, assessment, grade, value in changes:
            write_grade(enrollment, assessment, grade, value, current_actor, source="CSV import")
        return len(changes)
