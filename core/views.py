from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render

from core.models import (
    Enrollment,
    LearningOutcome,
    ProgramOutcome,
)
from core.services.lo_calculator import calculate_lo_achievement
from core.services.po_calculator import calculate_course_po_achievement


@staff_member_required
def enrollment_outcomes(request, enrollment_id):
    enrollment = get_object_or_404(
        Enrollment,
        pk=enrollment_id,
    )

    offering = enrollment.offering

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
            })

    return render(request, "core/enrollment_outcomes.html", {
        "enrollment": enrollment,
        "lo_results": lo_results,
        "po_results": po_results,
    })