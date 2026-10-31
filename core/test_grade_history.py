from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from core.grade_history import grade_state, history_entries, history_row, record_grade_change
from core.models import Assessment, Enrollment, Grade


class GradeHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.enrollment = Enrollment.objects.get(
            student__student_number="PILOT001", offering__course__code="PILOT321",
        )
        cls.midterm = cls.enrollment.offering.assessments.get(name="Midterm")
        cls.lab = cls.enrollment.offering.assessments.get(name="Lab")
        cls.user = get_user_model().objects.create_user(username="history_editor", is_staff=True)
        cls.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="core", codename__in=["change_grade", "view_grade"],
        ))
        cls.admin = get_user_model().objects.create_superuser(username="history_admin")

    def setUp(self):
        self.client.force_login(self.user)
        self.edit_url = reverse("enrollment_grade_editor", args=[self.enrollment.pk])
        self.history_url = reverse("enrollment_grade_history", args=[self.enrollment.pk])

    def payload(self):
        form = self.client.get(self.edit_url).context["form"]
        return {field.name: "" if field.value() is None else str(field.value()) for field in form}

    def rows(self):
        return [history_row(entry) for entry in history_entries(self.enrollment.pk)]

    def test_native_create_zero_change_clear_and_noop(self):
        Grade.objects.filter(enrollment=self.enrollment, assessment=self.lab).delete()
        self.client.post(self.edit_url, self.payload())
        self.assertEqual(LogEntry.objects.count(), 0)
        for value, old, new, operation in [
            ("0", None, "0", "create"),
            ("35", "0.00", "35", "change"),
            ("", "35.00", None, "change"),
        ]:
            data = self.payload()
            data[f"score_{self.lab.pk}"] = value
            self.assertEqual(self.client.post(self.edit_url, data).status_code, 302)
            row = self.rows()[0]
            self.assertEqual((row["old"], row["new"], row["operation"]), (old, new, operation))
            self.assertEqual(row["actor"], self.user.username)
            self.assertEqual(row["source"], "native editor")
            self.assertIsNotNone(row["time"])
        self.client.post(self.edit_url, self.payload())
        self.assertEqual(LogEntry.objects.count(), 3)
        response = self.client.get(self.history_url)
        self.assertContains(response, "Ungraded")
        self.assertContains(response, "history_editor")

    def test_invalid_and_stale_submissions_add_no_history(self):
        data = self.payload()
        data[f"score_{self.lab.pk}"] = "51"
        self.assertContains(self.client.post(self.edit_url, data), "Nothing was saved")
        data = self.payload()
        Grade.objects.filter(enrollment=self.enrollment, assessment=self.midterm).update(score=10)
        self.assertContains(self.client.post(self.edit_url, data), "changed since you opened")
        self.assertEqual(LogEntry.objects.count(), 0)

    def test_failed_second_log_rolls_back_all_grades_and_history(self):
        data = self.payload()
        data[f"score_{self.midterm.pk}"] = "20"
        data[f"score_{self.lab.pk}"] = "35"
        before = list(Grade.objects.values_list("pk", "score"))
        calls = []

        def fail_second(*args, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                raise ValidationError("History save failed")
            return record_grade_change(*args, **kwargs)

        with patch("core.grade_editor.record_grade_change", side_effect=fail_second):
            self.assertContains(self.client.post(self.edit_url, data), "Nothing was saved")
        self.assertEqual(list(Grade.objects.values_list("pk", "score")), before)
        self.assertEqual(LogEntry.objects.count(), 0)

    def test_history_permission_links_methods_and_missing_enrollment(self):
        self.assertContains(self.client.get(self.edit_url), self.history_url)
        self.assertEqual(self.client.post(self.history_url).status_code, 405)
        for staff, active, allowed in [(True, True, False), (False, True, True), (True, False, True)]:
            user = get_user_model().objects.create_user(
                username=f"reader_{staff}_{active}", is_staff=staff, is_active=active,
            )
            if allowed:
                user.user_permissions.add(Permission.objects.get(codename="view_grade"))
            client = Client()
            client.force_login(user)
            self.assertEqual(client.get(self.history_url).status_code, 403 if staff and active else 302)
            if staff and active:
                self.assertNotContains(client.get(reverse("enrollment_outcomes", args=[self.enrollment.pk])), self.history_url)
        reader = get_user_model().objects.create_user(username="reader", is_staff=True)
        reader.user_permissions.add(Permission.objects.get(codename="view_grade"))
        self.client.force_login(reader)
        self.assertEqual(self.client.get(self.history_url).status_code, 200)
        self.assertEqual(self.client.get(reverse("enrollment_grade_history", args=[999999])).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.history_url).status_code, 302)

    def test_admin_create_change_clear_noop_and_single_delete(self):
        self.client.force_login(self.admin)
        Grade.objects.filter(enrollment=self.enrollment, assessment=self.lab).delete()
        response = self.client.post(reverse("admin:core_grade_add"), {
            "enrollment": self.enrollment.pk, "assessment": self.lab.pk, "score": "0", "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        grade = Grade.objects.get(enrollment=self.enrollment, assessment=self.lab)
        url = reverse("admin:core_grade_change", args=[grade.pk])
        for score in ["30", ""]:
            self.assertEqual(self.client.post(url, {"score": score, "_save": "Save"}).status_code, 302)
        self.client.post(url, {"score": "", "_save": "Save"})
        self.assertEqual(LogEntry.objects.count(), 3)
        self.assertEqual(self.client.post(reverse("admin:core_grade_delete", args=[grade.pk]), {"post": "yes"}).status_code, 302)
        self.assertFalse(Grade.objects.filter(pk=grade.pk).exists())
        self.assertEqual(len(self.rows()), 4)
        self.assertEqual(self.rows()[0]["operation"], "delete")
        self.assertTrue(all(row["actor"] == self.admin.username and row["source"] == "Django Admin" for row in self.rows()))
        self.assertEqual(self.rows()[-1]["new"], "0")

    def test_admin_bulk_delete_keeps_scoped_history(self):
        self.client.force_login(self.admin)
        grades = Grade.objects.filter(enrollment=self.enrollment)
        count = grades.count()
        self.assertEqual(self.client.post(reverse("admin:core_grade_changelist"), {
            "action": "delete_selected", "_selected_action": list(grades.values_list("pk", flat=True)), "post": "yes",
        }).status_code, 302)
        self.assertFalse(grades.exists())
        self.assertEqual(len(self.rows()), count)
        other = Enrollment.objects.exclude(pk=self.enrollment.pk).first()
        self.assertFalse(history_entries(other.pk).exists())
        self.assertContains(self.client.get(self.history_url), "delete")

    def test_admin_log_failure_rolls_back_update_and_bulk_deletion(self):
        self.client.force_login(self.admin)
        grade = Grade.objects.get(enrollment=self.enrollment, assessment=self.midterm)
        with patch("core.admin.record_grade_change", side_effect=RuntimeError("History unavailable")):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("admin:core_grade_change", args=[grade.pk]), {"score": "25", "_save": "Save"})
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("admin:core_grade_changelist"), {
                    "action": "delete_selected", "_selected_action": [grade.pk], "post": "yes",
                })
        grade.refresh_from_db()
        self.assertEqual(grade.score, Decimal("0"))
        self.assertEqual(LogEntry.objects.count(), 0)

    def test_admin_cannot_reassign_existing_grade(self):
        self.client.force_login(self.admin)
        grade = Grade.objects.get(enrollment=self.enrollment, assessment=self.midterm)
        self.client.post(reverse("admin:core_grade_change", args=[grade.pk]), {
            "score": "15", "assessment": self.lab.pk,
            "enrollment": Enrollment.objects.exclude(pk=self.enrollment.pk).first().pk, "_save": "Save",
        })
        grade.refresh_from_db()
        self.assertEqual((grade.assessment_id, grade.enrollment_id), (self.midterm.pk, self.enrollment.pk))

    def test_history_snapshots_escape_names_and_paginate(self):
        Assessment.objects.filter(pk=self.lab.pk).update(name="<script>example</script>")
        data = self.payload()
        data[f"score_{self.lab.pk}"] = "10"
        self.client.post(self.edit_url, data)
        Assessment.objects.filter(pk=self.lab.pk).update(name="Renamed")
        response = self.client.get(self.history_url)
        self.assertContains(response, "&lt;script&gt;example&lt;/script&gt;")
        self.assertNotContains(response, "<script>")
        grade = Grade.objects.get(enrollment=self.enrollment, assessment=self.lab)
        for number in range(50):
            before = grade_state(grade)
            grade.score = Decimal(number)
            record_grade_change(self.user, grade, before, source="native editor", operation="change")
        response = self.client.get(self.history_url)
        self.assertEqual(len(response.context["history"]), 50)
        self.assertContains(response, "Older changes")
        self.assertEqual(len(self.client.get(self.history_url, {"page": 2}).context["history"]), 1)
