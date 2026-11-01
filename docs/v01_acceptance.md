# Gnosis v0.1 staff workflow

Scope: a local staff application using existing configured academic data.
This is a product acceptance checklist, not completion of the CSE311/CSE321
reports, institutional approval of fictional mappings or a deployed service.
The project owner reviewed and approved this v0.1 staff workflow on November 1,
2026. PR #19 records CI and merge evidence; the Work → Chat handoff records the
final source checkpoint. This is owner acceptance, not full-team sign-off.

## Reproduce

Follow README's Python 3.14 virtual environment and pinned installation steps.
Run migrations and `python manage.py seed_pilot` on a fresh local database;
create your own superuser with `python manage.py createsuperuser` and start
the server. No private database or shared credentials are needed. Seeds preserve
later grade edits. The pilot includes official PO1–PO11 descriptions with clearly
fictional students, offerings, mappings and grades.

## Minimum staff journey

1. Sign in through the existing Admin login. A superuser can perform the whole
   flow; ordinary active staff need `add_student`, `add_enrollment`,
   `change_grade` and `view_grade` for the corresponding actions.
2. Open Students → Register student. Create a fictional student in PILOT with a
   new student number. Required fields, unknown programs and duplicate numbers
   must be rejected without overwriting an existing record.
3. From the student record, enroll in PILOT311 and PILOT321 for Fall 2026,
   section PILOT. Each enrollment is active, appears in the student's record
   and class roster, and begins with no grades. Repeated submission must not
   create a duplicate. Incompatible programs/frameworks are unavailable.
4. Open each course evidence/grade editor. Before entry, blank is missing
   evidence, not zero; a blank save creates no grade records.
5. For PILOT311 enter Midterm 80/100 and Project 40/50. For PILOT321 enter
   Midterm 0/100 and Lab 35/50. Course LO/PO and student profile should update
   immediately: student PO2 = 58.75%, PO3 = 80%, PO4 = 0%, PO5 = 70%, all with
   complete evidence. Unmapped PO1 and PO6–PO11 still have no evidence.
6. Inspect source courses and mappings on the profile/evidence pages. Correct
   Lab to 40/50: PO5 becomes 80%. Open grade history to see actor/time and
   35 → 40. Clear Lab: PO5 returns to no evidence, and history records
   40 → ungraded. PO4 remains a genuine zero with complete evidence.
7. Cancel an unsaved form and try invalid/above-maximum and stale submissions:
   grades and history must stay unchanged. Verify students/offerings stay
   isolated and unauthorized/anonymous users cannot write or read history.

## Verification record

- November 1 baseline main `235f9d9`: 53 tests passed, no missing migrations;
  browser verified history login redirect, 403 for staff lacking view permission,
  empty state and native Lab ungraded → 35 with actor/time/assessment snapshot,
  against actual source using a separate temporary database.
- Issue #18 adds nine intake tests, including the full two-course journey above,
  duplicate/eligibility guards, required/invalid inputs, permissions/CSRF,
  current-state revalidation, save-conflict handling and empty/escaped states.
- November 1 feature validation: all 62 tests pass locally (53 preserved plus
  nine intake tests), system check clean, no migration changes, whitespace check
  clean. Actual-source browser walkthrough used an isolated temporary database:
  registered V01REVIEW, enrolled in both pilot offerings, verified 58.75% student
  PO2, 80% PO3, genuine zero PO4, 70% PO5 and source weights 5/3; corrected Lab
  35 → 40 and cleared it, confirming recalculation and actor/time/value history.
  Duplicate registration retained input and saved nothing; existing enrollment
  was removed from choices. This is assistant verification, not teammate review.
  The owner subsequently approved commit/push/PR and merge after successful CI.
  See PR #19 for the current CI and merge result.

## Limits and remaining work

Academic configuration remains in Admin. Global staff access is used; login
accounts are not linked to Instructor records. Retakes, framework equivalence,
publication/lifecycle rules, imports, status changes, student self-service,
frontend/API choice and deployment are separate decisions. Grade history covers
only native editor and Grade Admin writes, has no backfill and is not immutable;
see README. Native intake eligibility does not constrain direct Admin/ORM writes.

Independent teammate reproduction (#9), interaction/frontend handoff (#6),
framework/aggregation boundary regressions (#12), ERD/model alignment (#2/#3),
reproducible SQL (#4) and report evidence (#13/#14) remain tracked separately.
An assistant browser walkthrough is not teammate review or team acceptance.
