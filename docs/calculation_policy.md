# Implemented calculation policy

This documents the current implementation, not a claim of full-team or
institutional approval of every missing-evidence or enrollment policy.

## Assessment to learning outcome

Normalize each recorded score as `100 * score / max_score`. Combine scores
using the assessment-to-LO relative mapping weights for the selected offering.
Weights are normalized per target LO and need not sum to 100.

A missing Grade record and `score=None` both mean ungraded. A recorded zero
is graded evidence and is included in the average. The provisional score
uses graded weight only. Coverage is graded weight divided by all configured
weight. No mappings or no graded weight yields `score=None`, coverage 0 and
`no_data`; all configured weight graded yields `complete`, otherwise
`provisional`. Completeness describes evidence, not passing or mastery.

Use Decimal arithmetic without intermediate rounding. Format rounded values
for display only; do not feed displayed rounded values into later layers.

## Instructor-example regression evidence

For Midterm=90 and Project=80 (both out of 100):

| Target | Relative weights (Midterm, Project) | Exact LO result | Display to 1 decimal |
| --- | --- | --- | --- |
| LO1 | 60, 40 | 86 | 86.0 |
| LO2 | 40, 100 | 580/7 = 82.857142… | 82.9 |

Both have 100% evidence coverage and complete status. These examples are
protected by `LOCalculatorTests.test_instructor_example_lo1_is_86` and
`test_instructor_example_lo2_preserves_precision` in `core/tests.py`.

Source: instructor Team Project Guidelines, worked example, page 6;
Team Project Brief, assessment-to-LO diagram. The Brief's early rounded
82 is illustrative rather than the exact arithmetic result.

## Subsequent layers and boundaries

Course PO scores combine LO results using LO-to-PO strength adjusted by
LO coverage. Student PO scores combine course PO results using the separate
CoursePOContribution weight adjusted by course coverage. Course credits,
assessment course-grade weights and LO mapping weights are distinct fields.

Student aggregation uses active enrollments in the exact selected framework,
reports unmapped enrollments separately and rejects repeated mapped courses
until an explicit retake policy is agreed. Missing evidence stays absent,
not zero. Framework/selection regression follow-ups are tracked in issue #12.
