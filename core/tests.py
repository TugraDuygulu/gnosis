from django.test import TestCase

from decimal import Decimal

from django.core.exceptions import ValidationError

from core.models import (
    Program,
    Course,
    Instructor,
    Student,
    CourseCurriculum,
    CourseOffering,
    Enrollment,
    Assessment,
    Grade,
    LearningOutcome,
    AssessmentLOMapping,
)
from core.services.lo_calculator import calculate_lo_achievement


class LOCalculatorTests(TestCase):

    def setUp(self):
        """Create a fresh miniature Gnosis database for each test."""

        program = Program.objects.create(
            code="CENG",
            name="Computer Engineering",
        )

        course = Course.objects.create(
            code="CSE311",
            title="Software Engineering",
            credits=4,
        )

        instructor = Instructor.objects.create(
            full_name="Test Instructor",
            email="instructor@example.com",
        )

        student = Student.objects.create(
            program=program,
            student_number="TEST001",
            full_name="Test Student",
        )

        curriculum = CourseCurriculum.objects.create(
            course=course,
            version_number=1,
        )

        offering = CourseOffering.objects.create(
            course=course,
            curriculum=curriculum,
            instructor=instructor,
            year=2026,
            term="Fall",
        )

        self.enrollment = Enrollment.objects.create(
            student=student,
            offering=offering,
        )

        self.lo1 = LearningOutcome.objects.create(
            curriculum=curriculum,
            code="LO1",
            description="Explain software development methodologies.",
        )

        self.midterm = Assessment.objects.create(
            offering=offering,
            name="Midterm",
            max_score=100,
        )

        self.project = Assessment.objects.create(
            offering=offering,
            name="Project",
            max_score=100,
        )

        AssessmentLOMapping.objects.create(
            assessment=self.midterm,
            learning_outcome=self.lo1,
            weight=60,
        )

        AssessmentLOMapping.objects.create(
            assessment=self.project,
            learning_outcome=self.lo1,
            weight=40,
        )

        Grade.objects.create(
            enrollment=self.enrollment,
            assessment=self.midterm,
            score=85,
        )

    def test_grade_above_maximum_is_rejected(self):
        with self.assertRaises(ValidationError):
            Grade.objects.create(
                enrollment=self.enrollment,
                assessment=self.project,
                score=120,
            )

    def test_negative_grade_is_rejected(self):
        with self.assertRaises(ValidationError):
            Grade.objects.create(
                enrollment=self.enrollment,
                assessment=self.project,
                score=-5,
            )

    def test_missing_grade_is_provisional(self):
        result = calculate_lo_achievement(
            self.enrollment, self.lo1
        )

        self.assertEqual(result["score"], Decimal("85.00"))
        self.assertEqual(result["coverage"], Decimal("60.00"))
        self.assertEqual(result["status"], "provisional")

    def test_completed_grades(self):
        Grade.objects.create(
            enrollment=self.enrollment,
            assessment=self.project,
            score=90,
        )

        result = calculate_lo_achievement(
            self.enrollment, self.lo1
        )

        self.assertEqual(result["score"], Decimal("87.00"))
        self.assertEqual(result["coverage"], Decimal("100.00"))
        self.assertEqual(result["status"], "complete")

    def test_zero_is_not_missing(self):
        Grade.objects.create(
            enrollment=self.enrollment,
            assessment=self.project,
            score=0,
        )

        result = calculate_lo_achievement(
            self.enrollment, self.lo1
        )

        self.assertEqual(result["score"], Decimal("51.00"))
        self.assertEqual(result["coverage"], Decimal("100.00"))
        self.assertEqual(result["status"], "complete")

    def test_no_grades(self):
        Grade.objects.all().delete()

        result = calculate_lo_achievement(
            self.enrollment, self.lo1
        )

        self.assertIsNone(result["score"])
        self.assertEqual(result["coverage"], Decimal("0.00"))
        self.assertEqual(result["status"], "no_data")