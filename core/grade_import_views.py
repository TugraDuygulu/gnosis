"""Upload, preview and confirmation pages for a class grade CSV import (#43).

``core.grade_import`` validates and writes; these views only show its result.
The previewed file goes back with the confirmation form (base64 in a hidden
field), so the server never stores an upload between the two steps.
"""

import base64
import binascii
import csv
import io
import re

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import floatformat
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from core.access import INSTRUCTOR, offerings_for, require_roles
from core.grade_import import ASSESSMENT_ID, HEADER, MAX_BYTES, MAX_ROWS, confirm_grades, preview_grades

# Base64 length of the largest accepted file; anything longer is refused undecoded.
MAX_ENCODED = (MAX_BYTES + 2) // 3 * 4
SIZE_LIMIT = f"{MAX_BYTES / 1_000_000:g}\u00a0MB"
# A spreadsheet runs a cell that starts with one of these as a formula (OWASP CSV
# injection list, plus the full-width forms). Templates never write such a cell.
FORMULA_START = ("=", "+", "-", "@", "\t", "\r", "＝", "＋", "－", "＠")

FILE_PROBLEMS = {
    "too_large": f"The file is larger than {SIZE_LIMIT}. Split it into smaller files.",
    "encoding": "The file isn’t saved as UTF-8 text. In Excel, save it as “CSV UTF-8 (Comma delimited)”.",
    "invalid_header": "The first line must be exactly student_number,assessment_id,score.",
    "too_many_rows": f"The file has more than {MAX_ROWS} rows. Split it into smaller files.",
    "malformed_csv": "A line can’t be read as CSV. Check for a quotation mark that isn’t closed.",
    "empty": "The file has the header line but no grade rows.",
}
SEMICOLON_HINT = ("The file uses semicolons between columns. Save it again with commas, for example "
                  "as “CSV UTF-8 (Comma delimited)” in Excel, and use a dot for decimals.")
REJECTED = {
    "stale": "Nothing was saved. Grades or class settings changed after your preview. "
             "The preview below shows the current grades: check it and confirm again.",
    "expired": "Nothing was saved. The preview was more than two hours old. "
               "The preview below is new: check it and confirm again.",
    "busy": "Nothing was saved. Another save was in progress. "
            "The preview below shows the current grades: check it and confirm again.",
    "replayed": "Nothing was saved this time. This preview was already confirmed, so its grades "
                "may already be in the grade book. Check the grade book before importing again.",
    "invalid_token": "Nothing was saved. The confirmation didn’t match the file you previewed. "
                     "Choose the file again.",
}


class UploadForm(forms.Form):
    file = forms.FileField(
        label="CSV file",
        help_text=f"UTF-8, comma-separated, at most {MAX_ROWS} rows and {SIZE_LIMIT}.",
        error_messages={
            "required": "Choose a CSV file to preview.",
            "missing": "Choose a CSV file to preview.",
            "invalid": "Choose a CSV file to preview.",
            "empty": "The selected file is empty. Choose the CSV file with your grades.",
        },
        widget=forms.FileInput(attrs={"accept": ".csv,text/csv"}),
    )


def _shown(value, limit=40):
    """A cell short enough to quote back on the page."""
    return value if len(value) <= limit else value[:limit - 1] + "…"


def _cells_by_line(data):
    """Each data line's cells, read like the service reads them. Display only."""
    cells = {}
    try:
        reader = csv.reader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
        next(reader, None)
        while len(cells) <= MAX_ROWS:
            line = reader.line_num + 1
            row = next(reader, None)
            if row is None:
                break
            cells[line] = row
    except (UnicodeDecodeError, csv.Error):
        pass
    return cells


