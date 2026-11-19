"""Route-access matrix for every named core route under the academic roles (#40).

``ACCESS`` is the single declarative record of who may reach each protected
route, at which record scope, and what a denial looks like. The tests walk
``core.urls`` so a new page without an access rule fails the suite, then drive
every actor through every route with GET and POST. Denied POSTs carry payloads
that would really write if the gate were missing (``test_write_payloads_*``
proves that), and every rejection is checked against unchanged student,
enrollment, grade, grade-history, record and account rows.

Rows marked "pending decision" encode the PR #25 behaviour proposed in the
#38 access-matrix comment; the team has not yet confirmed them.
"""
from collections import namedtuple
from decimal import Decimal
from io import StringIO
from secrets import token_urlsafe

from django.contrib.admin.models import LogEntry
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.db import transaction
from django.test import Client, TestCase
from django.urls import reverse

from core import urls as core_urls
from core.access import COORDINATOR_GROUP
from core.grade_editor import revision_token, snapshot
from core.models import (
    Course, CourseCurriculum, CourseOffering, Enrollment, Grade, Instructor,
    POFramework, Program, Student,
)

# Intentionally public: reachable without a session, no academic role required.
PUBLIC_ROUTES = {"login", "logout"}

# Access rules. ``core.<perm>`` in the legacy column means "allowed only with
# that Django permission, otherwise 403".
ALL = "all"            # 200 for every applicable record
OWN = "own"            # 200 inside the actor's scope, 404 for a foreign record
DENY = "deny"          # 403 for the role, whatever the record
TO_COURSES = "to_courses"        # redirect to course_list
TO_OWN_DETAIL = "to_own_detail"  # redirect to the student's own record

ROLES = ("admin", "coordinator", "legacy", "instructor", "student")
ACCESS = {
    # route                       admin coordinator legacy staff            instructor  student
    "student_list":              (ALL, ALL,  ALL,                    TO_COURSES, TO_OWN_DETAIL),
    "student_detail":            (ALL, ALL,  ALL,                    DENY,       OWN),
    "student_outcomes":          (ALL, ALL,  ALL,                    DENY,       OWN),
    "program_overview":          (ALL, ALL,  ALL,                    DENY,       DENY),
    "course_list":               (ALL, ALL,  ALL,                    ALL,        DENY),
    "offering_detail":           (ALL, ALL,  ALL,                    OWN,        DENY),
    "enrollment_outcomes":       (ALL, ALL,  ALL,                    OWN,        OWN),
    # pending decision: coordinator reads all history but cannot grade.
    "enrollment_grade_history":  (ALL, ALL,  "core.view_grade",      OWN,        DENY),
    "offering_gradebook":        (ALL, DENY, "core.change_grade",    OWN,        DENY),
    "enrollment_grade_editor":   (ALL, DENY, "core.change_grade",    OWN,        DENY),
    "student_register":          (ALL, ALL,  "core.add_student",     DENY,       DENY),
    "student_enroll":            (ALL, ALL,  "core.add_enrollment",  DENY,       DENY),
    "management_home":           (ALL, ALL,  DENY,                   DENY,       DENY),
    "management_records":        (ALL, ALL,  DENY,                   DENY,       DENY),
    "management_create":         (ALL, ALL,  DENY,                   DENY,       DENY),
    "management_edit":           (ALL, ALL,  DENY,                   DENY,       DENY),
    "management_account":        (ALL, ALL,  DENY,                   DENY,       DENY),
    "management_enrollment_status": (ALL, ALL, DENY,                 DENY,       DENY),
}
# Routes whose URL names a record; they are exercised for an in-scope and a foreign record.
SCOPED = {
    "student_detail", "student_outcomes", "offering_detail", "enrollment_outcomes",
    "enrollment_grade_history", "offering_gradebook", "enrollment_grade_editor",
    "student_enroll", "management_edit", "management_account", "management_enrollment_status",
}
# Routes that accept POST; every other protected route is GET-only (405 for an allowed role).
WRITABLE = {
    "offering_gradebook", "enrollment_grade_editor", "student_register", "student_enroll",
    "management_create", "management_edit", "management_account", "management_enrollment_status",
}
LEGACY_PERMISSIONS = ("core.view_grade", "core.change_grade", "core.add_student", "core.add_enrollment")

