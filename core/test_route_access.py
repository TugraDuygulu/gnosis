"""Access-control matrix for every page of the academic application.

Instead of checking routes one by one, these tests walk ``core.urls`` so that a
newly added page without login/permission protection fails the suite.
"""
from io import StringIO

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from core import urls as core_urls
from core.models import Enrollment, Grade, POFramework, Student

# Route name -> permission codename required on top of active staff (None = staff only).
ROUTE_PERMISSIONS = {
    "student_list": None,
    "student_register": "add_student",
    "student_detail": None,
    "student_enroll": "add_enrollment",
    "student_outcomes": None,
    "course_list": None,
    "offering_detail": None,
    "offering_gradebook": "change_grade",
    "program_overview": None,
    "enrollment_outcomes": None,
    "enrollment_grade_editor": "change_grade",
    "enrollment_grade_history": "view_grade",
}


AUTH_ROUTES = {"login", "logout"}
MANAGEMENT = {"management_home", "management_records", "management_create",
              "management_edit", "management_account", "management_enrollment_status"}


def academic_state():
    return [list(model.objects.order_by("pk").values_list())
            for model in (Student, Enrollment, Grade, LogEntry)]


class RouteAccessMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.enrollment = Enrollment.objects.select_related("student", "offering").get(
            student__student_number="PILOT001", offering__course__code="PILOT321",
        )
        cls.framework = POFramework.objects.get(program__code="PILOT", version_number=1)
        users = get_user_model().objects
        cls.non_staff = users.create_user(username="regular", is_staff=False)
        cls.inactive = users.create_user(username="inactive", is_staff=True, is_active=False)
        cls.plain_staff = users.create_user(username="plain_staff", is_staff=True)

    def url(self, name):
        e = self.enrollment
        args = {
            "management_records": ["students"],
            "management_create": ["students"],
            "management_edit": ["students", e.student_id],
            "management_account": ["students", e.student_id],
            "management_enrollment_status": [e.pk],
            "student_detail": [e.student_id],
            "student_enroll": [e.student_id],
            "student_outcomes": [e.student_id, self.framework.pk],
            "offering_detail": [e.offering_id],
            "offering_gradebook": [e.offering_id],
            "enrollment_outcomes": [e.pk],
            "enrollment_grade_editor": [e.pk],
            "enrollment_grade_history": [e.pk],
        }.get(name, [])
        return reverse(name, args=args)

    def staff_with(self, codename):
        user, _ = get_user_model().objects.get_or_create(username=f"has_{codename}", is_staff=True)
        user.user_permissions.add(Permission.objects.get(
            content_type__app_label="core", codename=codename,
        ))
        return user

    def test_every_route_is_listed_in_the_matrix(self):
        names = {p.name for p in core_urls.urlpatterns if p.name}
        self.assertEqual(
            names, set(ROUTE_PERMISSIONS) | MANAGEMENT | AUTH_ROUTES,
            "A route was added or removed: update ROUTE_PERMISSIONS with its access rule.",
        )

    def test_anonymous_non_staff_and_inactive_users_are_sent_to_login(self):
        for label, user in (("anonymous", None), ("non_staff", self.non_staff),
                            ("inactive_staff", self.inactive)):
            self.client.logout()
            if user is not None:
                self.client.force_login(user)
            for name in set(ROUTE_PERMISSIONS) | MANAGEMENT:
                url = self.url(name)
                with self.subTest(user=label, route=name):
                    response = self.client.get(url)
                    self.assertRedirects(
                        response, f"{reverse('login')}?next={url}",
                        fetch_redirect_response=False,
                    )

    def test_staff_without_permission_gets_403_on_protected_routes(self):
        self.client.force_login(self.plain_staff)
        for name, codename in ROUTE_PERMISSIONS.items():
            with self.subTest(route=name):
                status = self.client.get(self.url(name)).status_code
                self.assertEqual(status, 200 if codename is None else 403)

    def test_matching_permission_opens_each_protected_route(self):
        for name, codename in ROUTE_PERMISSIONS.items():
            if codename is None:
                continue
            with self.subTest(route=name, permission=codename):
                self.client.force_login(self.staff_with(codename))
                self.assertEqual(self.client.get(self.url(name)).status_code, 200)
                self.client.logout()

    def test_unauthorized_posts_change_nothing(self):
        before = academic_state()
        for user, status in ((None, 302), (self.plain_staff, 403)):
            self.client.logout()
            if user:
                self.client.force_login(user)
            routes = MANAGEMENT | {name for name, perm in ROUTE_PERMISSIONS.items() if perm}
            for name in routes:
                with self.subTest(route=name, status=status):
                    response = self.client.post(self.url(name), {"status": "withdrawn"})
                    self.assertEqual(response.status_code, status)
                    self.assertEqual(academic_state(), before)

    def test_csrf_rejection_preserves_academic_state(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(get_user_model().objects.create_superuser("matrix_admin"))
        before = academic_state()
        response = client.post(self.url("management_enrollment_status"), {"status": "withdrawn"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(academic_state(), before)

    def test_authentication_routes_and_admin_redirect(self):
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        admin = reverse("admin:index")
        self.assertRedirects(self.client.get(admin), f"{reverse('admin:login')}?next={admin}",
                             fetch_redirect_response=False)