def _row_problem(code, cells, assessments):
    identifier = (cells + ["", ""])[1]
    # The service's own ID rule, so an ID thousands of digits long is never converted.
    assessment = assessments.get(int(identifier)) if ASSESSMENT_ID.fullmatch(identifier) else None
    number, identifier, raw = (_shown(cell) for cell in (cells + ["", "", ""])[:3])
    if code == "column_count":
        return f"This line has {len(cells)} values. It needs 3: student number, assessment ID and score."
    if code == "duplicate":
        return "This student and assessment are already on an earlier line. Keep only one of them."
    if code == "unknown_student":
        return f"No student numbered “{number}” is in this class. Check for missing leading zeros."
    if code == "invalid_id":
        return f"“{identifier}” isn’t an assessment ID. Use an ID from the assessment list."
    if code == "unknown_assessment":
        return f"Assessment {identifier} isn’t part of this class."
    if code == "min_value":
        return "Scores can’t be negative."
    if code == "max_value" and assessment:
        return f"{raw} is above the maximum of {floatformat(assessment.max_score, '-2')} for {assessment.name}."
    if code == "max_decimal_places":
        return f"“{raw}” has more than 2 decimal places."
    if code in ("max_digits", "max_whole_digits"):
        return f"“{raw}” has too many digits."
    return f"“{raw}” isn’t a score. Use digits with a dot for decimals, like 42.5."


def _kind(row):
    if row.action == "set":
        return "new" if row.previous is None else "change"
    return "blank" if row.proposed is None else "same"


def _preview(request, offering, data, filename):
    """Run the read-only preview and shape it for the page."""
    preview = preview_grades(user=request.user, offering_id=offering.pk, upload=io.BytesIO(data))
    assessments = {a.pk: a for a in offering.assessments.all()}
    students = {e.pk: e.student for e in offering.enrollments.select_related("student")}
    file_problems, by_line = [], {}
    cells = _cells_by_line(data) if preview.errors else {}
    for problem in preview.errors:
        if problem.field in ("file", "header"):
            message = FILE_PROBLEMS.get(problem.code, "The file can’t be read.")
            if problem.code == "invalid_header" and b";" in data.split(b"\n", 1)[0]:
                message = SEMICOLON_HINT
            file_problems.append({"line": problem.line, "message": message})
        else:
            line_cells = cells.get(problem.line, [])
            entry = by_line.setdefault(problem.line, {
                "line": problem.line, "cells": [_shown(cell) for cell in line_cells], "messages": [],
            })
            entry["messages"].append(_row_problem(problem.code, line_cells, assessments))
    rows = [{
        "line": row.line, "number": row.student_number, "student": students.get(row.enrollment_id),
        "assessment": assessments.get(row.assessment_id), "assessment_id": row.assessment_id,
        "previous": row.previous, "proposed": row.proposed, "kind": _kind(row),
    } for row in preview.rows]
    kinds = [row["kind"] for row in rows]
    changes = kinds.count("new") + kinds.count("change")
    return {
        "result": {
            "filename": filename, "rows": rows, "file_problems": file_problems,
            "line_problems": sorted(by_line.values(), key=lambda entry: entry["line"]),
            "changes": changes, "new": kinds.count("new"),
            "unchanged": kinds.count("blank") + kinds.count("same"),
            "blank": kinds.count("blank"), "same": kinds.count("same"),
            "token": preview.confirmation_token,
            "content": base64.b64encode(data).decode() if preview.confirmation_token and changes else "",
        },
    }


def _template_students(offering):
    """Students a template lists, and those left out because a spreadsheet would run their number."""
    listed, left_out = [], []
    for enrollment in offering.enrollments.select_related("student").order_by(
        "student__full_name", "student__student_number", "pk",
    ):
        student = enrollment.student
        (left_out if student.student_number.startswith(FORMULA_START) else listed).append(student)
    return listed, left_out


