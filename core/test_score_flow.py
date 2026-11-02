from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import Enrollment


class ScoreFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.user = get_user_model().objects.create_user(username="flow_viewer", is_staff=True)

    def flow(self, course_code):
        enrollment = Enrollment.objects.get(student__student_number="PILOT001", offering__course__code=course_code)
        self.client.force_login(self.user)
        response = self.client.get(reverse("enrollment_outcomes", args=[enrollment.pk]))
        self.assertContains(response, "How the scores flow")
        return response.context["flow"]

    def test_brief_example_weights_are_drawn(self):
        flow = self.flow("PILOT311")
        titles = [node["title"] for node in flow["nodes"]]
        self.assertEqual(titles, ["Midterm", "Project", "LO1", "LO2", "PO2", "PO3"])
        labels = sorted(edge["label"] for edge in flow["edges"])
        self.assertEqual(labels, sorted(["60%", "40%", "40%", "100%", "2/5", "1/5", "5/5"]))
        lo1 = next(node for node in flow["nodes"] if node["title"] == "LO1")
        self.assertEqual(lo1["value"], "86.00%")

    def test_ungraded_assessment_is_marked_missing_down_the_chain(self):
        flow = self.flow("PILOT321")
        lab = next(node for node in flow["nodes"] if node["title"] == "Lab")
        self.assertTrue(lab["missing"])
        self.assertEqual(lab["value"], "Not graded")
        dashed = [edge for edge in flow["edges"] if edge["missing"]]
        self.assertEqual(len(dashed), 3)  # Lab → LO2, LO2 → PO2, LO2 → PO5
