
from decimal import Decimal
from core.models import CoursePOContribution
from core.services.po_calculator import calculate_course_po_achievement

def aggregate_course_po_results(course_results):
    """Combine course-level PO results using contribution weights."""

    weighted_sum = Decimal("0")
    total_weight = Decimal("0")
    effective_weight_total = Decimal("0")
    all_complete = True

    for result, weight in course_results:
        total_weight += weight
        if result["status"] != "complete":
            all_complete = False
        # Missing evidence must not count as a zero score.
        if result["score"] is None:
            continue

        coverage_fraction = result["coverage"] / Decimal("100")
        effective_weight = weight * coverage_fraction

        weighted_sum += result["score"] * effective_weight
        effective_weight_total += effective_weight

    if effective_weight_total == 0:
        return {
            "score": None,
            "coverage": Decimal("0"),
            "status": "no_data",
        }

    score = weighted_sum / effective_weight_total
    coverage = (
        effective_weight_total / total_weight * Decimal("100")
    )

    return {
        "score": score,
        "coverage": coverage,
        "status": "complete" if all_complete else "provisional",
    }
def calculate_student_po_achievement(student, program_outcome):
    """Calculate one student's PO result across contributing courses."""

    if student.program_id != program_outcome.framework.program_id:
        raise ValueError(
            "The student and PO framework must belong "
            "to the same program."
        )

    enrollments = student.enrollments.filter(
        status="active",
        offering__po_framework_id=program_outcome.framework_id,
    ).select_related(
        "offering__course",
        "offering__curriculum",
        "offering__po_framework",
    ).order_by("offering__course__code", "pk")

    weights = dict(
        CoursePOContribution.objects.filter(
            program_outcome=program_outcome,
        ).values_list("curriculum_id", "weight")
    )

    course_results = []
    courses = []
    unmapped_enrollments = []
    seen_courses = set()

    for enrollment in enrollments:
        offering = enrollment.offering
        weight = weights.get(offering.curriculum_id)

        if weight is None:
            unmapped_enrollments.append(enrollment)
            continue

        if offering.course_id in seen_courses:
            raise ValueError(
                "Repeated course enrollments need "
                "an explicit selection policy."
            )

        seen_courses.add(offering.course_id)

        result = calculate_course_po_achievement(
            enrollment,
            program_outcome,
        )

        course_results.append((result, Decimal(weight)))

        courses.append({
            "enrollment": enrollment,
            "weight": weight,
            **result,
        })

    return {
        **aggregate_course_po_results(course_results),
        "courses": courses,
        "unmapped_enrollments": unmapped_enrollments,
    }