from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from core.grade_history import history_entries, history_row
from core.models import CourseOffering, Enrollment, Grade, POFramework, Program, ProgramOutcome, Student
from core.services.student_po_calculator import calculate_student_po_achievement
from core.student_intake import available_offerings, enroll_student


class StudentIntakeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.program = Program.objects.get(code="PILOT")
        cls.framework = cls.program.po_frameworks.get(version_number=1)
        cls.offering = CourseOffering.objects.get(course__code="PILOT321")
        cls.user = get_user_model().objects.create_user(username="intake_staff", is_staff=True)
        cls.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="core",
            codename__in=["add_student", "add_enrollment", "change_grade", "view_grade"],
        ))

    def setUp(self):
        self.client.force_login(self.user)
        self.register_url = reverse("student_register")
        self.student = Student.objects.create(program=self.program, student_number="NEW001", full_name="New Student")
        self.detail_url = reverse("student_detail", args=[self.student.pk])
        self.enroll_url = reverse("student_enroll", args=[self.student.pk])

    def registration(self, **kwargs):
        return {"full_name": " New Person ", "student_number": " 0000123 ", "program": self.program.pk, **kwargs}

    def test_registration_trims_preserves_leading_zeros_and_does_not_create_login(self):
        count = get_user_model().objects.count()
        response = self.client.post(self.register_url, self.registration(), follow=True)
        student = Student.objects.get(student_number="0000123")
        self.assertEqual(student.full_name, "New Person")
        self.assertRedirects(response, reverse("student_detail", args=[student.pk]))
        self.assertContains(response, "Student registered")
        self.assertContains(response, "No course enrollments yet")
        self.assertEqual(get_user_model().objects.count(), count)
        self.assertFalse(student.enrollments.exists())

    def test_registration_invalid_duplicate_and_database_conflict(self):
        before = Student.objects.count()
        for data in [self.registration(full_name=" "), self.registration(student_number="NEW001"),
                     self.registration(student_number="x" * 21), self.registration(program=999999)]:
            response = self.client.post(self.register_url, data)
            self.assertContains(response, "Nothing was saved")
            self.assertTrue(response.context["form"].errors)
        with patch("core.student_intake.StudentRegistrationForm.save", side_effect=IntegrityError("duplicate")):
            response = self.client.post(self.register_url, self.registration())
        self.assertContains(response, "already exists")
        self.assertEqual(response.context["form"]["student_number"].value(), " 0000123 ")
        self.assertEqual(Student.objects.count(), before)

    def test_permissions_methods_and_csrf(self):
        self.assertContains(self.client.get(reverse("student_list")), self.register_url)
        for staff, active, permission in [(True, True, False), (False, True, True), (True, False, True)]:
            user = get_user_model().objects.create_user(username=f"intake_{staff}_{active}", is_staff=staff, is_active=active)
            if permission:
                user.user_permissions.add(*Permission.objects.filter(codename__in=["add_student", "add_enrollment"]))
            client = Client()
            client.force_login(user)
            for url in [self.register_url, self.enroll_url]:
                for method in [client.get, client.post]:
                    self.assertEqual(method(url).status_code, 403 if staff and active else 302)
            if staff and active:
                self.assertNotContains(client.get(reverse("student_list")), self.register_url)
                self.assertNotContains(client.get(self.detail_url), self.enroll_url)
        for url in [self.register_url, self.enroll_url, self.detail_url]:
            self.assertEqual(Client().get(url).status_code, 302)
        self.assertEqual(self.client.put(self.register_url).status_code, 405)
        self.assertEqual(self.client.post(self.detail_url).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        for url, data in [(self.register_url, self.registration()), (self.enroll_url, {"offering": self.offering.pk})]:
            client.get(url)
            self.assertEqual(client.post(url, data).status_code, 403)
        response = client.post(self.enroll_url, {"offering": self.offering.pk,
                                               "csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertEqual(response.status_code, 302)

    def test_enrollment_is_active_unique_and_creates_no_grades(self):
        before = Grade.objects.count()
        response = self.client.post(self.enroll_url, {"offering": self.offering.pk}, follow=True)
        self.assertRedirects(response, self.detail_url)
        enrollment = self.student.enrollments.get()
        self.assertEqual(enrollment.status, "active")
        self.assertContains(response, "No grades have been recorded yet")
        self.assertEqual(Grade.objects.count(), before)
        self.assertContains(self.client.post(self.enroll_url, {"offering": self.offering.pk}), "cannot be added")
        self.assertEqual(self.student.enrollments.count(), 1)
        self.assertContains(self.client.get(reverse("offering_detail", args=[self.offering.pk])), self.detail_url)
        enrollment.status = "withdrawn"
        enrollment.save()
        self.assertContains(self.client.get(self.detail_url), "withdrawn")
        self.assertEqual(self.client.post(self.enroll_url, {"offering": self.offering.pk}).status_code, 200)
        self.assertEqual(self.student.enrollments.get().status, "withdrawn")

    def copy_offering(self, **kwargs):
        original = self.offering
        return CourseOffering.objects.create(
            course=original.course, curriculum=original.curriculum, instructor=original.instructor,
            **{"po_framework": self.framework, "year": 2027, "term": "Spring", "section": "NEW", **kwargs},
        )

    def test_eligibility_rejects_incompatible_missing_framework_and_bad_curriculum(self):
        foreign = Program.objects.create(code="OTHER", name="Other program")
        framework = POFramework.objects.create(program=foreign, version_number=1)
        wrong = self.copy_offering(po_framework=framework, section="OTHER")
        missing = self.copy_offering(po_framework=None, section="NONE")
        bad = self.copy_offering(section="BAD")
        CourseOffering.objects.filter(pk=bad.pk).update(curriculum=CourseOffering.objects.get(course__code="PILOT311").curriculum)
        for offering in [wrong, missing, bad]:
            self.assertNotIn(offering.pk, list(available_offerings(self.student).values_list("pk", flat=True)))
            self.assertContains(self.client.post(self.enroll_url, {"offering": offering.pk}), "cannot be added")
        self.assertFalse(self.student.enrollments.exists())

    def test_repeated_active_course_same_framework_rejected_but_other_version_separate(self):
        enroll_student(self.student.pk, self.offering.pk)
        repeated = self.copy_offering()
        with self.assertRaises(ValidationError):
            enroll_student(self.student.pk, repeated.pk)
        version2 = POFramework.objects.create(program=self.program, version_number=2)
        separate = self.copy_offering(po_framework=version2, section="V2")
        self.assertEqual(self.client.post(self.enroll_url, {"offering": separate.pk}).status_code, 302)
        self.assertEqual(self.student.enrollments.count(), 2)

    def test_rechecks_current_program_and_handles_database_conflict(self):
        foreign = Program.objects.create(code="CHANGED", name="Changed program")
        original = enroll_student

        def change_program(student_id, offering_id):
            Student.objects.filter(pk=student_id).update(program=foreign)
            return original(student_id, offering_id)

        with patch("core.views.enroll_student", side_effect=change_program):
            response = self.client.post(self.enroll_url, {"offering": self.offering.pk})
        self.assertContains(response, "no longer available")
        self.assertFalse(self.student.enrollments.exists())
        Student.objects.filter(pk=self.student.pk).update(program=self.program)
        with patch("core.views.enroll_student", side_effect=IntegrityError("duplicate")):
            response = self.client.post(self.enroll_url, {"offering": self.offering.pk})
        self.assertContains(response, "Reload before trying again")
        self.assertFalse(self.student.enrollments.exists())

    def test_empty_states_missing_student_and_escaped_identity(self):
        empty = Program.objects.create(code="EMPTY", name="Unconfigured program")
        self.student.program = empty
        self.student.full_name = "<script>test</script>"
        self.student.save()
        response = self.client.get(self.detail_url)
        self.assertContains(response, "No outcome framework configured")
        self.assertContains(response, "&lt;script&gt;test&lt;/script&gt;")
        response = self.client.get(self.enroll_url)
        self.assertContains(response, "No eligible offerings")
        self.assertNotContains(response, 'type="submit"')
        self.assertEqual(self.client.get(reverse("student_detail", args=[999999])).status_code, 404)
        self.assertEqual(self.client.get(reverse("student_enroll", args=[999999])).status_code, 404)
        with patch("core.student_intake.Program.objects.order_by", return_value=Program.objects.none()):
            self.assertContains(self.client.get(self.register_url), "No programs configured")

    def grade_payload(self, enrollment):
        url = reverse("enrollment_grade_editor", args=[enrollment.pk])
        form = self.client.get(url).context["form"]
        return url, {field.name: "" if field.value() is None else str(field.value()) for field in form}

    def test_complete_native_staff_journey_and_outcome_history_propagation(self):
        untouched = list(Grade.objects.values_list("pk", "score"))
        self.client.post(self.register_url, self.registration())
        student = Student.objects.get(student_number="0000123")
        for offering in CourseOffering.objects.filter(po_framework=self.framework):
            self.client.post(reverse("student_enroll", args=[student.pk]), {"offering": offering.pk})
        self.assertEqual(student.enrollments.count(), 2)
        enrollment = student.enrollments.get(offering=self.offering)
        self.assertFalse(Grade.objects.filter(enrollment__student=student).exists())
        profile_url = reverse("student_outcomes", args=[student.pk, self.framework.pk])
        self.assertContains(self.client.get(profile_url), "No graded evidence")
        # Blank save never manufactures grades or history.
        url, data = self.grade_payload(enrollment)
        self.client.post(url, data)
        self.assertFalse(history_entries(enrollment.pk).exists())
        # Software-engineering course: all assessment percentages are 80.
        other = student.enrollments.exclude(pk=enrollment.pk).get()
        url, data = self.grade_payload(other)
        for assessment in other.offering.assessments.all():
            data[f"score_{assessment.pk}"] = str((assessment.max_score * Decimal("0.8")).quantize(Decimal("0.01")))
        self.assertEqual(self.client.post(url, data).status_code, 302)
        url, data = self.grade_payload(enrollment)
        for assessment in self.offering.assessments.all():
            data[f"score_{assessment.pk}"] = "0" if assessment.name == "Midterm" else "35"
        self.assertEqual(self.client.post(url, data).status_code, 302)
        outcomes = {po.code: calculate_student_po_achievement(student, po) for po in self.framework.program_outcomes.all()}
        self.assertEqual(outcomes["PO2"]["score"].quantize(Decimal("0.01")), Decimal("58.75"))
        self.assertEqual(outcomes["PO2"]["coverage"], Decimal("100"))
        self.assertEqual(len(outcomes["PO2"]["courses"]), 2)
        self.assertEqual(outcomes["PO4"]["score"], Decimal("0"))
        self.assertEqual(outcomes["PO5"]["score"], Decimal("70"))
        self.assertContains(self.client.get(profile_url), "58.75%")
        self.assertContains(self.client.get(reverse("enrollment_outcomes", args=[enrollment.pk])), "70.00%")
        lab = self.offering.assessments.get(name="Lab")
        for value in ["40", ""]:
            url, data = self.grade_payload(enrollment)
            data[f"score_{lab.pk}"] = value
            self.assertEqual(self.client.post(url, data).status_code, 302)
        rows = [history_row(entry) for entry in history_entries(enrollment.pk)]
        self.assertEqual(rows[0]["old"], "40.00")
        self.assertIsNone(rows[0]["new"])
        self.assertEqual(rows[1]["old"], "35.00")
        self.assertEqual(rows[1]["new"], "40")
        self.assertContains(self.client.get(reverse("enrollment_grade_history", args=[enrollment.pk])), "intake_staff")
        po5 = ProgramOutcome.objects.get(framework=self.framework, code="PO5")
        self.assertIsNone(calculate_student_po_achievement(student, po5)["score"])
        self.assertEqual(list(Grade.objects.exclude(enrollment__student=student).values_list("pk", "score")), untouched)
