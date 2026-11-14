# Academic accounts

Gnosis uses Django authentication. Active superusers administer the system.
An administrator designates coordinators through the `Gnosis Coordinators`
group. An instructor or student signs in with the user linked to their existing
academic record. Email addresses, student numbers and offering IDs do not grant
access.

| Role | Workspace access |
| --- | --- |
| Administrator | Academic management, all grade and outcome views, and full Django Admin |
| Coordinator | Programs, courses, offerings, assignments, students, instructors, academic logins, enrollment, curriculum configuration, grade history, and program-wide results |
| Instructor | Assigned offerings, their rosters, gradebooks, grade history and course outcome evidence |
| Student | Own enrollments, grades, course LO/PO evidence and student-wide outcomes |

Existing unlinked Django staff users retain their previous workspace access and
model-permission checks. Only superusers can manage users, groups and identity
links through Django Admin. Review any legacy staff permissions before working
with real records.

Coordinators use **Academic management** to create a new dedicated login from
an existing instructor or student record. To link an already existing Django
user, a superuser can select that user on the academic record in full Admin.
Use an account without staff flags, unrelated groups or direct permissions.
Use a single academic role per account. The application rejects ambiguous roles
and prevents coordinators from changing credentials for privileged or ambiguous
logins. Use a trusted channel to convey initial credentials. Reset passwords
through the coordinator workflow. Disabling a login clears its password and
invalidates prior sessions. To restore access, set a new password and enable it.

The coordinator's curriculum configuration area permits academic changes and
excludes account administration. Coordinators can add and update records,
withdraw or reactivate enrollments, and reassign an offering's instructor.
Configuration fields tied to existing academic records are restricted where
changing them would rewrite those relationships. Destructive operations are
reserved for administrators. The role work does not change the LO/PO formulas,
coverage rules, or existing grade history.

## Upgrade

Back up the intended database and run `python manage.py migrate`. Migration
`core.0010` adds a nullable, unique link to each Instructor and Student table.
Existing unlinked records, enrollments and grades are retained. Removing a
Django user clears their academic link. Public signup and recovery by email
are outside this workflow.

## Fictional walkthrough

Use a separate checkout with a fresh development database and the repository's
pinned dependencies. Run these commands from that checkout. Choose credentials
interactively. Keep passwords and the local database out of Git.

```sh
python manage.py migrate
python manage.py seed_pilot
python manage.py createsuperuser
python manage.py runserver
```

1. Open `http://127.0.0.1:8000/login/` as the superuser. In Django Admin, create
   the group `Gnosis Coordinators` with no additional permissions. Create a
   dedicated non-staff user, set its password and add it to the group. Log out
   and sign in as that coordinator.
2. Open **Academic management**. Add a fictional instructor and create their
   login. Edit the `PILOT311` offering and assign the instructor. Leave
   `PILOT321` with the original instructor to check offering isolation.
3. Register a new fictional student in the `PILOT` program. Create the student's
   login from their record, then enroll them in `PILOT311`.
4. Sign in as the new instructor. Open **My courses**, the `PILOT311` roster,
   and its gradebook. Enter Midterm `90` and Project `40` for the new student.
   LO1 is 86% and LO2 is approximately 82.857%. Correct a grade and inspect
   grade history. Confirm that `PILOT321` is absent from **My courses**.
5. Sign in as the new student. Open **Grades and LO/PO evidence** and their
   program outcome profile. Direct grade-editor requests and access to another
   student's record should fail. To check zero versus missing, have the
   instructor save `0` for one assessment and clear another.
6. Sign in as the coordinator. Open **Overview** to inspect the program's
   aggregated outcome results and evidence coverage.

`python manage.py test core.test_academic_roles` exercises the principal role
boundaries and the intake-to-outcomes walkthrough with generated credentials.
