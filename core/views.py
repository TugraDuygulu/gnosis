from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render

from core.models import (
    Enrollment,
    LearningOutcome,
    ProgramOutcome,
    Student,
    POFramework,
    Grade,
    LOPOMapping,
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