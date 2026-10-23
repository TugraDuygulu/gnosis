from decimal import Decimal

from core.models import AssessmentLOMapping, Grade


def calculate_lo_achievement(enrollment, learning_outcome):
    """
    Calculate a student's achievement for one Learning Outcome.

    Returns:
        score: Provisional weighted achievement, or None.
        coverage: Percentage of configured LO weight that is graded.
        status: "provisional", "complete", or "no_data".
    """

    mappings = AssessmentLOMapping.objects.filter(
        learning_outcome=learning_outcome,
        assessment__offering=enrollment.offering,
    ).select_related("assessment")

    weighted_sum = Decimal("0")
    graded_weight = Decimal("0")
    total_weight = Decimal("0")

    for mapping in mappings:
        weight = mapping.weight
        total_weight += weight

        grade = Grade.objects.filter(
            enrollment=enrollment,
            assessment=mapping.assessment,
        ).first()

        # NULL and missing Grade records are both ungraded.
        if grade is None or grade.score is None:
            continue

        normalized_score = (
            grade.score / mapping.assessment.max_score
        ) * Decimal("100")

        weighted_sum += normalized_score * weight
        graded_weight += weight

    if total_weight == 0:
        return {
            "score": None,
            "coverage": Decimal("0"),
            "status": "no_data",
        }

    coverage = (graded_weight / total_weight) * Decimal("100")

    if graded_weight == 0:
        return {
            "score": None,
            "coverage": coverage,
            "status": "no_data",
        }

    score = weighted_sum / graded_weight

    status = (
        "complete"
        if graded_weight == total_weight
        else "provisional"
    )

    return {
        "score": score.quantize(Decimal("0.01")),
        "coverage": coverage.quantize(Decimal("0.01")),
        "status": status,
    }