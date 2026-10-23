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

## Development Status

Initial Django project setup complete.
Database schema and application features are under development.