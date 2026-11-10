from decimal import Decimal
from io import StringIO
from secrets import token_urlsafe

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from core.access import COORDINATOR_GROUP
from core.models import Course, CourseOffering, Enrollment, Grade, Instructor, Student


class AcademicRolesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.offering = CourseOffering.objects.get(course__code="PILOT311")
        cls.enrollment, cls.peer = cls.offering.enrollments.order_by("student__student_number")
        cls.other_offering = CourseOffering.objects.get(course__code="PILOT321")
        cls.other_offering.instructor = Instructor.objects.create(
            full_name="Other instructor", email="other@example.test",
        )
        cls.other_offering.save(update_fields=["instructor"])
        cls.password = token_urlsafe(24)
        users = get_user_model().objects
        cls.admin = users.create_superuser(username="role_admin", password=cls.password)
        cls.coordinator = users.create_user(username="coordinator", password=cls.password)
        cls.coordinator.groups.add(Group.objects.create(name=COORDINATOR_GROUP))
        cls.instructor = users.create_user(username="instructor", password=cls.password)
        cls.offering.instructor.user = cls.instructor
        cls.offering.instructor.save(update_fields=["user"])
        cls.student = users.create_user(username="student", password=cls.password)
        cls.enrollment.student.user = cls.student
        cls.enrollment.student.save(update_fields=["user"])

    def login(self, user):
        self.client.logout()
        response = self.client.post(reverse("login"), {
            "username": user.username, "password": self.password,
        })
        self.assertRedirects(response, reverse("student_list"), fetch_redirect_response=False)

    def test_sign_in_and_admin_sites(self):
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse("admin:auth_user_add")).status_code, 200)
        self.login(self.coordinator)
        self.assertContains(self.client.get(reverse("management_home")), "Academic management")
        self.assertEqual(self.client.get(reverse("program_overview")).status_code, 200)
        self.assertEqual(self.client.get(reverse("academic_admin:core_assessment_add")).status_code, 200)
        admin_response = self.client.get(reverse("admin:auth_user_add"))
        self.assertTrue(admin_response.url.startswith(reverse("admin:login")))
        self.assertEqual(self.client.post(reverse("offering_gradebook", args=[self.offering.pk]), {}).status_code, 403)
        self.login(self.instructor)
        self.assertRedirects(self.client.get(reverse("student_list")), reverse("course_list"))
        self.login(self.student)
        self.assertRedirects(
            self.client.get(reverse("student_list")),
            reverse("student_detail", args=[self.enrollment.student_id]),
        )

    def test_student_can_read_only_own_results_even_with_accidental_staff_flag(self):
        self.student.is_staff = True
        self.student.save(update_fields=["is_staff"])
        self.login(self.student)
        self.assertEqual(self.client.get(reverse("enrollment_outcomes", args=[self.enrollment.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("student_outcomes", args=[
            self.enrollment.student_id, self.offering.po_framework_id,
        ])).status_code, 200)
        for url in (
            reverse("student_detail", args=[self.peer.student_id]),
            reverse("enrollment_outcomes", args=[self.peer.pk]),
            reverse("student_outcomes", args=[self.peer.student_id, self.offering.po_framework_id]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
        before = list(Grade.objects.order_by("pk").values_list("pk", "score"))
        for name, pk in (("enrollment_grade_editor", self.enrollment.pk), ("offering_gradebook", self.offering.pk)):
            with self.subTest(name=name):
                self.assertEqual(self.client.post(reverse(name, args=[pk]), {"score": "100"}).status_code, 403)
        self.assertEqual(list(Grade.objects.order_by("pk").values_list("pk", "score")), before)
        self.assertEqual(self.client.get(reverse("academic_admin:index"), follow=True).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)

    def test_instructor_cannot_access_unassigned_offerings_or_management(self):
        self.login(self.instructor)
        course_list = self.client.get(reverse("course_list"))
        self.assertEqual([offering.pk for offering in course_list.context["offerings"]], [self.offering.pk])
        own = reverse("offering_detail", args=[self.offering.pk])
        foreign = self.other_offering.enrollments.first()
        self.assertEqual(self.client.get(own).status_code, 200)
        for name, pk in (
            ("offering_detail", self.other_offering.pk),
            ("offering_gradebook", self.other_offering.pk),
            ("enrollment_outcomes", foreign.pk),
            ("enrollment_grade_history", foreign.pk),
            ("enrollment_grade_editor", foreign.pk),
        ):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("offering_gradebook", args=[self.other_offering.pk]), {}).status_code, 404)
        for url in (reverse("management_create", args=["courses"]),
                    reverse("management_account", args=["students", self.peer.student_id]),
                    reverse("program_overview")):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, {}).status_code, 403)

    def test_instructor_grades_and_student_sees_zero_and_missing(self):
        self.login(self.instructor)
        editor = reverse("enrollment_grade_editor", args=[self.enrollment.pk])
        form = self.client.get(editor).context["form"]
        scores = {assessment.name: f"score_{assessment.pk}" for assessment in self.offering.assessments.all()}
        payload = {"revision": form.initial["revision"], scores["Midterm"]: "90", scores["Project"]: "40"}
        self.assertEqual(self.client.post(editor, payload).status_code, 302)
        evidence_url = reverse("enrollment_outcomes", args=[self.enrollment.pk])
        results = self.client.get(evidence_url).context["lo_results"]
        self.assertIn(Decimal("86"), [row["score"] for row in results])
        payload.update(revision=self.client.get(editor).context["form"].initial["revision"])
        payload.update({scores["Midterm"]: "0", scores["Project"]: ""})
        self.assertEqual(self.client.post(editor, payload).status_code, 302)
        history = self.client.get(reverse("enrollment_grade_history", args=[self.enrollment.pk]))
        self.assertContains(history, self.instructor.username)
        self.login(self.student)
        response = self.client.get(evidence_url)
        by_name = {row["assessment"].name: row["score"] for row in response.context["assessment_results"]}
        self.assertEqual(by_name, {"Midterm": Decimal("0"), "Project": None})

    def test_gradebook_rejects_tampered_enrollment_fields(self):
        self.login(self.instructor)
        url = reverse("offering_gradebook", args=[self.offering.pk])
        payload = {}
        for row in self.client.get(url).context["rows"]:
            form = row["form"]
            payload[form.add_prefix("revision")] = form.initial["revision"]
            for field in row["fields"]:
                payload[field.html_name] = "1"
        foreign = self.other_offering.enrollments.first()
        assessment = self.other_offering.assessments.first()
        payload[f"e{foreign.pk}-score_{assessment.pk}"] = "2"
        before = list(Grade.objects.order_by("pk").values_list("pk", "score"))
        self.assertContains(self.client.post(url, payload), "do not match this roster")
        self.assertEqual(list(Grade.objects.order_by("pk").values_list("pk", "score")), before)

    def test_coordinator_links_existing_record_and_cannot_escalate(self):
        self.login(self.coordinator)
        account = reverse("management_account", args=["students", self.peer.student_id])
        users = get_user_model().objects
        count = Student.objects.count()
        data = {"action": "create", "username": "linked", "password1": self.password, "password2": self.password}
        self.assertEqual(self.client.post(account, {**data, "is_superuser": "on"}).status_code, 403)
        self.assertFalse(users.filter(username="linked").exists())
        self.assertEqual(self.client.post(account, {**data, "username": self.admin.username}).status_code, 200)
        self.assertEqual(self.client.post(account, data).status_code, 302)
        linked = users.get(username="linked")
        self.assertTrue(linked.check_password(self.password))
        self.assertFalse(linked.is_staff or linked.is_superuser or linked.groups.exists())
        self.assertEqual(Student.objects.get(pk=self.peer.student_id).user_id, linked.pk)
        self.assertEqual(Student.objects.count(), count)
        student_client = Client()
        self.assertTrue(student_client.login(username="linked", password=self.password))
        self.assertEqual(self.client.post(account, {"action": "disable"}).status_code, 302)
        linked.refresh_from_db()
        self.assertFalse(linked.is_active or linked.has_usable_password())
        self.assertEqual(student_client.get(reverse("student_detail", args=[self.peer.student_id])).status_code, 302)

    def test_coordinator_cannot_reset_privileged_linked_identity(self):
        Student.objects.filter(pk=self.peer.student_id).update(user=self.admin)
        self.login(self.coordinator)
        url = reverse("management_account", args=["students", self.peer.student_id])
        self.assertEqual(self.client.post(url, {
            "action": "reset", "new_password1": token_urlsafe(24), "new_password2": token_urlsafe(24),
        }).status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password(self.password))

    def test_coordinator_academic_records_and_assignment(self):
        self.login(self.coordinator)
        instructor_url = reverse("management_create", args=["instructors"])
        data = {"full_name": "Demo Instructor", "email": "instructor@example.test"}
        self.assertEqual(self.client.post(instructor_url, data).status_code, 302)
        self.assertEqual(self.client.post(instructor_url, data).status_code, 200)
        instructor = Instructor.objects.get(email=data["email"])
        self.assertEqual(self.client.post(reverse("management_create", args=["courses"]), {
            "code": "DEMO101", "title": "Demo Course", "credits": 3,
        }).status_code, 302)
        self.assertTrue(Course.objects.filter(code="DEMO101").exists())
        offering = self.other_offering
        self.assertEqual(self.client.post(reverse("management_edit", args=["offerings", offering.pk]), {
            "instructor": instructor.pk, "status": offering.status,
        }).status_code, 302)
        offering.refresh_from_db()
        self.assertEqual(offering.instructor_id, instructor.pk)
        url = reverse("management_enrollment_status", args=[self.enrollment.pk])
        for status in ("withdrawn", "active"):
            self.assertEqual(self.client.post(url, {"status": status}).status_code, 302)
            self.enrollment.refresh_from_db()
            self.assertEqual(self.enrollment.status, status)

    def test_full_intake_gradebook_and_student_workflow(self):
        self.login(self.coordinator)
        self.assertEqual(self.client.post(reverse("student_register"), {
            "full_name": "New pilot student", "student_number": "ROLE003",
            "program": self.offering.po_framework.program_id,
        }).status_code, 302)
        record = Student.objects.get(student_number="ROLE003")
        account = reverse("management_account", args=["students", record.pk])
        self.assertEqual(self.client.post(account, {
            "action": "create", "username": "new_pilot", "password1": self.password,
            "password2": self.password,
        }).status_code, 302)
        record.refresh_from_db()
        self.assertEqual(self.client.post(reverse("student_enroll", args=[record.pk]), {
            "offering": self.offering.pk,
        }).status_code, 302)
        enrollment = Enrollment.objects.get(student=record, offering=self.offering)

        self.login(self.instructor)
        url = reverse("offering_gradebook", args=[self.offering.pk])
        payload = {}
        for row in self.client.get(url).context["rows"]:
            form = row["form"]
            payload[form.add_prefix("revision")] = form.initial["revision"]
            for field in row["fields"]:
                value = field.value()
                if row["enrollment"].pk == enrollment.pk:
                    value = {"Midterm": 90, "Project": 40}[field.label]
                payload[field.html_name] = "" if value is None else str(value)
        self.assertEqual(self.client.post(url, payload).status_code, 302)

        self.login(record.user)
        self.assertContains(self.client.get(reverse("student_list"), follow=True), "My courses and outcomes")
        evidence = self.client.get(reverse("enrollment_outcomes", args=[enrollment.pk]))
        scores = sorted(row["score"] for row in evidence.context["lo_results"])
        self.assertEqual([round(score, 3) for score in scores], [Decimal("82.857"), Decimal("86.000")])
        self.assertNotContains(evidence, "Edit course grades")
        profile = self.client.get(reverse("student_outcomes", args=[record.pk, self.offering.po_framework_id]))
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(self.client.post(url, payload).status_code, 403)
        self.assertEqual(self.client.get(reverse("student_detail", args=[self.peer.student_id])).status_code, 404)

    def test_anonymous_and_csrf_rejection_do_not_write(self):
        url = reverse("management_create", args=["courses"])
        data = {"code": "DENIED", "title": "No Write", "credits": 3}
        self.assertEqual(self.client.post(url, data).status_code, 302)
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.coordinator)
        self.assertEqual(browser.post(url, data).status_code, 403)
        self.assertFalse(Course.objects.filter(code="DENIED").exists())
