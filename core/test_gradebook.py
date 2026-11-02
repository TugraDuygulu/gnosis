from io import StringIO

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from core.models import CourseOffering, Grade


class OfferingGradebookTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.offering = CourseOffering.objects.get(course__code="PILOT321")
        cls.lab = cls.offering.assessments.get(name="Lab")
        cls.midterm = cls.offering.assessments.get(name="Midterm")
        cls.a = cls.offering.enrollments.get(student__student_number="PILOT001")
        cls.b = cls.offering.enrollments.get(student__student_number="PILOT002")
        cls.editor = get_user_model().objects.create_user(username="book_editor", is_staff=True)
        cls.editor.user_permissions.add(Permission.objects.get(
            content_type__app_label="core", codename="change_grade",
        ))

    def setUp(self):
        self.client.force_login(self.editor)
        self.url = reverse("offering_gradebook", args=[self.offering.pk])

    def payload(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = {}
        for row in response.context["rows"]:
            for field in row["form"]:
                value = field.value()
                data[field.html_name] = "" if value is None else str(value)
        return data

    def score(self, enrollment, assessment):
        grade = Grade.objects.filter(enrollment=enrollment, assessment=assessment).first()
        return None if grade is None else grade.score

    def test_lists_every_student_and_assessment(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Pilot Student A")
        self.assertContains(response, "Pilot Student B")
        self.assertContains(response, f'name="e{self.a.pk}-score_{self.lab.pk}"')
        self.assertContains(response, f'name="e{self.b.pk}-score_{self.midterm.pk}"')
        roster = self.client.get(reverse("offering_detail", args=[self.offering.pk]))
        self.assertContains(roster, self.url)

    def test_saves_only_changed_students_and_records_history(self):
        before_b = self.score(self.b, self.lab)
        data = self.payload()
        data[f"e{self.a.pk}-score_{self.lab.pk}"] = "35"
        response = self.client.post(self.url, data, follow=True)
        self.assertRedirects(response, self.url)
        self.assertContains(response, "Grades saved for 1 student")
        self.assertEqual(self.score(self.a, self.lab), 35)
        self.assertEqual(self.score(self.b, self.lab), before_b)
        self.assertEqual(LogEntry.objects.count(), 1)

    def test_invalid_cell_saves_nothing(self):
        data = self.payload()
        data[f"e{self.a.pk}-score_{self.midterm.pk}"] = "70"
        data[f"e{self.b.pk}-score_{self.lab.pk}"] = "60"  # above the 50 maximum
        response = self.client.post(self.url, data)
        self.assertContains(response, "Nothing was saved")
        self.assertEqual(self.score(self.a, self.midterm), 0)
        self.assertEqual(LogEntry.objects.count(), 0)

    def test_stale_student_rolls_back_the_whole_save(self):
        data = self.payload()
        data[f"e{self.a.pk}-score_{self.lab.pk}"] = "35"
        data[f"e{self.b.pk}-score_{self.midterm.pk}"] = "55"
        Grade.objects.filter(enrollment=self.b, assessment=self.lab).update(score=10)
        response = self.client.post(self.url, data)
        self.assertContains(response, "changed since you opened")
        self.assertIsNone(self.score(self.a, self.lab))
        self.assertEqual(LogEntry.objects.count(), 0)

    def test_requires_change_grade_permission(self):
        viewer = get_user_model().objects.create_user(username="book_viewer", is_staff=True)
        client = Client()
        client.force_login(viewer)
        self.assertEqual(client.get(self.url).status_code, 403)
        self.assertNotContains(client.get(reverse("offering_detail", args=[self.offering.pk])), self.url)
        self.assertEqual(Client().get(self.url).status_code, 302)
