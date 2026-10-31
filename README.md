# Gnosis

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

## Development Status

The local v0.1 demo supports staff-only student selection,
assessment-to-LO calculations, course and student-wide PO
results, evidence coverage, and native per-student course grade editing.

The fictional two-course demo currently covers one PO.
The separate representative pilot covers all eleven official POs.
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
