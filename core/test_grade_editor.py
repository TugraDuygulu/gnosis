from decimal import Decimal
from io import StringIO
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Assessment, Enrollment, Grade, ProgramOutcome
from core.services.student_po_calculator import calculate_student_po_achievement


class EnrollmentGradeEditorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.enrollment = Enrollment.objects.get(
            student__student_number="PILOT001",
            offering__course__code="PILOT321",
        )
        cls.assessments = list(cls.enrollment.offering.assessments.order_by("pk"))
        cls.midterm = next(a for a in cls.assessments if a.name == "Midterm")
        cls.lab = next(a for a in cls.assessments if a.name == "Lab")
        cls.editor = get_user_model().objects.create_user(
            username="grade_editor", is_staff=True,
        )
        cls.editor.user_permissions.add(Permission.objects.get(
            content_type__app_label="core", codename="change_grade",
        ))

    def setUp(self):
        self.client.force_login(self.editor)
        self.url = reverse("enrollment_grade_editor", args=[self.enrollment.pk])

    def payload(self, client=None, url=None):
        response = (client or self.client).get(url or self.url)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        return {field.name: "" if field.value() is None else str(field.value())
                for field in form}

    def scores(self):
        return list(Grade.objects.order_by("pk").values_list("pk", "score"))

    def test_context_and_link_are_scoped_to_enrollment(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Pilot Student A")
        self.assertContains(response, "PILOT321")
        self.assertContains(response, "Out of 50.00")
        self.assertEqual(set(response.context["form"].fields), {
            "revision", f"score_{self.midterm.pk}", f"score_{self.lab.pk}",
        })
        evidence = self.client.get(reverse("enrollment_outcomes", args=[self.enrollment.pk]))
        self.assertContains(evidence, self.url)

    def test_save_recalculates_and_preserves_other_students_and_courses(self):
        untouched = dict(Grade.objects.exclude(enrollment=self.enrollment).values_list("pk", "score"))
        data = self.payload()
        data[f"score_{self.lab.pk}"] = "35"
        response = self.client.post(self.url, data, follow=True)
        self.assertRedirects(response, reverse("enrollment_outcomes", args=[self.enrollment.pk]))
        self.assertContains(response, "Grades saved")
        self.assertContains(response, "70.00%")
        po = ProgramOutcome.objects.get(framework=self.enrollment.offering.po_framework, code="PO5")
        result = calculate_student_po_achievement(self.enrollment.student, po)
        self.assertEqual(result["score"], Decimal("70"))
        self.assertEqual(result["coverage"], Decimal("100"))
        self.assertEqual(dict(Grade.objects.exclude(enrollment=self.enrollment).values_list("pk", "score")), untouched)

    def test_zero_blank_and_missing_grade_record(self):
        Grade.objects.filter(enrollment=self.enrollment, assessment=self.lab).delete()
        data = self.payload()
        self.assertEqual(data[f"score_{self.lab.pk}"], "")
        self.client.post(self.url, data)
        self.assertFalse(Grade.objects.filter(enrollment=self.enrollment, assessment=self.lab).exists())
        data = self.payload()
        data[f"score_{self.lab.pk}"] = "0"
        self.client.post(self.url, data)
        grade = Grade.objects.get(enrollment=self.enrollment, assessment=self.lab)
        self.assertEqual(grade.score, Decimal("0"))
        data = self.payload()
        data[f"score_{self.lab.pk}"] = ""
        self.client.post(self.url, data)
        grade.refresh_from_db()
        self.assertIsNone(grade.score)

    def test_invalid_scores_save_nothing_and_preserve_input(self):
        for value in ("-1", "50.01", "1.001", "NaN", "Infinity", "not a number"):
            with self.subTest(value=value):
                before = self.scores()
                data = self.payload()
                data[f"score_{self.midterm.pk}"] = "25"
                data[f"score_{self.lab.pk}"] = value
                response = self.client.post(self.url, data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertEqual(response.context["form"][f"score_{self.midterm.pk}"].value(), "25")
                self.assertEqual(self.scores(), before)

    def test_partial_extra_and_duplicate_fields_save_nothing(self):
        original = self.payload()
        foreign = Assessment.objects.exclude(offering=self.enrollment.offering).first()
        cases = [
            {k: v for k, v in original.items() if k != f"score_{self.lab.pk}"},
            {**original, f"score_{foreign.pk}": "100"},
            {**original, f"score_{self.midterm.pk}": ["20", "30"]},
        ]
        for data in cases:
            before = self.scores()
            response = self.client.post(self.url, data)
            self.assertContains(response, "Nothing was saved")
            self.assertEqual(self.scores(), before)

    def test_stale_grade_and_settings_are_rejected(self):
        data = self.payload()
        data[f"score_{self.lab.pk}"] = "35"
        Grade.objects.filter(enrollment=self.enrollment, assessment=self.midterm).update(score=10)
        before = self.scores()
        response = self.client.post(self.url, data)
        self.assertContains(response, "changed since you opened")
        self.assertEqual(self.scores(), before)
        data = self.payload()
        Assessment.objects.filter(pk=self.lab.pk).update(max_score=60)
        response = self.client.post(self.url, data)
        self.assertContains(response, "changed since you opened")
        self.assertEqual(self.scores(), before)

    def test_token_cannot_be_tampered_or_reused_for_another_student(self):
        data = self.payload()
        other = Enrollment.objects.get(
            student__student_number="PILOT002", offering=self.enrollment.offering,
        )
        before = self.scores()
        response = self.client.post(reverse("enrollment_grade_editor", args=[other.pk]), data)
        self.assertContains(response, "Nothing was saved")
        data["revision"] += "tampered"
        response = self.client.post(self.url, data)
        self.assertContains(response, "invalid or expired")
        self.assertEqual(self.scores(), before)

    def test_expired_editing_session_saves_nothing(self):
        data = self.payload()
        data[f"score_{self.lab.pk}"] = "35"
        before = self.scores()
        with patch("django.core.signing.time.time", return_value=time.time() + 7201):
            response = self.client.post(self.url, data)
        self.assertContains(response, "invalid or expired")
        self.assertEqual(self.scores(), before)

    def test_permissions_cover_get_post_and_hidden_link(self):
        for staff, active in ((False, True), (True, True), (True, False)):
            user = get_user_model().objects.create_user(
                username=f"user_{staff}_{active}", is_staff=staff, is_active=active,
            )
            client = Client()
            client.force_login(user)
            before = self.scores()
            for method in (client.get, client.post):
                response = method(self.url)
                self.assertEqual(response.status_code, 403 if staff and active else 302)
            if staff and active:
                response = client.get(reverse("enrollment_outcomes", args=[self.enrollment.pk]))
                self.assertNotContains(response, self.url)
            self.assertEqual(self.scores(), before)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(self.client.post(self.url).status_code, 302)

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.editor)
        data = self.payload(client)
        before = self.scores()
        self.assertEqual(client.post(self.url, data).status_code, 403)
        data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
        self.assertEqual(client.post(self.url, data).status_code, 302)
        self.assertEqual(self.scores(), before)

    def test_failure_after_first_write_rolls_back_every_grade(self):
        Grade.objects.filter(enrollment=self.enrollment, assessment=self.lab).delete()
        data = self.payload()
        data[f"score_{self.midterm.pk}"] = "20"
        data[f"score_{self.lab.pk}"] = "35"
        # The existing Midterm updates before creation of the missing Lab fails.
        before = self.scores()
        with patch("core.grade_editor.Grade.objects.create", side_effect=ValidationError("Save failed")):
            response = self.client.post(self.url, data)
        self.assertContains(response, "Nothing was saved")
        self.assertEqual(self.scores(), before)

    def test_empty_and_unknown_enrollment(self):
        # Use an offering without assessments without disturbing protected evidence.
        from core.models import CourseOffering
        source = self.enrollment.offering
        offering = CourseOffering.objects.create(
            course=source.course, curriculum=source.curriculum,
            instructor=source.instructor, po_framework=source.po_framework,
            year=2027, term="Spring",
        )
        enrollment = Enrollment.objects.create(student=self.enrollment.student, offering=offering)
        response = self.client.get(reverse("enrollment_grade_editor", args=[enrollment.pk]))
        self.assertContains(response, "No assessments configured")
        self.assertNotContains(response, "Save grades</button>")
        self.assertEqual(self.client.get(reverse("enrollment_grade_editor", args=[999999])).status_code, 404)
