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
Open a course and follow its grade-edit link to change a score
in Django Admin. Save, return to the outcome pages, and refresh
to see recalculated results.

Running `seed_demo` again preserves existing grade edits,
so your results may differ from the initial example.
This small demo contains one fictional PO, not the full
eleven-outcome departmental framework.

## Development Status

The local v0.1 demo supports staff-only student selection,
assessment-to-LO calculations, course and student-wide PO
results, evidence coverage, and grade editing through Django Admin.

The fictional two-course demo currently covers one PO.
The full departmental framework, frontend improvements,
REST API, CI, and external deployment are not yet implemented.

## Running tests

Run `python manage.py test` from the project root.
