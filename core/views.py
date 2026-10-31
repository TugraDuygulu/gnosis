from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.grade_editor import (
    EnrollmentGradeForm, revision_token, save_grades, snapshot, STALE_MESSAGE,
)

from core.models import (
    Enrollment,
    LearningOutcome,
    ProgramOutcome,
    Student,
    POFramework,
    Grade,
    LOPOMapping,
    CourseOffering,
)
from core.services.lo_calculator import calculate_lo_achievement
from core.services.po_calculator import calculate_course_po_achievement
from core.services.student_po_calculator import (
    calculate_student_po_achievement,
)

@staff_member_required
def enrollment_outcomes(request, enrollment_id):
    enrollment = get_object_or_404(
        Enrollment,
        pk=enrollment_id,
    )

    offering = enrollment.offering
    grades_by_assessment = {
        grade.assessment_id: grade
        for grade in Grade.objects.filter(enrollment=enrollment)
    }

    assessment_results = []
    for assessment in offering.assessments.order_by("pk"):
        grade = grades_by_assessment.get(assessment.pk)

        assessment_results.append({
            "assessment": assessment,
            "score": grade.score if grade is not None else None,
            "mappings": assessment.lo_mappings.select_related(
                "learning_outcome"
            ).order_by("learning_outcome__pk"),
        })

    lo_results = []
    for lo in LearningOutcome.objects.filter(
        curriculum=offering.curriculum
    ):
        result = calculate_lo_achievement(enrollment, lo)
        lo_results.append({
            "outcome": lo,
            **result,
        })

    po_results = []
    if offering.po_framework:
        for po in ProgramOutcome.objects.filter(
            framework=offering.po_framework
        ):
            result = calculate_course_po_achievement(enrollment, po)
            po_results.append({
                "outcome": po,
                **result,
                "mappings": LOPOMapping.objects.filter(
                    program_outcome=po,
                    learning_outcome__curriculum=offering.curriculum,
                ).select_related(
                    "learning_outcome"
                ).order_by("learning_outcome__pk"),
            })
    return render(request, "core/enrollment_outcomes.html", {
        "enrollment": enrollment,
        "lo_results": lo_results,
        "po_results": po_results,
        "assessment_results": assessment_results,
    })
@staff_member_required
def student_outcomes(request, student_id, framework_id):
    student = get_object_or_404(
        Student.objects.select_related("program"),
        pk=student_id,
    )
    framework = get_object_or_404(
        POFramework,
        pk=framework_id,
        program=student.program,
    )

    enrollments = student.enrollments.filter(
        status="active",
        offering__po_framework=framework,
    ).select_related("offering__course")

    po_results = []
    outcomes = sorted(
        framework.program_outcomes.all(),
        key=lambda outcome: (len(outcome.code), outcome.code),
    )
    for po in outcomes:
        row = {"outcome": po}

        try:
            row.update(
                calculate_student_po_achievement(student, po)
            )
        except ValueError as error:
            row["error"] = str(error)

        po_results.append(row)

    return render(request, "core/student_outcomes.html", {
        "student": student,
        "framework": framework,
        "enrollments": enrollments,
        "po_results": po_results,
    })
@staff_member_required
def student_list(request):
    students = (
        Student.objects
        .select_related("program")
        .prefetch_related("program__po_frameworks")
        .order_by("full_name", "pk")
    )

    return render(request, "core/student_list.html", {
        "students": students,
    })


@staff_member_required
@permission_required("core.change_grade", raise_exception=True)
@require_http_methods(["GET", "POST"])
def enrollment_grade_editor(request, enrollment_id):
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("student", "offering__course"),
        pk=enrollment_id,
    )
    assessments, grades, revision = snapshot(enrollment)
    form = EnrollmentGradeForm(
        assessments, grades,
        request.POST if request.method == "POST" else None,
        initial={"revision": revision_token(enrollment, request.user, revision)},
    )
    if request.method == "POST" and form.is_valid():
        try:
            save_grades(enrollment.pk, request.user, form)
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            form.add_error(None, STALE_MESSAGE)
        except OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            form.add_error(None, "Another save is in progress. Nothing was saved. "
                           "Reload grades and try again.")
        else:
            messages.success(request, "Grades saved. Outcome results are up to date.")
            return redirect("enrollment_outcomes", enrollment_id=enrollment.pk)
    return render(request, "core/enrollment_grade_editor.html", {
        "enrollment": enrollment,
        "form": form,
        "has_assessments": bool(assessments),
    })


@staff_member_required
@require_http_methods(["GET"])
def course_list(request):
    query = request.GET.get("q", "").strip()
    offerings = CourseOffering.objects.select_related(
        "course", "instructor", "po_framework__program",
    ).annotate(
        enrollment_count=Count("enrollments"),
        active_count=Count("enrollments", filter=Q(enrollments__status="active")),
    ).order_by("-year", "term", "course__code", "section", "pk")
    if query:
        match = (
            Q(course__code__icontains=query) | Q(course__title__icontains=query)
            | Q(instructor__full_name__icontains=query)
            | Q(term__icontains=query) | Q(section__icontains=query)
        )
        if query.isdecimal() and len(query) <= 4:
            match |= Q(year=int(query))
        offerings = offerings.filter(match)
    return render(request, "core/course_list.html", {
        "offerings": offerings,
        "query": query,
    })


@staff_member_required
@require_http_methods(["GET"])
def offering_detail(request, offering_id):
    offering = get_object_or_404(
        CourseOffering.objects.select_related(
            "course", "instructor", "curriculum", "po_framework__program",
        ),
        pk=offering_id,
    )
    enrollments = offering.enrollments.select_related(
        "student__program",
    ).order_by("student__full_name", "student__student_number", "pk")
    return render(request, "core/offering_detail.html", {
        "offering": offering,
        "enrollments": enrollments,
    })