def _parts(count):
    """(part, first row, last row) for each file of a template, at most MAX_ROWS rows each."""
    return [(start // MAX_ROWS + 1, start + 1, min(start + MAX_ROWS, count)) for start in range(0, count, MAX_ROWS)]


def _render(request, offering, context):
    assessments = list(offering.assessments.order_by("pk"))
    listed, left_out = _template_students(offering)
    return render(request, "core/offering_grade_import.html", {
        **context, "offering": offering, "assessments": assessments,
        "student_count": len(listed) + len(left_out), "left_out": left_out,
        "student_parts": _parts(len(listed)), "cell_count": len(listed) * len(assessments),
        "max_rows": MAX_ROWS, "size_limit": SIZE_LIMIT,
    })


def _confirm(request, offering, context):
    filename = request.POST.get("filename", "")[:120]
    content = request.POST.get("content", "")
    data = None
    if len(content) <= MAX_ENCODED:
        try:
            data = base64.b64decode(content, validate=True)
        except (binascii.Error, ValueError):
            pass
    reason = "invalid_token"
    if data is not None:
        try:
            changed = confirm_grades(user=request.user, offering_id=offering.pk,
                                     upload=io.BytesIO(data), token=request.POST.get("token"))
        except ValidationError as error:
            # The shared grade writer raises an uncoded error when a cell changed meanwhile.
            reason = error.code if error.code in REJECTED else "stale"
        except IntegrityError:
            reason = "stale"
        except OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            reason = "busy"
        else:
            if changed:
                messages.success(request, f"Import saved: {changed} grade{'s' if changed != 1 else ''} "
                                          f"changed from {filename or 'the CSV file'}. Grade history lists "
                                          "each change as “CSV import”.")
            else:
                messages.success(request, "No grades changed. Every score in the file was blank or already the same.")
            return redirect("offering_gradebook", offering_id=offering.pk)
    context["rejected"] = REJECTED[reason]
    if reason in ("stale", "expired", "busy"):
        context.update(_preview(request, offering, data, filename))
    return _render(request, offering, context)


@require_roles(INSTRUCTOR)
@require_http_methods(["GET", "POST"])
def grade_import(request, offering_id):
    """Choose a CSV, preview every row, then confirm the exact previewed file."""
    offering = get_object_or_404(
        offerings_for(request).select_related("course", "instructor"), pk=offering_id,
    )
    context = {"form": UploadForm(label_suffix="")}
    if request.method == "POST" and "token" in request.POST:
        return _confirm(request, offering, context)
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES, label_suffix="")
        context["form"] = form
        if form.is_valid():
            upload = form.cleaned_data["file"]
            context.update(_preview(request, offering, upload.read(MAX_BYTES + 1), upload.name[:120]))
    return _render(request, offering, context)


@require_roles(INSTRUCTOR)
@require_http_methods(["GET"])
def grade_import_template(request, offering_id):
    """A CSV of this class's students with blank scores, for one or every assessment.

    A template longer than the import's row limit comes in parts (?part=2), so every
    file it gives can be imported as it is.
    """
    offering = get_object_or_404(offerings_for(request).select_related("course"), pk=offering_id)
    assessments = list(offering.assessments.order_by("pk"))
    name = slugify(offering.course.code) or "class"
    selected = request.GET.get("assessment")
    if selected is not None:
        assessments = [a for a in assessments if str(a.pk) == selected]
        if not assessments:
            raise Http404
        name += f"-{slugify(assessments[0].name) or assessments[0].pk}"
    listed, _ = _template_students(offering)
    rows = [(student.student_number, assessment.pk) for student in listed for assessment in assessments]
    parts = len(_parts(len(rows)))
    part = request.GET.get("part", "1")
    if not re.fullmatch(r"[1-9][0-9]{0,5}", part) or int(part) > max(parts, 1):
        raise Http404
    part = int(part)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    suffix = f"-part-{part}" if parts > 1 else ""
    response["Content-Disposition"] = f'attachment; filename="{name}-grades{suffix}.csv"'
    response.write("\ufeff")  # BOM, so Excel opens the file as UTF-8
    writer = csv.writer(response, lineterminator="\r\n")
    writer.writerow(HEADER)
    start = (part - 1) * MAX_ROWS
    for number, assessment in rows[start:start + MAX_ROWS]:
        writer.writerow([number, assessment, ""])
    return response
