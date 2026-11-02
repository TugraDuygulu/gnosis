from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from core.models import POFramework, Student
from core.services.student_po_calculator import calculate_student_po_achievement


class ProgramOverviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.framework = POFramework.objects.get(program__code="PILOT")
        cls.user = get_user_model().objects.create_user(username="head", is_staff=True)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("program_overview") + f"?framework={self.framework.pk}"

    def test_averages_match_the_student_calculator(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Pilot Student A")
        self.assertContains(response, "Pilot Student B")
        po3 = self.framework.program_outcomes.get(code="PO3")
        scores = [
            calculate_student_po_achievement(student, po3)["score"]
            for student in Student.objects.filter(program=self.framework.program)
        ]
        scores = [score for score in scores if score is not None]
        item = next(row for row in response.context["summary"] if row["outcome"] == po3)
        self.assertEqual(item["scored"], len(scores))
        self.assertEqual(item["average"], sum(scores) / len(scores))

    def test_unmeasured_outcomes_have_no_average_and_missing_grades_are_counted(self):
        response = self.client.get(self.url)
        po11 = next(row for row in response.context["summary"] if row["outcome"].code == "PO11")
        self.assertIsNone(po11["average"])
        expected = sum(row["expected"] - row["graded"] for row in response.context["classes"])
        self.assertEqual(response.context["missing_total"], expected)
        self.assertGreaterEqual(expected, 1)  # Pilot Student A's Lab is ungraded

    def test_staff_only(self):
        self.assertEqual(Client().get(self.url).status_code, 302)
        self.assertContains(self.client.get(reverse("student_list")), reverse("program_overview"))
