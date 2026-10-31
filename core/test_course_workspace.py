from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import CourseOffering, Enrollment, Program, Student


class CourseWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.offering = CourseOffering.objects.get(course__code="PILOT321")
        cls.staff = get_user_model().objects.create_user(username="reader", is_staff=True)
        cls.editor = get_user_model().objects.create_user(username="editor", is_staff=True)
        cls.editor.user_permissions.add(Permission.objects.get(
            content_type__app_label="core", codename="change_grade",
        ))

    def setUp(self):
        self.client.force_login(self.staff)
        self.list_url = reverse("course_list")
        self.roster_url = reverse("offering_detail", args=[self.offering.pk])

    def new_section(self, **kwargs):
        values = {
            "course": self.offering.course, "curriculum": self.offering.curriculum,
            "instructor": self.offering.instructor, "year": 2027,
            "term": "Spring", "section": "B", "po_framework": self.offering.po_framework,
        }
        values.update(kwargs)
        return CourseOffering.objects.create(**values)

    def test_offering_list_distinguishes_sections_and_enrollment_counts(self):
        second = self.new_section()
        response = self.client.get(self.list_url)
        self.assertContains(response, self.roster_url)
        self.assertContains(response, reverse("offering_detail", args=[second.pk]))
        self.assertContains(response, "Spring 2027")
        rows = {offering.pk: offering for offering in response.context["offerings"]}
        self.assertEqual(rows[self.offering.pk].enrollment_count, 2)
        self.assertEqual(rows[self.offering.pk].active_count, 2)
        self.assertEqual(rows[second.pk].enrollment_count, 0)

    def test_search_finds_code_title_instructor_year_term_and_section(self):
        self.new_section()
        for query in ("pilot321", "Data Systems", "Fictional Pilot Instructor", "2027", "Spring", "B"):
            with self.subTest(query=query):
                response = self.client.get(self.list_url, {"q": query})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["offerings"])
        response = self.client.get(self.list_url, {"q": "2027"})
        self.assertEqual([o.year for o in response.context["offerings"]], [2027])
        response = self.client.get(self.list_url, {"q": '<script>alert("x")</script>'})
        self.assertContains(response, "No matching course offerings")
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "Clear search")

    def test_roster_has_only_its_enrollments_and_matching_links(self):
        foreign = Student.objects.create(
            program=self.offering.po_framework.program,
            student_number="OTHER001", full_name="Other Section Only",
        )
        Enrollment.objects.create(student=foreign, offering=self.new_section())
        response = self.client.get(self.roster_url)
        self.assertContains(response, "Pilot Student A")
        self.assertContains(response, "Pilot Student B")
        self.assertNotContains(response, "Other Section Only")
        for enrollment in self.offering.enrollments.all():
            self.assertContains(response, reverse("enrollment_outcomes", args=[enrollment.pk]))
            self.assertContains(response, reverse("student_outcomes", args=[
                enrollment.student_id, self.offering.po_framework_id,
            ]))
            self.assertNotContains(response, reverse("enrollment_grade_editor", args=[enrollment.pk]))
        self.client.force_login(self.editor)
        response = self.client.get(self.roster_url)
        for enrollment in self.offering.enrollments.all():
            self.assertContains(response, reverse("enrollment_grade_editor", args=[enrollment.pk]))

    def test_inactive_enrollments_are_visible_without_changing_calculation_policy(self):
        enrollment = self.offering.enrollments.first()
        enrollment.status = "withdrawn"
        enrollment.save()
        response = self.client.get(self.roster_url)
        self.assertContains(response, "withdrawn")
        self.assertEqual(len(response.context["enrollments"]), 2)
        response = self.client.get(self.list_url)
        row = next(o for o in response.context["offerings"] if o.pk == self.offering.pk)
        self.assertEqual(row.enrollment_count, 2)
        self.assertEqual(row.active_count, 1)

    def test_missing_or_incompatible_framework_does_not_link_to_invalid_profile(self):
        offering = self.new_section(po_framework=None)
        enrollment = Enrollment.objects.create(
            student=self.offering.enrollments.first().student, offering=offering,
        )
        response = self.client.get(reverse("offering_detail", args=[offering.pk]))
        self.assertContains(response, "No program outcome framework assigned")
        self.assertContains(response, reverse("enrollment_outcomes", args=[enrollment.pk]))
        self.assertContains(response, "No compatible student outcome profile")
        other_program = Program.objects.create(code="OTHER", name="Other Program")
        student = Student.objects.create(program=other_program, student_number="OTHER002", full_name="Transfer Example")
        enrollment = Enrollment.objects.create(student=student, offering=self.offering)
        invalid_profile = reverse("student_outcomes", args=[student.pk, self.offering.po_framework_id])
        self.assertNotContains(self.client.get(self.roster_url), invalid_profile)
        self.assertNotContains(self.client.get(reverse("enrollment_outcomes", args=[enrollment.pk])), invalid_profile)

    def test_navigation_returns_to_exact_roster_from_evidence_and_editor(self):
        enrollment = self.offering.enrollments.first()
        self.client.force_login(self.editor)
        for url in (reverse("enrollment_outcomes", args=[enrollment.pk]),
                    reverse("enrollment_grade_editor", args=[enrollment.pk]),
                    reverse("student_outcomes", args=[enrollment.student_id, self.offering.po_framework_id]),
                    reverse("student_list")):
            response = self.client.get(url)
            self.assertContains(response, self.list_url)
        for name in ("enrollment_outcomes", "enrollment_grade_editor"):
            self.assertContains(self.client.get(reverse(name, args=[enrollment.pk])), self.roster_url)

    def test_empty_roster_unknown_offering_and_read_only_requests(self):
        empty = self.new_section()
        response = self.client.get(reverse("offering_detail", args=[empty.pk]))
        self.assertContains(response, "No students enrolled")
        self.assertNotContains(response, reverse("admin:core_enrollment_add"))
        self.assertEqual(self.client.get(reverse("offering_detail", args=[999999])).status_code, 404)
        for url in (self.list_url, self.roster_url):
            self.assertEqual(self.client.post(url, {"status": "withdrawn"}).status_code, 405)

    def test_access_requires_active_staff(self):
        for label, user in (
            ("anonymous", None),
            ("regular", get_user_model().objects.create_user(username="regular")),
            ("inactive", get_user_model().objects.create_user(username="inactive", is_staff=True, is_active=False)),
        ):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for url in (self.list_url, self.roster_url):
                with self.subTest(user=label, url=url):
                    self.assertRedirects(self.client.get(url), f"{reverse('admin:login')}?next={url}", fetch_redirect_response=False)
