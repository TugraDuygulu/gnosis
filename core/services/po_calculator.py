from decimal import Decimal
from core.models import LOPOMapping
from core.services.lo_calculator import calculate_lo_achievement


def calculate_course_po_achievement(enrollment, program_outcome):
    """
    Calculate a student's PO achievement within one course offering.

    Uses LO achievement scores weighted by mapping strength
    and evidence coverage.
    """
    offering = enrollment.offering

    # The offering must have an assigned PO framework.
    if offering.po_framework_id is None:
        raise ValueError(
            "The course offering has no assigned PO framework."
        )

    # Never calculate using a PO from another framework version.
    if program_outcome.framework_id != offering.po_framework_id:
        raise ValueError(
            "The requested Program Outcome does not belong "
            "to this offering's PO framework."
        )

    # Only use LOs from the offering's assigned curriculum.
    mappings = LOPOMapping.objects.filter(
        program_outcome=program_outcome,
        learning_outcome__curriculum=offering.curriculum,
    ).select_related("learning_outcome")
    total_strength = Decimal("0")
    effective_strength_total = Decimal("0")
    weighted_score_total = Decimal("0")

    for mapping in mappings:
        strength = Decimal(mapping.strength)
        total_strength += strength

        lo_result = calculate_lo_achievement(
            enrollment,
            mapping.learning_outcome,
        )

        if lo_result["score"] is None:
            continue

        coverage_fraction = lo_result["coverage"] / Decimal("100")
        effective_strength = strength * coverage_fraction

        weighted_score_total += lo_result["score"] * effective_strength
        effective_strength_total += effective_strength

    if effective_strength_total == 0:
        return {
            "score": None,
            "coverage": Decimal("0"),
            "status": "no_data",
        }

    score = weighted_score_total / effective_strength_total
    coverage = effective_strength_total / total_strength * Decimal("100")

    return {
        "score": score,
        "coverage": coverage,
        "status": "complete" if coverage == Decimal("100") else "provisional",
    }
