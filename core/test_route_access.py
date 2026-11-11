"""Access-control matrix for every page of the staff application.

Instead of checking routes one by one, these tests walk ``core.urls`` so that a
newly added page without login/permission protection fails the suite.
"""
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
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
            names, set(ROUTE_PERMISSIONS),
            "A route was added or removed: update ROUTE_PERMISSIONS with its access rule.",
        )

    def test_anonymous_non_staff_and_inactive_users_are_sent_to_login(self):
        for label, user in (("anonymous", None), ("non_staff", self.non_staff),
                            ("inactive_staff", self.inactive)):
            self.client.logout()
            if user is not None:
                self.client.force_login(user)
            for name in ROUTE_PERMISSIONS:
                url = self.url(name)
                with self.subTest(user=label, route=name):
                    response = self.client.get(url)
                    self.assertRedirects(
                        response, f"{reverse('admin:login')}?next={url}",
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
        before = (Student.objects.count(), Enrollment.objects.count(),
                  list(Grade.objects.order_by("pk").values_list("pk", "score")))
        for label, user in (("anonymous", None), ("plain_staff", self.plain_staff)):
            self.client.logout()
            if user is not None:
                self.client.force_login(user)
            for name, codename in ROUTE_PERMISSIONS.items():
                if codename is None:
                    continue
                with self.subTest(user=label, route=name):
                    response = self.client.post(self.url(name), {
                        "full_name": "Should Not Exist", "student_number": "X999",
                    })
                    self.assertIn(response.status_code, (302, 403))
        after = (Student.objects.count(), Enrollment.objects.count(),
                 list(Grade.objects.order_by("pk").values_list("pk", "score")))
        self.assertEqual(after, before)
