"""Database-backed regressions for existing framework/selection policies (#12)."""

from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import (
    CourseOffering, CoursePOContribution, Enrollment, Grade,
    POFramework, Program, ProgramOutcome, Student,
)
from core.services.po_calculator import calculate_course_po_achievement
from core.services.student_po_calculator import calculate_student_po_achievement


class CalculationBoundaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.framework = POFramework.objects.get(program__code="PILOT", version_number=1)
        cls.po = cls.framework.program_outcomes.get(code="PO2")
        cls.student = Student.objects.create(
            program=cls.framework.program, student_number="BOUNDARY", full_name="Boundary Student",
        )
        cls.first = Enrollment.objects.create(
            student=cls.student, offering=CourseOffering.objects.get(course__code="PILOT311"),
        )
        cls.second = Enrollment.objects.create(
            student=cls.student, offering=CourseOffering.objects.get(course__code="PILOT321"),
        )

    def grade_course(self, enrollment, percentage):
        for assessment in enrollment.offering.assessments.all():
            score = assessment.max_score * Decimal(percentage) / Decimal("100")
            Grade.objects.update_or_create(
                enrollment=enrollment, assessment=assessment, defaults={"score": score},
            )

    def result(self):
        return calculate_student_po_achievement(self.student, self.po)

    def assert_sources(self, result, *enrollments):
        self.assertEqual([row["enrollment"].pk for row in result["courses"]], [e.pk for e in enrollments])

    def test_course_requires_assigned_exact_framework(self):
        other_version = POFramework.objects.create(program=self.student.program, version_number=2)
        other_po = ProgramOutcome.objects.create(framework=other_version, code="PO2", description="Other version")
        with self.assertRaisesMessage(ValueError, "does not belong"):
            calculate_course_po_achievement(self.first, other_po)
        self.first.offering.po_framework = None
        self.first.offering.save()
        with self.assertRaisesMessage(ValueError, "no assigned PO framework"):
            calculate_course_po_achievement(self.first, self.po)

    def test_student_rejects_other_program_in_service_and_profile(self):
        program = Program.objects.create(code="FOREIGN", name="Foreign program")
        framework = POFramework.objects.create(program=program, version_number=1)
        po = ProgramOutcome.objects.create(framework=framework, code="PO2", description="Foreign outcome")
        with self.assertRaisesMessage(ValueError, "same program"):
            calculate_student_po_achievement(self.student, po)
        staff = get_user_model().objects.create_user(username="boundary_reader", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("student_outcomes", args=[self.student.pk, framework.pk])).status_code, 404)

    def test_other_framework_version_excluded_from_score_coverage_and_sources(self):
        self.grade_course(self.first, "80")
        self.grade_course(self.second, "0")
        other_version = POFramework.objects.create(program=self.student.program, version_number=2)
        # Same curriculum and contribution mapping, but a different exact framework.
        self.second.offering.po_framework = other_version
        self.second.offering.save()
        result = self.result()
        self.assertEqual((result["score"], result["coverage"], result["status"]),
                         (Decimal("80"), Decimal("100"), "complete"))
        self.assert_sources(result, self.first)
        self.assertEqual(result["unmapped_enrollments"], [])

    def test_inactive_enrollment_excluded_without_replacing_missing_with_zero(self):
        self.grade_course(self.first, "80")
        self.grade_course(self.second, "0")
        self.second.status = "withdrawn"
        self.second.save()
        result = self.result()
        self.assertEqual((result["score"], result["coverage"], result["status"]),
                         (Decimal("80"), Decimal("100"), "complete"))
        self.assert_sources(result, self.first)
        self.first.status = "withdrawn"
        self.first.save()
        result = self.result()
        self.assertEqual((result["score"], result["coverage"], result["status"]),
                         (None, Decimal("0"), "no_data"))
        self.assertEqual(result["courses"], [])

    def test_unmapped_enrollment_reported_separately_not_counted_as_zero(self):
        self.grade_course(self.first, "80")
        self.grade_course(self.second, "0")
        CoursePOContribution.objects.filter(curriculum=self.second.offering.curriculum, program_outcome=self.po).delete()
        result = self.result()
        self.assertEqual((result["score"], result["coverage"], result["status"]),
                         (Decimal("80"), Decimal("100"), "complete"))
        self.assert_sources(result, self.first)
        self.assertEqual([e.pk for e in result["unmapped_enrollments"]], [self.second.pk])
        CoursePOContribution.objects.filter(curriculum=self.first.offering.curriculum, program_outcome=self.po).delete()
        result = self.result()
        self.assertIsNone(result["score"])
        self.assertEqual(result["coverage"], Decimal("0"))
        self.assertEqual(result["courses"], [])
        self.assertEqual([e.pk for e in result["unmapped_enrollments"]], [self.first.pk, self.second.pk])

    def test_repeated_mapped_course_rejected_until_selection_policy_agreed(self):
        source = self.first.offering
        repeat = CourseOffering.objects.create(
            course=source.course, curriculum=source.curriculum, instructor=source.instructor,
            po_framework=source.po_framework, year=2027, term="Spring", section="REPEAT",
        )
        enrollment = Enrollment.objects.create(student=self.student, offering=repeat)
        with self.assertRaisesMessage(ValueError, "Repeated course enrollments"):
            self.result()
        enrollment.status = "withdrawn"
        enrollment.save()
        self.assert_sources(self.result(), self.first, self.second)

    def test_database_aggregation_distinguishes_missing_null_and_recorded_zero(self):
        self.grade_course(self.first, "80")
        # Missing rows and explicit NULL rows carry the same absence of evidence.
        for explicit_null in [False, True]:
            if explicit_null:
                for assessment in self.second.offering.assessments.all():
                    Grade.objects.create(enrollment=self.second, assessment=assessment, score=None)
            result = self.result()
            self.assertEqual((result["score"], result["coverage"], result["status"]),
                             (Decimal("80"), Decimal("62.5"), "provisional"))
            self.assert_sources(result, self.first, self.second)
            self.assertEqual([row["weight"] for row in result["courses"]], [5, 3])
            self.assertIsNone(result["courses"][1]["score"])
        self.grade_course(self.second, "0")
        result = self.result()
        self.assertEqual((result["score"], result["coverage"], result["status"]),
                         (Decimal("50"), Decimal("100"), "complete"))
        self.assertEqual(result["courses"][1]["score"], Decimal("0"))
