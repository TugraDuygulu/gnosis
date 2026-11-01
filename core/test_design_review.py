from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import Enrollment


class MissingGradeLinkTests(TestCase):
    """Regression: "Enter grade" opens the editor at the missing assessment."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.enrollment = Enrollment.objects.get(
            student__student_number="PILOT001",
            offering__course__code="PILOT321",
        )
        cls.lab = cls.enrollment.offering.assessments.get(name="Lab")
        cls.editor = get_user_model().objects.create_user(username="design_editor", is_staff=True)
        cls.editor.user_permissions.add(Permission.objects.get(
            content_type__app_label="core", codename="change_grade",
        ))

    def setUp(self):
        self.client.force_login(self.editor)
        self.target = (
            reverse("enrollment_grade_editor", args=[self.enrollment.pk])
            + f"#id_score_{self.lab.pk}"
        )

    def test_profile_and_evidence_link_to_the_missing_field(self):
        profile = reverse("student_outcomes", args=[
            self.enrollment.student_id, self.enrollment.offering.po_framework_id,
        ])
        for url in (profile, reverse("enrollment_outcomes", args=[self.enrollment.pk])):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), self.target)

    def test_editor_renders_the_targeted_field_for_the_live_preview(self):
        response = self.client.get(reverse("enrollment_grade_editor", args=[self.enrollment.pk]))
        self.assertContains(response, f'id="id_score_{self.lab.pk}"')
        self.assertContains(response, 'data-max="50.00"')
        self.assertContains(response, f'id="id_score_{self.lab.pk}_live"')