Actor = namedtuple("Actor", "label user role own staff_flag", defaults=((), False))
Records = namedtuple("Records", "student enrollment offering framework")


def academic_state():
    """Rows a rejected request must leave untouched, grade history (LogEntry) included."""
    users = get_user_model().objects.order_by("pk").values_list(
        "pk", "username", "password", "is_active", "is_staff", "is_superuser",
    )
    tables = (Student, Enrollment, Grade, LogEntry, Instructor, Course, CourseOffering, Program)
    return [list(model.objects.order_by("pk").values_list()) for model in tables] + [list(users)]


class RouteAccessMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        users = get_user_model().objects
        cls.password = token_urlsafe(24)
        cls.program = Program.objects.get(code="PILOT")
        framework = POFramework.objects.get(program=cls.program, version_number=1)
        own = Enrollment.objects.get(student__student_number="PILOT001", offering__course__code="PILOT311")
        foreign = Enrollment.objects.get(student__student_number="PILOT002", offering__course__code="PILOT321")
        # Scope "A" belongs to the signed-in instructor and student; scope "B" belongs to neither.
        cls.records = {
            "A": Records(own.student_id, own.pk, own.offering_id, framework.pk),
            "B": Records(foreign.student_id, foreign.pk, foreign.offering_id, framework.pk),
        }

        cls.coordinator_group = Group.objects.create(name=COORDINATOR_GROUP)
        cls.admin = users.create_superuser("matrix_admin", password=cls.password)
        cls.linked_admin = users.create_superuser("matrix_linked_admin", password=cls.password)
        Instructor.objects.create(full_name="Admin teaching record", email="admin@example.test",
                                  user=cls.linked_admin)
        cls.coordinator = users.create_user("matrix_coordinator", password=cls.password)
        cls.coordinator.groups.add(cls.coordinator_group)
        cls.legacy = users.create_user("matrix_legacy", password=cls.password, is_staff=True)
        cls.legacy_with = {}
        for perm in LEGACY_PERMISSIONS:
            user = users.create_user(f"matrix_legacy_{perm.split('.')[1]}", is_staff=True)
            user.user_permissions.add(Permission.objects.get(
                content_type__app_label="core", codename=perm.split(".")[1],
            ))
            cls.legacy_with[perm] = user

        cls.instructor = users.create_user("matrix_instructor", password=cls.password)
        Instructor.objects.filter(pk=own.offering.instructor_id).update(user=cls.instructor)
        cls.other_instructor = users.create_user("matrix_other_instructor", password=cls.password)
        other = Instructor.objects.create(full_name="Other instructor", email="other@example.test",
                                          user=cls.other_instructor)
        CourseOffering.objects.filter(pk=foreign.offering_id).update(instructor=other)
        cls.idle_instructor = users.create_user("matrix_idle_instructor", password=cls.password)
        Instructor.objects.create(full_name="Idle instructor", email="idle@example.test",
                                  user=cls.idle_instructor)
        cls.student = users.create_user("matrix_student", password=cls.password)
        Student.objects.filter(pk=own.student_id).update(user=cls.student)

        # A third offering both pilot students may still join, so enrollment payloads are valid.
        course = Course.objects.create(code="PILOT399", title="Matrix elective", credits=3)
        cls.open_offering = CourseOffering.objects.create(
            course=course, curriculum=CourseCurriculum.objects.create(course=course, version_number=1),
            instructor=other, po_framework=framework, year=2026, term="Fall", section="PILOT",
        )

        # Users with no single active academic role.
        cls.no_role = users.create_user("matrix_no_role", password=cls.password)
        cls.inactive_staff = users.create_user("matrix_inactive_staff", is_staff=True, is_active=False)
        cls.inactive_coordinator = users.create_user("matrix_inactive_coordinator", is_active=False)
        cls.inactive_coordinator.groups.add(cls.coordinator_group)
        cls.inactive_instructor = users.create_user("matrix_inactive_instructor", is_active=False)
        Instructor.objects.create(full_name="Inactive instructor", email="inactive@example.test",
                                  user=cls.inactive_instructor)
        cls.instructor_and_student = users.create_user("matrix_instructor_student")
        Instructor.objects.create(full_name="Dual instructor", email="dual@example.test",
                                  user=cls.instructor_and_student)
        Student.objects.create(full_name="Dual student", student_number="MATRIX-DUAL",
                               program=cls.program, user=cls.instructor_and_student)
        cls.coordinator_and_instructor = users.create_user("matrix_coordinator_instructor", is_staff=True)
        cls.coordinator_and_instructor.groups.add(cls.coordinator_group)
        Instructor.objects.create(full_name="Coordinating instructor", email="coord@example.test",
                                  user=cls.coordinator_and_instructor)

    # ----------------------------------------------------------------- helpers

    def url(self, name, scope="A"):
        r = self.records[scope]
        args = {
            "management_records": ["students"],
            "management_create": ["students"],
            "management_edit": ["students", r.student],
            "management_account": ["students", r.student],
            "management_enrollment_status": [r.enrollment],
            "student_detail": [r.student],
            "student_enroll": [r.student],
            "student_outcomes": [r.student, r.framework],
            "offering_detail": [r.offering],
            "offering_gradebook": [r.offering],
            "enrollment_outcomes": [r.enrollment],
            "enrollment_grade_editor": [r.enrollment],
            "enrollment_grade_history": [r.enrollment],
        }.get(name, [])
        return reverse(name, args=args)

    def scopes(self, name):
        return ("A", "B") if name in SCOPED else ("A",)

    @staticmethod
    def grade_fields(enrollment, user, prefix=None, change=True):
        """A complete, correctly signed grade form for ``user`` that changes every score."""
        assessments, grades, revision = snapshot(enrollment)

        def key(field):
            return f"{prefix}-{field}" if prefix else field

        data = {key("revision"): revision_token(enrollment, user, revision)}
        for assessment in assessments:
            grade = grades.get(assessment.pk)
            value = grade.score if grade else None
            if change:
                value = Decimal("1") if value != Decimal("1") else Decimal("2")
            data[key(f"score_{assessment.pk}")] = "" if value is None else str(value)
        return data

    def payload(self, name, scope, user):
        """A POST body that would change data if the access gate were missing."""
        r = self.records[scope]
        user = user or AnonymousUser()
        if name == "enrollment_grade_editor":
            return self.grade_fields(Enrollment.objects.get(pk=r.enrollment), user)
        if name == "offering_gradebook":
            data = {}
            for index, enrollment in enumerate(Enrollment.objects.filter(offering_id=r.offering).order_by("pk")):
                data.update(self.grade_fields(enrollment, user, prefix=f"e{enrollment.pk}", change=index == 0))
            return data
        if name in ("student_register", "management_create"):
            return {"full_name": "Matrix written student", "student_number": "MX-R" if name == "student_register" else "MX-C",
                    "program": self.program.pk}
        if name == "student_enroll":
            return {"offering": self.open_offering.pk}
        if name == "management_edit":
            student = Student.objects.get(pk=r.student)
            return {"full_name": "Tampered name", "student_number": student.student_number,
                    "program": student.program_id}
        if name == "management_account":
            if Student.objects.get(pk=r.student).user_id:
                return {"action": "disable"}
            return {"action": "create", "username": "matrix_new_login",
                    "password1": self.password, "password2": self.password}
        if name == "management_enrollment_status":
            return {"status": "withdrawn"}
        return {"status": "withdrawn", "score": "100"}

    def actors(self):
        A, B = {"A"}, {"B"}
        actors = [
            Actor("superuser", self.admin, "admin"),
            Actor("superuser_linked_to_instructor", self.linked_admin, "admin"),
            Actor("coordinator", self.coordinator, "coordinator"),
            Actor("coordinator_with_staff_flag", self.coordinator, "coordinator", staff_flag=True),
            Actor("legacy_staff", self.legacy, "legacy"),
            Actor("instructor_assigned", self.instructor, "instructor", A),
            Actor("instructor_with_staff_flag", self.instructor, "instructor", A, staff_flag=True),
            Actor("instructor_assigned_elsewhere", self.other_instructor, "instructor", B),
            Actor("instructor_without_offerings", self.idle_instructor, "instructor"),
            Actor("student", self.student, "student", A),
            Actor("student_with_staff_flag", self.student, "student", A, staff_flag=True),
        ]
        actors += [Actor(f"legacy_staff_{perm}", user, "legacy") for perm, user in self.legacy_with.items()]
        return actors

    def expected_get(self, actor, name, scope):
        """('status', code) or ('redirect', url) for this actor's GET."""
        rule = ACCESS[name][ROLES.index(actor.role)]
        if rule.startswith("core."):
            rule = ALL if actor.user.has_perm(rule) else DENY
        if rule == TO_COURSES:
            return "redirect", reverse("course_list")
        if rule == TO_OWN_DETAIL:
            return "redirect", self.url("student_detail", "A")
        if rule == ALL:
            return "status", 200
        if rule == OWN:
            return "status", 200 if scope in actor.own else 404
        return "status", 403

    def assert_login_redirect(self, response, url):
        self.assertRedirects(response, f"{reverse('login')}?next={url}", fetch_redirect_response=False)

    def assert_rejected_post(self, name, scope, user, check):
        url = self.url(name, scope)
        data = self.payload(name, scope, user)
        before = academic_state()
        response = self.client.post(url, data)
        check(response, url)
        self.assertEqual(academic_state(), before, "a rejected request changed academic data")

    # ------------------------------------------------------------------ tests

    def test_every_route_is_classified(self):
        names = {p.name for p in core_urls.urlpatterns if p.name}
        self.assertEqual(
            names, PUBLIC_ROUTES | set(ACCESS),
            "A core route was added or removed: classify it as public or give it a row in ACCESS.",
        )
        self.assertFalse(PUBLIC_ROUTES & set(ACCESS))
        self.assertLessEqual(SCOPED | WRITABLE, set(ACCESS))
        self.assertTrue(all(len(rules) == len(ROLES) for rules in ACCESS.values()))

    def test_users_without_one_active_role_are_sent_to_login(self):
        """Anonymous, inactive, role-less and conflicting-role users never reach a protected view."""
        users = [
            ("anonymous", None), ("active_no_role", self.no_role),
            ("inactive_staff", self.inactive_staff), ("inactive_coordinator", self.inactive_coordinator),
            ("inactive_instructor", self.inactive_instructor),
            # pending decision: signed-in users with missing or conflicting roles are sent to login, not 403.
            ("instructor_and_student", self.instructor_and_student),
            ("coordinator_and_instructor", self.coordinator_and_instructor),
        ]
        for label, user in users:
            self.client.logout()
            if user is not None:
                self.client.force_login(user)
            for name in ACCESS:
                for scope in self.scopes(name):
                    url = self.url(name, scope)
                    with self.subTest(user=label, route=name, scope=scope, method="GET"):
                        self.assert_login_redirect(self.client.get(url), url)
                    with self.subTest(user=label, route=name, scope=scope, method="POST"):
                        self.assert_rejected_post(name, scope, user, self.assert_login_redirect)

    def test_role_matrix_for_get_and_denied_post(self):
        """Every role on every protected route, for its own and a foreign record."""
        User = get_user_model()
        for actor in self.actors():
            if actor.staff_flag:
                User.objects.filter(pk=actor.user.pk).update(is_staff=True)
            user = User.objects.get(pk=actor.user.pk)
            self.client.force_login(user)
            for name in ACCESS:
                for scope in self.scopes(name):
                    kind, value = self.expected_get(actor._replace(user=user), name, scope)
                    url = self.url(name, scope)
                    with self.subTest(actor=actor.label, route=name, scope=scope, method="GET"):
                        response = self.client.get(url)
                        if kind == "redirect":
                            self.assertRedirects(response, value, fetch_redirect_response=False)
                        else:
                            self.assertEqual(response.status_code, value)

                    if kind == "redirect" or value == 200:
                        if name in WRITABLE:
                            continue  # a permitted write; see test_write_payloads_change_data
                        status = 405
                    elif value == 404 and name not in WRITABLE:
                        status = 405  # method check precedes the record lookup; no existence leak
                    else:
                        status = value
                    with self.subTest(actor=actor.label, route=name, scope=scope, method="POST"):
                        self.assert_rejected_post(
                            name, scope, user,
                            lambda response, url, status=status: self.assertEqual(response.status_code, status),
                        )
            if actor.staff_flag:
                User.objects.filter(pk=actor.user.pk).update(is_staff=False)

    def test_write_payloads_change_data_for_authorized_users(self):
        """Positive control: the payloads used in denial tests really write when access is granted."""
        cases = [(self.admin, name, scope) for name in sorted(WRITABLE) for scope in self.scopes(name)]
        cases += [(self.coordinator, name, scope) for name in sorted(WRITABLE - {
            "offering_gradebook", "enrollment_grade_editor"}) for scope in self.scopes(name)]
        cases += [(self.instructor, "offering_gradebook", "A"), (self.instructor, "enrollment_grade_editor", "A"),
                  (self.other_instructor, "enrollment_grade_editor", "B")]
        cases += [(self.legacy_with["core.change_grade"], "enrollment_grade_editor", "B"),
                  (self.legacy_with["core.change_grade"], "offering_gradebook", "A"),
                  (self.legacy_with["core.add_student"], "student_register", "A"),
                  (self.legacy_with["core.add_enrollment"], "student_enroll", "B")]
        for user, name, scope in cases:
            with self.subTest(user=user.username, route=name, scope=scope), transaction.atomic():
                self.client.force_login(user)
                before = academic_state()
                response = self.client.post(self.url(name, scope), self.payload(name, scope, user))
                self.assertEqual(response.status_code, 302, getattr(response, "context", None)
                                 and response.context.get("form") and response.context["form"].errors)
                self.assertNotEqual(academic_state(), before)
                transaction.set_rollback(True)

    def test_grade_writes_record_history_only_when_permitted(self):
        """A permitted grade save adds history rows; the same payload from an outsider adds none."""
        enrollment = Enrollment.objects.get(pk=self.records["A"].enrollment)
        url = self.url("enrollment_grade_editor", "A")
        history = LogEntry.objects.count()
        for user in (self.other_instructor, self.coordinator, self.student, self.legacy):
            self.client.force_login(user)
            self.client.post(url, self.grade_fields(enrollment, user))
        self.assertEqual(LogEntry.objects.count(), history)
        self.client.force_login(self.instructor)
        self.assertEqual(self.client.post(url, self.grade_fields(enrollment, self.instructor)).status_code, 302)
        self.assertGreater(LogEntry.objects.count(), history)

    def test_course_list_shows_only_assigned_offerings(self):
        expected = {
            self.instructor: {self.records["A"].offering},
            self.other_instructor: {self.records["B"].offering, self.open_offering.pk},
            self.idle_instructor: set(),
            self.coordinator: set(CourseOffering.objects.values_list("pk", flat=True)),
        }
        for user, offerings in expected.items():
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse("course_list"))
                self.assertEqual({o.pk for o in response.context["offerings"]}, offerings)

    def test_tampered_management_identifiers_are_not_found(self):
        self.client.force_login(self.coordinator)
        missing = Student.objects.order_by("-pk").first().pk + 1000
        missing_enrollment = Enrollment.objects.order_by("-pk").first().pk + 1000
        self.assertEqual(self.client.get(reverse("management_records", args=["users"])).status_code, 404)
        for url in (
            reverse("management_create", args=["users"]),
            reverse("management_edit", args=["students", missing]),
            reverse("management_account", args=["students", missing]),
            reverse("management_account", args=["programs", self.program.pk]),
            reverse("management_enrollment_status", args=[missing_enrollment]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
                before = academic_state()
                response = self.client.post(url, {
                    "username": "matrix_escalated", "password1": self.password, "password2": self.password,
                    "action": "create", "status": "withdrawn", "full_name": "Tampered",
                    "student_number": "MATRIX-T", "program": self.program.pk, "is_superuser": "on",
                })
                self.assertEqual(response.status_code, 404)
                self.assertEqual(academic_state(), before)

    def test_csrf_rejection_preserves_academic_state(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        for name in sorted(WRITABLE):
            with self.subTest(route=name):
                before = academic_state()
                response = client.post(self.url(name), self.payload(name, "A", self.admin))
                self.assertEqual(response.status_code, 403)
                self.assertEqual(academic_state(), before)


class AuthenticationRouteTests(TestCase):
    """The two intentionally public routes and the separate admin sign-in boundary."""

    @classmethod
    def setUpTestData(cls):
        cls.password = token_urlsafe(24)
        users = get_user_model().objects
        cls.user = users.create_user("auth_coordinator", password=cls.password)
        cls.user.groups.add(Group.objects.create(name=COORDINATOR_GROUP))
        cls.inactive = users.create_user("auth_inactive", password=cls.password, is_active=False)

    def sign_in(self, username, next_url=None):
        url = reverse("login") + (f"?next={next_url}" if next_url else "")
        return self.client.post(url, {"username": username, "password": self.password,
                                      **({"next": next_url} if next_url else {})})

    def test_login_form_is_public(self):
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)

    def test_successful_login_redirects_to_safe_destination(self):
        cases = {
            None: reverse("student_list"),
            reverse("course_list"): reverse("course_list"),
            "https://attacker.example/": reverse("student_list"),
            "//attacker.example/": reverse("student_list"),
        }
        for next_url, destination in cases.items():
            with self.subTest(next=next_url):
                self.client.logout()
                self.assertRedirects(self.sign_in(self.user.username, next_url), destination,
                                     fetch_redirect_response=False)
                self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_failed_login_redisplays_form_without_session(self):
        for label, data in (
            ("wrong_password", {"username": self.user.username, "password": "not-the-password"}),
            ("unknown_user", {"username": "nobody", "password": self.password}),
            ("inactive_user", {"username": self.inactive.username, "password": self.password}),
        ):
            with self.subTest(case=label):
                response = self.client.post(reverse("login"), data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertNotIn(SESSION_KEY, self.client.session)

    def test_logout_requires_post_and_ends_session(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        self.assertNotIn(SESSION_KEY, self.client.session)
        protected = reverse("course_list")
        self.assertRedirects(self.client.get(protected), f"{reverse('login')}?next={protected}",
                             fetch_redirect_response=False)

    def test_django_admin_keeps_its_own_login(self):
        admin = reverse("admin:index")
        self.assertRedirects(self.client.get(admin), f"{reverse('admin:login')}?next={admin}",
                             fetch_redirect_response=False)
