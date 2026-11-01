# Gnosis v0.1 teammate verification

This is a short independent review checklist for issues #9 and #6. It is ready
for a teammate to use; no teammate completion or team sign-off is claimed.
Use fictional records on your own local database and your own local account.

## Fresh setup (macOS/Linux shell)

Install Python 3.14 first, then:

```bash
git clone https://github.com/TugraDuygulu/gnosis.git
cd gnosis
git rev-parse HEAD
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python manage.py migrate
python manage.py seed_pilot
python manage.py createsuperuser
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py runserver
```

Choose your own credentials when prompted. Do not request another developer's
SQLite file or copy their account/session data. The database stays local and
ignored by Git. Record the actual test count and source revision you receive;
counts may increase after later merges.

## Try the minimum journey

1. Open http://127.0.0.1:8000/ and sign in. On Students, register a new fictional
   student in program PILOT using a new student number. This is an academic
   record, not a student login. Try the same number twice: it must be rejected.
2. Open that student's record and enroll in the existing PILOT311 and PILOT321
   offerings for Fall 2026, section PILOT. Confirm both appear in the record and
   class rosters. An already enrolled offering must disappear from choices.
3. Follow [the v0.1 acceptance walkthrough](v01_acceptance.md), steps 4–7, to enter
   grades, inspect source evidence and correct/clear a score. Expected student
   results with PILOT311 Midterm 80/Project 40 and PILOT321 Midterm0/Lab 35 are:

   | Outcome | Achievement | Coverage |
   | --- | --- | --- |
   | PO2 | 58.75% | 100% |
   | PO3 | 80% | 100% |
   | PO4 | 0% (recorded zero) | 100% |
   | PO5 | 70% | 100% |

4. Change Lab 35 to 40 (out of 50), then clear it. PO5 must move to 80%, then no
   graded evidence; history must show the actor, time and old/new values.
   Missing evidence must not become a zero. Check the other student's records
   remain unchanged. Cancel a form with unsaved edits and confirm no save.
5. Note any confusing navigation, missing explanation, incorrect result or
   blocker. A screenshot of fictional data is useful; never include passwords,
   cookies, private records or an ignored database file in feedback.

The ordinary staff permissions for the journey are add_student, add_enrollment,
change_grade and view_grade. A superuser can perform all steps. Global staff
access is the current policy; instructor-specific ownership is not implemented.
Academic configuration remains in Admin. The pilot includes all eleven official
PO definitions, with intentionally unassessed outcomes and fictional mappings.
Seed reruns preserve manual grade edits rather than resetting the example.

## Return genuine evidence

Add a comment to issue #9 (setup/reproduction) and #6 (interaction findings),
or give the project owner the following information to record accurately:

- Your actual name, date, source commit and operating system/Python version.
- Which setup and journey steps you completed; commands/test result observed.
- Expected versus actual result for any failure, with the relevant route and
  fictional record identifier. Describe any workaround instead of hiding it.
- Whether you independently reproduced the flow or reviewed someone else's
  screen. Do not call either activity a formal PR review unless one occurred.

No shared credentials, invented approvals or retrospective sprint history are
needed. Issues #9/#6 remain open until their actual review criteria are met.

## Assistant reproduction evidence — 1 November 2026

An assistant independently materialized only the tracked source of main
`3a470d5bb0eb5df29ab98694bfd0189d5dc0d0fe` with git archive into a new temporary
directory. No private DB, virtualenv or account/session file was copied.
A new virtualenv installed the pinned requirements with pip --no-cache-dir
(downloaded wheels). Runtime: macOS, Python 3.14.3, Django 6.1.2, SQLite 3.50.4.

Pip compatibility, Django configuration and migration-drift checks passed;
all 62 tests in that committed source passed. A fresh DB migrated successfully,
seed_demo reproduced PO1=72.5%/100% coverage, seed_pilot created eleven official
PO definitions, and rerunning both preserved grades. A temporary superuser with
an unusable password exercised authorized pages using Django's test client;
anonymous access redirected. This check did not test a new manual password
login. The earlier actual browser journey is recorded in v01_acceptance.md.

Seven additional database-boundary tests in the verification branch protect
framework/program mismatch rejection, exact-version/active selection, unmapped
reporting, repeated-course rejection and missing/NULL/zero distinctions. These
tests preserve existing services and policy. Their PR provides final test/CI
evidence after owner approval. Assistant reproduction is not teammate sign-off.
