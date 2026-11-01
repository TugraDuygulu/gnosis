# Three reproducible Gnosis SQL questions — CSE321 issue #4

Review deliverables for [issue #4](https://github.com/TugraDuygulu/gnosis/issues/4), based on application source `1106cd01d572b1a73af433ab30e7bf7ab3854db1` (1 November 2026), core migrations through 0009. The three files are executable SQLite SELECT statements, not ORM equivalents. No application model, formula, migration or UI change is proposed.

## Reproduce safely

From a project checkout with the existing pinned dependencies installed:

```sh
.venv/bin/python sql/verify_queries.py --output-dir /tmp/gnosis-sql-review
```

Choose an output directory that does not exist. The verifier configures a **new temporary SQLite database before Django setup**, runs `migrate`, runs `seed_pilot` **once**, executes the saved SQL, compares it with independent hand calculations and `calculate_lo_achievement()`, and runs the edge-case tests. It deletes the temporary database afterwards. It accepts no development database path and does not use `DJANGO_SETTINGS_MODULE` to select a database. Do not run seed commands against the normal project database to reproduce this evidence.

The output directory contains:

- `actual_results.md`: readable baseline result tables.
- `actual_results.json`: every returned SQL column, bound parameter and baseline Decimal service reference.
- `manual_expectations.json`: independent exact expectations, including rational values such as `580/7`.
- `verification.json`: runtime, source hashes, numeric tolerance/difference, test names and result counts.

The checked-in outputs under [evidence/pilot_2026-11-01](evidence/pilot_2026-11-01/actual_results.md) come from an actual successful run. Rerunning does not overwrite them. The recipe creates the same fictional pilot used by the [database documentation](../docs/database_design.md): two students, two offerings, four assessments, four LOs, six assessment/LO mappings and eight Grade rows (including NULL scores). This SQL task does not alter `seed_pilot` or `seed_demo`. The smaller `seed_demo` is not used here because the richer pilot already exercises unequal maxima and partial/zero/no-data evidence.

## Parameters and an equivalent SQL-client invocation

| Query | File | Required named bindings |
| --- | --- | --- |
| 1 | [01_student_assessment_grades.sql](01_student_assessment_grades.sql) | `:student_number` TEXT, `:offering_id` INTEGER |
| 2 | [02_student_lo_attainment.sql](02_student_lo_attainment.sql) | `:student_number` TEXT, `:offering_id` INTEGER |
| 3 | [03_offering_lo_summary.sql](03_offering_lo_summary.sql) | `:offering_id` INTEGER |

The verifier executes the file contents directly using Python's SQLite client, binding values separately from SQL text. This is the equivalent-SQL-client route permitted by issue #4; it does not run the calculations through ORM expressions. It resolves offering IDs by course code only in the fresh seed, which has exactly one offering per course. No query relies on this uniqueness or hardcodes a primary key. The actual baseline IDs are recorded in the output (PILOT311=1, PILOT321=2); arbitrary databases can assign different IDs.

For presentation practice, execute the same saved statement in the already isolated Python/Django setup:

```python
from pathlib import Path
from django.db import connection

sql = Path('sql/02_student_lo_attainment.sql').read_text()
cursor = connection.connection.execute(
    sql, {'student_number': 'PILOT001', 'offering_id': 1}
)
columns = [column[0] for column in cursor.description]
rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
```

This snippet assumes the verifier's temporary connection is already initialized. The one-command verifier is the complete standalone setup/invocation; the snippet is not a command to seed or mutate the development database. Named `:bindings` are SQLite/Python client syntax; Django's wrapped `cursor.execute()` uses a different placeholder convention, so the verifier intentionally uses the underlying initialized SQLite connection. SQL parameters are values, not interpolated table names or string replacements.

## Query 1 — What assessment grades has a student received in one offering?

**Statement:** [01_student_assessment_grades.sql](01_student_assessment_grades.sql).

Start with Student → Enrollment → CourseOffering → Course → Assessment using INNER JOINs. Assessment belongs to the **selected offering**, not just the same course code. LEFT JOIN Grade using **both enrollment_id and assessment_id**: this retains an assessment whose Grade row has not been created and prevents another student's grade from matching. Filtering by unique student number and exact offering ID prevents student/section/year mixing.

`100.0 * raw_score / max_score` converts raw marks to a comparable percentage. `CASE` labels three distinct database states: `missing_grade`, `null_score`, and `recorded`. Both missing states have a NULL percentage; a recorded zero has percentage zero and remains recorded evidence. Individual queries include the selected enrollment regardless of its status and expose that status in Query 1. This matches the LO service's individual-enrollment contract; it is different from Query 3's explicitly active-only summary.

Expected versus observed baseline (all eight assessment rows):

| Student | Offering | Assessment | Expected raw/max | Expected normalized % | Observed normalized % | Observed state |
| --- | --- | --- | --- | ---: | ---: | --- |
| PILOT001 | PILOT311 | Midterm | 90/100 | 90 | 90 | recorded |
| PILOT001 | PILOT311 | Project | 40/50 | 80 | 80 | recorded |
| PILOT002 | PILOT311 | Midterm | 70/100 | 70 | 70 | recorded |
| PILOT002 | PILOT311 | Project | NULL/50 | NULL | NULL | null_score |
| PILOT001 | PILOT321 | Midterm | 0/100 | 0 | 0 | recorded |
| PILOT001 | PILOT321 | Lab | NULL/50 | NULL | NULL | null_score |
| PILOT002 | PILOT321 | Midterm | 80/100 | 80 | 80 | recorded |
| PILOT002 | PILOT321 | Lab | 40/50 | 80 | 80 | recorded |

The pilot baseline contains NULL Grade rows. A separate test deletes a Grade row and verifies that its assessment remains visible as `missing_grade`, then recreates a NULL row and verifies `null_score`. Query 2 treats both as absent evidence. With no enrollment, a nonexistent offering or no assessments, Query 1 returns no rows; it does not invent a grade.

**Interpretation:** an instructor can see what was entered, compare different maximum scores and distinguish an actual zero from unfinished entry. This is not the student's final course grade: `course_grade_weight` is not applied here.

## Query 2 — What is each LO's weighted attainment for this student/offering?

**Statement:** [02_student_lo_attainment.sql](02_student_lo_attainment.sql).

The CTEs name three readable steps, not persisted tables:

1. `selected_enrollment` chooses the exact student/offering pair and its curriculum.
2. `offering_mappings` joins AssessmentLOMapping to Assessment and filters assessments to the exact offering. This matters because different offerings may share a curriculum and its LOs.
3. `evidence_totals` starts with **all LOs of that curriculum**, then LEFT JOINs the filtered mappings and the selected enrollment's grades. GROUP BY the enrollment and LO produces one evidence total per student/LO.

For mapped weight `w_i` and normalized recorded score `x_i`, the query computes:

- `attainment = SUM(w_i * x_i for non-NULL grades) / SUM(w_i for non-NULL grades)`.
- `coverage = 100 * graded_mapping_weight / total_mapping_weight`.

`COUNT(g.score)` counts non-NULL scores, **including zero**. It does not count a missing/NULL score. `COALESCE` supplies zero evidence totals; it never turns a missing attainment into a zero score. `NULLIF(graded_mapping_weight, 0)` leaves attainment NULL when there is no graded evidence. An unmapped LO is retained with NULL score, zero coverage and `no_data`.

All mapping weights are positive by the database CHECK. Therefore, “every mapped assessment is graded” is equivalent to equality of graded and configured weight. The query uses **integer evidence counts** for complete/provisional status, avoiding floating-point or display-rounding decisions. A coverage of 99.999% remains provisional even if a UI rounds it to 100.00%.

Expected versus observed (values shown to nine decimals; calculations are not rounded):

| Student | Offering | LO | Expected attainment % | Observed attainment % | Expected coverage % | Observed coverage % | Status, expected = observed |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| PILOT001 | PILOT311 | LO1 | 86 | 86 | 100 | 100 | complete |
| PILOT001 | PILOT311 | LO2 | 580/7 | 82.857142857 | 100 | 100 | complete |
| PILOT002 | PILOT311 | LO1 | 70 | 70 | 60 | 60 | provisional |
| PILOT002 | PILOT311 | LO2 | 70 | 70 | 200/7 | 28.571428571 | provisional |
| PILOT001 | PILOT321 | LO1 | 0 | 0 | 100 | 100 | complete |
| PILOT001 | PILOT321 | LO2 | NULL | NULL | 0 | 0 | no_data |
| PILOT002 | PILOT321 | LO1 | 80 | 80 | 100 | 100 | complete |
| PILOT002 | PILOT321 | LO2 | 80 | 80 | 100 | 100 | complete |

For PILOT001/PILOT311, the normalized scores are 90 and 80. LO1 = `(90*60 + 80*40)/100 = 86`; LO2 = `(90*40 + 80*100)/140 = 580/7`. Dividing LO2 by 100 would be wrong: its **relative weights sum to 140**. For PILOT002, only Midterm is graded, so LO1 and LO2 both score 70, with different coverage (60/100 and 40/140).

The separate instructor-example test changes the **temporary test** Project to 80/100, reproducing the official worked example literally as well as the pilot's equivalent normalized 40/50 case. It matches `LOCalculatorTests.test_instructor_example_lo1_is_86` and `test_instructor_example_lo2_preserves_precision` in [core/tests.py](../core/tests.py). No early rounding to 82 or 82.9 is fed into subsequent calculations.

**Interpretation:** an instructor sees both attainment based on available evidence and how much configured evidence supports that number. Completeness is an evidence statement, not passing/mastery. Credits, LO→PO strengths and course→PO contribution weights do not belong in this query.

## Query 3 — What are students' average LO results in one offering?

**Statement:** [03_offering_lo_summary.sql](03_offering_lo_summary.sql).

This introduces an explicit **reporting choice for review**, not a new institutional rule or changed application calculation:

| Question | Chosen summary semantics |
| --- | --- |
| Population | Enrollment rows in the exact offering with `status='active'` |
| Unit of averaging | One student's already normalized, evidence-weighted LO result; equal weight per student |
| Partially graded students | Included using their provisional available-evidence score |
| Students with no evidence | Excluded from score AVG because score is NULL; retained in counts and mean coverage as coverage zero |
| Coverage | Arithmetic mean of each active student's LO evidence coverage, including zero for no data |
| No active students | Retain each curriculum LO; counts 0; score and coverage means NULL (no population) |
| No mappings / everyone ungraded | Score mean NULL; active population retained, coverage mean 0; `no_data_students` records absence |
| Missing offering / no curriculum LOs | No result rows |

The first CTEs calculate the same per-enrollment totals as Query 2 for every active enrollment. `student_results` computes the individual score, coverage and status. The final GROUP BY LO then uses `AVG(attainment_percent)` and `AVG(coverage_percent)`, with CASE-based evidence counts. The outer LEFT JOIN retains LOs even when the active roster is empty; `COUNT(enrollment_id)` correctly reports zero instead of counting a placeholder row as a student.

`AVG` ignores NULL scores. This is deliberate and visible in `students_with_evidence`, `complete_students`, `provisional_students` and `no_data_students`. It is **not** an average of raw marks, a pooled evidence-weighted course average, a complete-students-only average, a pass rate or a PO aggregate. Provisional students can influence the mean as much as complete students; the separate coverage/status columns expose that limitation.

Expected versus observed baseline:

| Offering | LO | Active | Scored | Complete / provisional / no data | Expected mean score % | Observed mean score % | Expected mean coverage % | Observed mean coverage % |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| PILOT311 | LO1 | 2 | 2 | 1 / 1 / 0 | 78 | 78 | 80 | 80 |
| PILOT311 | LO2 | 2 | 2 | 1 / 1 / 0 | 535/7 | 76.428571429 | 450/7 | 64.285714286 |
| PILOT321 | LO1 | 2 | 2 | 2 / 0 / 0 | 40 | 40 | 100 | 100 |
| PILOT321 | LO2 | 2 | 1 | 1 / 0 / 1 | 80 | 80 | 50 | 50 |

Example: PILOT311 LO1 = `(86 + 70)/2 = 78`; coverage = `(100 + 60)/2 = 80%`. PILOT321 LO2 has only one scored student, so its mean score is 80, **not 40**; mean coverage is `(0+100)/2 = 50%`. A zero score in PILOT321 LO1 does count, producing `(0+80)/2 = 40` with 100% coverage.

There is no existing course-summary service. The verifier independently calls `calculate_lo_achievement()` for each active enrollment and then averages those Decimal results according to this explicit definition. It does not claim a previously implemented institutional summary formula.

**Interpretation:** PILOT321's LO2 mean of 80 looks strong but covers only half the active roster's configured evidence. PILOT311's means include provisional results and should not be presented as finalized cohort attainment. This helps instructors identify entry gaps before interpreting scores.

## Verification, numeric limits and evidence provenance

The initial implementation was checked against the actual models/migration DDL, [field dictionary](../docs/data/pilot_2026-11-01/field_dictionary.md), [schema inventory](../docs/data/pilot_2026-11-01/schema_inventory.json), ERD and [calculation policy](../docs/calculation_policy.md). The source hashes of models, migrations, services and seed still match the reviewed v0.1 inventory. FK and unique endpoint constraints prevent valid Grade/mapping joins from multiplying one logical fact into duplicates. Only validated data is assumed: these read-only queries do not repair cross-table inconsistencies introduced by raw/bulk writes outside supported flows.

The dedicated verifier runs **17 independent test cases** with transaction rollback around each mutation. It covers baseline hand/service comparisons, literal instructor examples, unequal maxima, missing versus NULL grade rows, recorded zero, fractional division and weights, 99.999% provisional coverage, no mappings, no-data students, empty and inactive rosters, unknown/un-enrolled students and exact-offering isolation with a shared curriculum. Baseline output is captured before test mutations and checked again after rollback. SQLite integrity and FK checks pass. The main application's existing 69-test suite is run separately; these 17 checks are not silently represented as part of existing CI.

Selected edge-case assertions (executed, not hypothetical examples):

| Controlled temporary change | Expected | Observed / assertion |
| --- | --- | --- |
| Delete a Grade row, then recreate it with NULL score | Assessment retained; missing_grade then null_score | Passed; LO evidence results identical for absent/NULL scores |
| Set every selected student's score to recorded zero | Score 0, coverage 100, complete | Passed for both curriculum LOs and matched Decimal service |
| Add an active student with no Grade rows | Score means unchanged; coverage reduced; no_data count increases | Passed; active count 3 and no_data count 1 |
| Create another offering sharing the curriculum, with extra mappings/grades | Original student's grades, LOs and original summary unchanged | Passed; separate offering's results also matched service |
| Grade 999.99 of 1000 relative weight | Coverage 99.999%, provisional | Passed; status was not rounded to complete |
| Withdraw every enrollment | Counts 0, both means NULL, LOs still returned | Passed; no phantom student from the outer join |

To repeat the completed validation from a checkout:

```sh
.venv/bin/python sql/verify_queries.py --output-dir /tmp/gnosis-sql-review
.venv/bin/python manage.py test --verbosity 1
.venv/bin/python manage.py makemigrations --check --dry-run
```

The first command's 17 dedicated SQL cases and the second command's 69 application tests passed separately using the actual project virtualenv against a source copy. The migration dry run reported no changes. Two fresh SQL runs produced byte-identical JSON and Markdown output. No GitHub Actions run is claimed before publication.

SQLite `decimal` columns have numeric affinity rather than strict fixed-point Decimal storage. `100.0`/REAL casts prevent integer division. SQL uses binary floating-point sums/division, whereas the service uses Python Decimal arithmetic. On the checked-in run (Python 3.14.3, Django 6.1.2, SQLite 3.50.4), **122 numeric comparisons** passed with absolute tolerance **1e-9 percentage points**; maximum observed difference was approximately **4.28571428571e-15**. NULLs, evidence status and counts must match exactly. These tests establish agreement on the specified fixtures/cases, not exact numeric identity for all possible data or another database engine. No performance improvement, query-plan optimization, production authorization or cross-engine portability is claimed.

Query 2 and Query 3 deliberately repeat their small evidence-total CTEs so that each SQL file executes independently. Verification against the same service helps detect future drift. No persistent view, extra index or materialized aggregate was introduced. Standalone queries have no web-session permission checks; run only in the intended local/report context with appropriate database access.

## CSE321 report use and issue acceptance

Official sources consulted: **Team Project Guidelines**, October 22 version, pp. 5–6 (normalized weighted assessment→LO example), p. 14 (November 12 Data & System Architecture checkpoint), pp. 16 and 18 (125% code/figure visibility and six-section report outline); **CSE321 Report Format 2**, pp. 1–2 (System Design, Data Model, Scalability and Fault Tolerance, Consistency, Teamwork). Issue #4 additionally cites the October 22 weekly task checklist's three SQL questions. That issue is the source for this task; the report-format PDF does **not** prescribe a separate numbered “SQL section.”

Proposed report placement: use this question/SQL/result/verification material as a database-query evidence appendix referenced from Section 3 (Data Model), with a suitable short excerpt during the presentation. Keep complete executable statements in the repository and ensure pasted snippets remain readable at the required scale. This is prepared material for [report issue #13](https://github.com/TugraDuygulu/gnosis/issues/13), not the full report, its architecture/class diagram, transaction analysis or team-contribution narrative.

| Current issue #4 criterion | Evidence / review status |
| --- | --- |
| Three saved queries answer the agreed questions | Three standalone parameterized SQL files; Query 3 semantics explicitly proposed for review |
| Actual names, exact setup and invocation | Real core_* tables/FKs, migration+seed recipe and one-command isolated verifier |
| Expected/actual output and isolation | Eight grade rows, eight student/LO rows, four summary rows; JSON/Markdown and independent manual fractions; isolation tests |
| Normalize maxima and divide mapped totals correctly | Unequal-max pilot, weight total 140, fractional division and literal instructor-example tests |
| Missing/NULL/zero, provisional inclusion and coverage | SQL CASE/LEFT JOIN/NULLIF/COUNT/AVG semantics, tests and explanations above |
| Store notes/SQL and link from #13 | Files prepared locally; publishing and adding the #13 backlink await explicit approval |

All technical deliverables are ready for owner review. Do not claim commit, push, PR, CI result, issue closure or team/instructor review until each actually occurs. Issue #3 reconciliation and full report assembly are subsequent work, not part of this change.
