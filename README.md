# Gnosis

## Shared project context

Team Nous: start with [AGENTS.md](AGENTS.md), then the dated
[project snapshot](docs/PROJECT_CONTEXT.md) and the relevant GitHub issue.
The [six-week sprint plan](docs/sprints/SIX_WEEK_PLAN.md) schedules 16 November
through 27 December 2026; [Sprint 1](docs/sprints/SPRINT_01.md) starts 16 November.
Use [roadmap #27](https://github.com/TugraDuygulu/gnosis/issues/27) and its linked
issues for live planning, assignments, digital check-ins and reviews. Estimates
come from actual team Planning Poker; no completed sprints are implied by setup.
Use [task handoffs](docs/handoffs/README.md) to preserve unfinished work.
Tool-specific entry points link to these shared files rather than duplicate them.
No access to a personal Notion workspace or another sprint app is required.

## About

Gnosis is a web application for managing course assessments,
learning outcomes (LOs), and program outcomes (POs).

It aims to help instructors and coordinators track student
performance and evaluate achievement of educational outcomes.

## Tech Stack

- Python 3.14
- Django 6.1
- SQLite (development database)
- Git and GitHub

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/TugraDuygulu/gnosis.git
cd gnosis
```

### 2. Create a virtual environment

```bash
python3.14 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Initialize the database

```bash
python manage.py migrate
```

### 5. Start the development server

```bash
python manage.py runserver
```

Open the local address shown in the terminal.

### Windows setup notes

The commands above are for macOS/Linux. On Windows (PowerShell in VS Code):

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py test
```
## Running the demo (for teammates)

After completing Local Setup:

1. Run `python manage.py migrate`.
2. Run `python manage.py seed_demo`.
3. Create your own local admin account with `python manage.py createsuperuser`.
4. Start the server with `python manage.py runserver`.
5. Open http://127.0.0.1:8000/, sign in with that account,
   and select Demo Student → Framework v1.

On a fresh database, the fictional demo combines DEMO311
(80%, contribution weight 5) and DEMO321 (60%, weight 3),
giving PO1 achievement of 72.50% with 100% evidence coverage.
Open a course and select **Edit course grades** to change raw assessment
scores. Save returns to course evidence with recalculated results.

Running `seed_demo` again preserves existing grade edits,
so your results may differ from the initial example.
This small demo contains one fictional PO, not the full
eleven-outcome departmental framework.

## Teammate verification

Use [the fresh setup and short review checklist](docs/teammate_verification.md)
to independently reproduce v0.1 with your own account and fictional database.
Record the actual commit, results and any blockers in issues #9/#6. Assistant
checks do not substitute for independent teammate verification.

## Register and enroll students

From **Students**, authorized staff can select **Register student**, enter a
full name, unique student number and existing program, then open the student's
record and select **Enroll in a course offering**. Registration creates an
academic record, not a login. Names and numbers are trimmed; numbers preserve
case and leading zeros and use the existing exact database uniqueness rule.

Registration requires active staff plus `core.add_student`; enrollment requires
`core.add_enrollment`. The student page is staff-only, with grade editing/history
links gated by their existing permissions. New enrollment is active and starts
without grades. Existing enrollment records cannot be duplicated or reactivated
by this form. Offerings must have a matching course/curriculum and a same-program
PO framework. A second active offering of the same course/exact framework is
excluded while retake policy remains unresolved; another framework version is
kept separate. Eligibility is rechecked inside the save transaction.

The offering's recorded status is displayed; v0.1 does not invent a lifecycle
policy for the existing free-text status fields. Programs, course offerings,
curricula, assessments and outcome mappings are configured through Django Admin.
No import, mass enrollment, withdrawal/status editor or instructor ownership
policy is introduced. Admin/script writes are outside these native intake guards.
See [v0.1 acceptance and walkthrough](docs/v01_acceptance.md).

## Course workspace

Use **Courses** from any staff page to find an offering by course code/title,
instructor, term, year or section. Each offering has its own roster, including
recorded enrollment statuses. Open a student's course evidence, matching
framework profile, or grade editor (requires `core.change_grade`). Course
evidence and the editor link back to that offering's roster.

The roster shows all enrollment records; student-wide calculations continue
to use active enrollments only. Missing or incompatible frameworks are
explained rather than linked to a nonexistent profile. All pages remain
staff-only; this does not add instructor-specific ownership or new roles.

## Native grade editor

Active staff with `core.change_grade` can edit one student's course at
`/enrollments/<enrollment_id>/grades/`, linked from course evidence.
This retains the current global staff permission model; instructor ownership
is not enforced because academic Instructor records are not linked to logins.

Zero is a recorded grade; blank means ungraded and can clear a previous
score. Negative, above-maximum and invalid decimal scores are rejected.
All assessment fields must be submitted, and all changes save together.
An expired or stale page saves nothing and offers a reload link. Cancel
returns without saving. The Django Admin link remains available.

For the representative fictional pilot, run `python manage.py seed_pilot`.
Open Pilot Student A, Framework v1, then PILOT321. On fresh pilot data,
Midterm is 0/100 and Lab is blank. Saving Lab as 35/50 gives LO2 and PO5
70% achievement with complete evidence. Restore Lab to blank after review
if you want the original no-evidence example. Seed reruns preserve edits.
The pilot uses the eleven official PO descriptions with fictional course
mappings, students and grades.

## Grade-change history

Active staff with `core.view_grade` can open **Grade-change history** from a
student's course evidence or grade editor. History is scoped to that enrollment,
newest first, with 50 entries per page. It records actor, UTC time, assessment,
score maximum at the time, old/new values and source. Zero is distinct from
ungraded. Creates, changes, clears and single/bulk Admin deletions are recorded;
unchanged saves and rejected/rolled-back writes produce no history. Existing
Admin grade identities are read-only: clear a wrong record and create the
correct one rather than moving it to a different enrollment or assessment.

History uses Django's existing `admin.LogEntry`; no application model or
migration is added. It starts with this feature and cannot reconstruct earlier
scores. Only native-editor and Grade Admin writes are covered. ORM scripts,
seeds, shell, direct SQL and future import paths require explicit integration.
This is not an immutable audit ledger: database administrators can change logs,
and deleting an auth user cascades to their entries. Usernames shown are current
login names. History and grade writes share a transaction; a logging failure
aborts the write. The existing global staff permission boundary is unchanged.

## Development Status

Gnosis v0.1 supports native student registration and compatible course
enrollment, staff student/course navigation, assessment-to-LO calculations,
course and student-wide PO results, evidence coverage, native grade editing
and grade-change history. The owner-approved scope is a local staff application;
academic configuration remains in Django Admin.

The fictional two-course demo currently covers one PO.
The separate representative pilot contains all eleven official PO definitions;
some outcomes intentionally have no configured or graded evidence.
Further frontend improvements, REST API and external deployment remain
future work. The Django checks workflow verifies the development setup;
successful CI results must be confirmed in GitHub Actions.

## Development workflow

See [development workflow and evidence](docs/development_workflow.md) for the
issue-to-PR process, local checks and CI scope. Full-team adoption and reviewer
ownership remain for team agreement.

## Running tests

Run `python manage.py test` from the project root.

See [implemented calculation policy](docs/calculation_policy.md) for the
missing-versus-zero rules, relative weights and exact instructor examples.


## Reproducible CSE321 SQL evidence

See [the three SQL questions and verification guide](sql/README.md) for student assessment grades, weighted LO attainment and an explicitly defined course-offering summary. Run the saved statements and edge-case checks in a fresh temporary fictional database with:

```sh
.venv/bin/python sql/verify_queries.py --output-dir /tmp/gnosis-sql-review
```

Choose a new output directory. The verifier never reseeds or opens the development database.

## CSE321 report workspace

The [November 12 working report workspace](docs/reports/cse321/README.md) contains the six-section draft, architecture/class diagrams, verified model alignment, SQLite consistency evidence and remaining information checklist. It is a review draft, not a final submission.

## Academic accounts

See [Academic accounts](docs/academic_roles.md) for permissions, database
migration, account provisioning, and the fictional demonstration walkthrough.
