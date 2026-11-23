"""Read-only, instructor-scoped grade import preview for one offering."""

import csv
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError

from core.access import INSTRUCTOR, role_for
from core.models import Assessment, CourseOffering, Enrollment, Grade

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


def preview_grades(*, user, offering_id, upload):
    """Read a binary stream from its beginning. Caller owns its lifecycle."""
    if role_for(user) != INSTRUCTOR or not CourseOffering.objects.filter(
        pk=offering_id, instructor__user_id=user.pk
    ).exists():
        raise PermissionDenied

    data = upload.read(MAX_BYTES + 1)
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
    enrollments = dict(Enrollment.objects.filter(
        offering_id=offering_id, student__student_number__in=numbers
    ).values_list("student__student_number", "pk"))
    maxima = dict(Assessment.objects.filter(
        offering_id=offering_id, pk__in=ids
    ).values_list("pk", "max_score"))
    scores = {(e, a): score for e, a, score in Grade.objects.filter(
        enrollment_id__in=enrollments.values(), assessment_id__in=maxima
    ).values_list("enrollment_id", "assessment_id", "score")}

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
        if assessment not in maxima:
            result.errors.append(Problem(line, "assessment_id", "unknown_assessment"))
            continue
        value = None
        if raw:
            if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", raw):
                result.errors.append(Problem(line, "score", "invalid_decimal"))
                continue
            try:
                value = forms.DecimalField(min_value=0, max_value=maxima[assessment],
                                           max_digits=7, decimal_places=2).clean(raw)
            except ValidationError as error:
                result.errors.append(Problem(line, "score", error.error_list[0].code))
                continue
        if len(result.errors) == first_error:
            previous = scores.get((enrollment, assessment))
            action = "keep" if value is None or value == previous else "set"
            result.rows.append(PreviewRow(line, number, enrollment, assessment,
                                          previous, value, action))
    return result
