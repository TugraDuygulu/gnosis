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
    POFramework,
    ProgramOutcome,
    LOPOMapping,
)
from core.services.lo_calculator import calculate_lo_achievement
from core.services.po_calculator import calculate_course_po_achievement


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

class CourseOfferingValidationTests(TestCase):

    def test_rejects_curriculum_from_another_course(self):
        course_a = Course.objects.create(
            code="CSE311",
            title="Software Engineering",
            credits=4,
        )

        course_b = Course.objects.create(
            code="CSE321",
            title="Data Systems",
            credits=4,
        )

        wrong_curriculum = CourseCurriculum.objects.create(
            course=course_b,
            version_number=1,
        )

        instructor = Instructor.objects.create(
            full_name="Test Instructor",
            email="validation@example.com",
        )

        offering = CourseOffering(
            course=course_a,
            curriculum=wrong_curriculum,
            instructor=instructor,
            year=2026,
            term="Fall",
        )

        with self.assertRaises(ValidationError):
            offering.save()

        self.assertFalse(
            CourseOffering.objects.filter(
                course=course_a,
                curriculum=wrong_curriculum,
            ).exists()
        )
class POCalculatorTests(TestCase):

    def setUp(self):
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
            email="po-test@example.com",
        )

        student = Student.objects.create(
            program=program,
            student_number="PO001",
            full_name="Test Student",
        )

        curriculum = CourseCurriculum.objects.create(
            course=course,
            version_number=1,
        )

        framework = POFramework.objects.create(
            program=program,
            version_number=1,
        )

        self.po1 = ProgramOutcome.objects.create(
            framework=framework,
            code="PO1",
            description="Engineering knowledge",
        )

        offering = CourseOffering.objects.create(
            course=course,
            curriculum=curriculum,
            po_framework=framework,
            instructor=instructor,
            year=2026,
            term="Fall",
        )

        self.enrollment = Enrollment.objects.create(
            student=student,
            offering=offering,
        )

        lo1 = LearningOutcome.objects.create(
            curriculum=curriculum,
            code="LO1",
            description="Apply engineering principles",
        )

        LOPOMapping.objects.create(
            learning_outcome=lo1,
            program_outcome=self.po1,
            strength=5,
        )

        midterm = Assessment.objects.create(
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
            assessment=midterm,
            learning_outcome=lo1,
            weight=60,
        )

        AssessmentLOMapping.objects.create(
            assessment=self.project,
            learning_outcome=lo1,
            weight=40,
        )

        Grade.objects.create(
            enrollment=self.enrollment,
            assessment=midterm,
            score=85,
        )

        Grade.objects.create(
            enrollment=self.enrollment,
            assessment=self.project,
            score=90,
        )

    def test_completed_po_achievement(self):
        result = calculate_course_po_achievement(
            self.enrollment,
            self.po1,
        )

        self.assertEqual(result["score"], Decimal("87"))
        self.assertEqual(result["coverage"], Decimal("100"))
        self.assertEqual(result["status"], "complete")

    def test_partial_po_achievement(self):
        # Simulate a project that has not been graded yet.
        Grade.objects.filter(
            enrollment=self.enrollment,
            assessment=self.project,
        ).delete()

        result = calculate_course_po_achievement(
            self.enrollment,
            self.po1,
        )

        self.assertEqual(result["score"], Decimal("85"))
        self.assertEqual(result["coverage"], Decimal("60"))
        self.assertEqual(result["status"], "provisional")

    def test_zero_po_grade_is_not_missing(self):
        project_grade = Grade.objects.get(
            enrollment=self.enrollment,
            assessment=self.project,
        )

        project_grade.score = 0
        project_grade.save()

        result = calculate_course_po_achievement(
            self.enrollment,
            self.po1,
        )

        self.assertEqual(result["score"], Decimal("51"))
        self.assertEqual(result["coverage"], Decimal("100"))
        self.assertEqual(result["status"], "complete")