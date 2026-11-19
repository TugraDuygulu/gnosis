"""Each role lands on its own workspace, sees only its controls, and gets clear
feedback when a page is denied, hidden, or the account has no role."""
from io import StringIO
from secrets import token_urlsafe

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.access import COORDINATOR_GROUP
from core.models import CourseOffering, Grade, Instructor


class RoleNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.offering = CourseOffering.objects.get(course__code="PILOT311")
        cls.enrollment, cls.peer = cls.offering.enrollments.order_by("student__student_number")
        other = CourseOffering.objects.get(course__code="PILOT321")
        other.instructor = Instructor.objects.create(full_name="Other instructor", email="other@example.test")
        other.save(update_fields=["instructor"])
        cls.password = token_urlsafe(24)
        users = get_user_model().objects
        cls.coordinator = users.create_user(username="nav_coordinator", password=cls.password)
        cls.coordinator.groups.add(Group.objects.create(name=COORDINATOR_GROUP))
        cls.instructor = users.create_user(username="nav_instructor", password=cls.password)
        cls.offering.instructor.user = cls.instructor
        cls.offering.instructor.save(update_fields=["user"])
        cls.student = users.create_user(username="nav_student", password=cls.password)
        cls.enrollment.student.user = cls.student
        cls.enrollment.student.save(update_fields=["user"])
        cls.no_role = users.create_user(username="nav_norole", password=cls.password)

    def test_each_role_sees_its_own_navigation(self):
        self.client.force_login(self.coordinator)
        page = self.client.get(reverse("student_list"))
        self.assertContains(page, '<span class="role">Coordinator</span>', html=True)
        self.assertContains(page, "Academic management")
        self.assertContains(page, "Search students")

        self.client.force_login(self.instructor)
        page = self.client.get(reverse("course_list"))
        self.assertContains(page, '<span class="role">Instructor</span>', html=True)
        self.assertContains(page, "<h1>My courses</h1>", html=True)
        self.assertNotContains(page, "Academic management")
        self.assertNotContains(page, "Search students")

        self.client.force_login(self.student)
        page = self.client.get(reverse("student_list"), follow=True)
        self.assertContains(page, '<span class="role">Student</span>', html=True)
        self.assertContains(page, 'aria-current="page" href="/">')
        self.assertNotContains(page, "Search students")
        self.assertNotContains(page, 'class="crumbs"')

    def test_hidden_controls_are_also_denied_by_the_server(self):
        self.client.force_login(self.instructor)
        self.assertNotContains(self.client.get(reverse("course_list")), reverse("management_home"))
        self.assertEqual(self.client.get(reverse("management_home")).status_code, 403)

        self.client.force_login(self.student)
        evidence = self.client.get(reverse("enrollment_outcomes", args=[self.enrollment.pk]))
        editor = reverse("enrollment_grade_editor", args=[self.enrollment.pk])
        self.assertNotContains(evidence, editor)
        before = list(Grade.objects.order_by("pk").values_list("pk", "score"))
        self.assertEqual(self.client.get(editor).status_code, 403)
        self.assertEqual(self.client.post(editor, {"revision": "x"}).status_code, 403)
        self.assertEqual(list(Grade.objects.order_by("pk").values_list("pk", "score")), before)

    def test_denied_page_explains_and_offers_a_way_back(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse("offering_gradebook", args=[self.offering.pk]), {})
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")
        self.assertContains(response, "You don’t have access to this page", status_code=403)
        self.assertContains(response, "Your student account", status_code=403)
        self.assertContains(response, f'href="{reverse("student_list")}">Go to my workspace', status_code=403)

    def test_hidden_record_shows_the_not_found_page(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("student_detail", args=[self.peer.student_id]))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Page not found", status_code=404)
        self.assertNotContains(response, self.peer.student.full_name, status_code=404)

    def test_account_without_a_role_is_told_why(self):
        self.client.post(reverse("login"), {"username": "nav_norole", "password": self.password})
        response = self.client.get(reverse("student_list"), follow=True)
        self.assertEqual(response.redirect_chain[-1][0], f"{reverse('login')}?next=/")
        self.assertContains(response, "nav_norole isn’t linked to one Gnosis role")

    def test_sign_out_is_confirmed_on_the_sign_in_page(self):
        self.client.force_login(self.coordinator)
        response = self.client.post(reverse("logout"), follow=True)
        self.assertEqual(response.redirect_chain[-1][0], reverse("login"))
        self.assertContains(response, "You’ve signed out.")
        self.assertFalse(response.context["user"].is_authenticated)

    def test_django_admin_sign_in_explains_missing_admin_access(self):
        self.client.force_login(self.coordinator)
        response = self.client.get(reverse("admin:index"), follow=True)
        self.assertContains(response, "nav_coordinator (coordinator) can’t open Django Admin")

    def test_instructor_breadcrumbs_lead_back_to_my_courses(self):
        self.client.force_login(self.instructor)
        for name, pk in (("offering_detail", self.offering.pk), ("offering_gradebook", self.offering.pk),
                         ("enrollment_outcomes", self.enrollment.pk)):
            with self.subTest(page=name):
                page = self.client.get(reverse(name, args=[pk]))
                self.assertContains(page, f'<a href="{reverse("course_list")}">My courses</a>', html=True)

    def test_management_pages_are_marked_and_labelled(self):
        self.client.force_login(self.coordinator)
        pages = {
            "home": reverse("management_home"),
            "records": reverse("management_records", args=["students"]),
            "new login": reverse("management_account", args=["students", self.peer.student_id]),
            "offering": reverse("management_edit", args=["offerings", self.offering.pk]),
        }
        for label, url in pages.items():
            with self.subTest(page=label):
                page = self.client.get(url)
                self.assertEqual(page.content.decode().count("<h1"), 1)
                self.assertContains(page, "Academic management</a>")
                self.assertContains(page, "nav on")
                self.assertNotContains(page, ":</label>")
        home = self.client.get(pages["home"])
        self.assertContains(home, "1 of 2 can sign in")
        records = self.client.get(pages["records"])
        self.assertContains(records, "nav_student")
        self.assertContains(records, "None yet")
        self.assertContains(self.client.get(pages["offering"]), ">PO framework</label>")
