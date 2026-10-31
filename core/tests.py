from io import StringIO
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.test import TestCase, SimpleTestCase

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
    CoursePOContribution,
)
from core.services.lo_calculator import calculate_lo_achievement
from core.services.po_calculator import calculate_course_po_achievement
from core.services.student_po_calculator import (
    aggregate_course_po_results,
    calculate_student_po_achievement,
)

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

    def set_instructor_example_grades(self):
        midterm_grade = Grade.objects.get(
            enrollment=self.enrollment, assessment=self.midterm,
        )
        midterm_grade.score = Decimal("90")
        midterm_grade.save()
        Grade.objects.create(
            enrollment=self.enrollment,
            assessment=self.project,
            score=Decimal("80"),
        )

    def test_instructor_example_lo1_is_86(self):
        self.set_instructor_example_grades()

        result = calculate_lo_achievement(self.enrollment, self.lo1)

        self.assertEqual(result["score"], Decimal("86"))
        self.assertEqual(result["coverage"], Decimal("100"))
        self.assertEqual(result["status"], "complete")

    def test_instructor_example_lo2_preserves_precision(self):
        self.set_instructor_example_grades()
        lo2 = LearningOutcome.objects.create(
            curriculum=self.lo1.curriculum,
            code="LO2",
            description="Instructor example with relative weights totalling 140.",
        )
        AssessmentLOMapping.objects.create(
            assessment=self.midterm, learning_outcome=lo2, weight=40,
        )
        AssessmentLOMapping.objects.create(
            assessment=self.project, learning_outcome=lo2, weight=100,
        )

        result = calculate_lo_achievement(self.enrollment, lo2)

        # (90 * 40 + 80 * 100) / 140 = 580/7, not an early-rounded 82.
        self.assertEqual(result["score"], Decimal("580") / Decimal("7"))
        self.assertEqual(result["score"].quantize(Decimal("0.1")), Decimal("82.9"))
        self.assertEqual(result["coverage"], Decimal("100"))
        self.assertEqual(result["status"], "complete")

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


    def test_multiple_los_with_different_po_strengths(self):
        # Reproduce the example from our dashboard.
        curriculum = self.enrollment.offering.curriculum
        lo1 = LearningOutcome.objects.get(
            curriculum=curriculum, code="LO1"
        )
        lo2 = LearningOutcome.objects.create(
            curriculum=curriculum,
            code="LO2",
            description="Apply software engineering methods",
        )

        po2 = ProgramOutcome.objects.create(
            framework=self.po1.framework,
            code="PO2",
            description="Problem analysis",
        )

        # Midterm -> LO2: 40%, Project -> LO2: 100%
        midterm = Assessment.objects.get(
            offering=self.enrollment.offering,
            name="Midterm",
        )

        AssessmentLOMapping.objects.create(
            assessment=midterm,
            learning_outcome=lo2,
            weight=40,
        )
        AssessmentLOMapping.objects.create(
            assessment=self.project,
            learning_outcome=lo2,
            weight=100,
        )

        # LO1 -> PO1 already exists with strength 5.
        for lo, po, strength in [
            (lo1, po2, 3),
            (lo2, self.po1, 3),
            (lo2, po2, 5),
        ]:
            LOPOMapping.objects.create(
                learning_outcome=lo,
                program_outcome=po,
                strength=strength,
            )

        # Midterm = 85, Project = 70
        project_grade = Grade.objects.get(
            enrollment=self.enrollment,
            assessment=self.project,
        )
        project_grade.score = 70
        project_grade.save()

        result1 = calculate_course_po_achievement(
            self.enrollment, self.po1
        )
        result2 = calculate_course_po_achievement(
            self.enrollment, po2
        )

        self.assertEqual(
            result1["score"].quantize(Decimal("0.01")),
            Decimal("77.23"),
        )
        self.assertEqual(
            result2["score"].quantize(Decimal("0.01")),
            Decimal("76.05"),
        )

        for result in [result1, result2]:
            self.assertEqual(result["coverage"], Decimal("100"))
            self.assertEqual(result["status"], "complete")

    def test_course_po_contribution(self):
        contribution = CoursePOContribution.objects.create(
            curriculum=self.enrollment.offering.curriculum,
            program_outcome=self.po1,
            weight=5,
        )

        self.assertEqual(contribution.weight, 5)

    def test_two_course_contribution_mappings(self):
        # Our existing course is CSE311.
        curriculum_311 = self.enrollment.offering.curriculum

        # Create a second course and its curriculum.
        course_321 = Course.objects.create(
            code="CSE321",
            title="Data Systems",
            credits=4,
        )

        curriculum_321 = CourseCurriculum.objects.create(
            course=course_321,
            version_number=1,
        )

        # Both courses contribute to the same PO.
        CoursePOContribution.objects.create(
            curriculum=curriculum_311,
            program_outcome=self.po1,
            weight=5,
        )

        CoursePOContribution.objects.create(
            curriculum=curriculum_321,
            program_outcome=self.po1,
            weight=3,
        )

        contributions = CoursePOContribution.objects.filter(
            program_outcome=self.po1
        )

        self.assertEqual(contributions.count(), 2)
        self.assertEqual(
            set(contributions.values_list("weight", flat=True)),
            {3, 5},
        )
    def test_student_po_uses_real_course_grades(self):
        student = self.enrollment.student
        first_offering = self.enrollment.offering

        Grade.objects.filter(
            enrollment=self.enrollment,
        ).update(score=80)

        CoursePOContribution.objects.create(
            curriculum=first_offering.curriculum,
            program_outcome=self.po1,
            weight=5,
        )

        course = Course.objects.create(
            code="CSE321",
            title="Data Systems",
            credits=4,
        )
        curriculum = CourseCurriculum.objects.create(
            course=course,
            version_number=1,
        )
        offering = CourseOffering.objects.create(
            course=course,
            curriculum=curriculum,
            instructor=first_offering.instructor,
            po_framework=self.po1.framework,
            year=2026,
            term="Fall",
        )
        enrollment = Enrollment.objects.create(
            student=student,
            offering=offering,
        )
        lo = LearningOutcome.objects.create(
            curriculum=curriculum,
            code="LO1",
            description="Apply data-system concepts.",
        )
        assessment = Assessment.objects.create(
            offering=offering,
            name="Midterm",
            max_score=100,
        )

        AssessmentLOMapping.objects.create(
            assessment=assessment,
            learning_outcome=lo,
            weight=100,
        )
        LOPOMapping.objects.create(
            learning_outcome=lo,
            program_outcome=self.po1,
            strength=5,
        )
        CoursePOContribution.objects.create(
            curriculum=curriculum,
            program_outcome=self.po1,
            weight=3,
        )
        grade = Grade.objects.create(
            enrollment=enrollment,
            assessment=assessment,
            score=60,
        )

        result = calculate_student_po_achievement(
            student, self.po1
        )

        self.assertEqual(result["score"], Decimal("72.5"))
        self.assertEqual(result["coverage"], Decimal("100"))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["courses"]), 2)

        grade.delete()

        result = calculate_student_po_achievement(
            student, self.po1
        )

        self.assertEqual(result["score"], Decimal("80"))
        self.assertEqual(result["coverage"], Decimal("62.5"))
        self.assertEqual(result["status"], "provisional")
        self.assertEqual(len(result["courses"]), 2)

class StudentPOAggregationTests(SimpleTestCase):

    def test_two_complete_courses(self):
        course_results = [
            (
                {
                    "score": Decimal("80"),
                    "coverage": Decimal("100"),
                    "status": "complete",
                },
                Decimal("5"),
            ),
            (
                {
                    "score": Decimal("60"),
                    "coverage": Decimal("100"),
                    "status": "complete",
                },
                Decimal("3"),
            ),
        ]

        result = aggregate_course_po_results(course_results)

        self.assertEqual(result["score"], Decimal("72.5"))
        self.assertEqual(result["coverage"], Decimal("100"))
        self.assertEqual(result["status"], "complete")

    def test_one_course_has_no_data(self):
        course_results = [
            (
                {
                    "score": Decimal("80"),
                    "coverage": Decimal("100"),
                    "status": "complete",
                },
                Decimal("5"),
            ),
            (
                {
                    "score": None,
                    "coverage": Decimal("0"),
                    "status": "no_data",
                },
                Decimal("3"),
            ),
        ]

        result = aggregate_course_po_results(course_results)

        self.assertEqual(result["score"], Decimal("80"))
        self.assertEqual(result["coverage"], Decimal("62.5"))
        self.assertEqual(result["status"], "provisional")

    def test_partially_graded_course(self):
        course_results = [
            (
                {
                    "score": Decimal("80"),
                    "coverage": Decimal("100"),
                    "status": "complete",
                },
                Decimal("5"),
            ),
            (
                {
                    "score": Decimal("60"),
                    "coverage": Decimal("50"),
                    "status": "provisional",
                },
                Decimal("3"),
            ),
        ]

        result = aggregate_course_po_results(course_results)

        self.assertAlmostEqual(
            result["score"],
            Decimal("75.384615"),
            places=5,
        )
        self.assertEqual(
            result["coverage"],
            Decimal("81.25"),
        )
        self.assertEqual(
            result["status"],
            "provisional",
        )

class PilotOutcomeTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.framework = POFramework.objects.get(
            program__code="PILOT",
            version_number=1,
        )

    def test_representative_student_outcomes(self):
        cases = (
            ("PILOT001", "PO1", None, "0.00", "no_data"),
            ("PILOT001", "PO2", "60.68", "87.50", "provisional"),
            ("PILOT001", "PO3", "82.86", "100.00", "complete"),
            ("PILOT001", "PO4", "0.00", "100.00", "complete"),
            ("PILOT001", "PO5", None, "0.00", "no_data"),
            ("PILOT002", "PO2", "75.48", "68.45", "provisional"),
            ("PILOT002", "PO3", "70.00", "28.57", "provisional"),
            ("PILOT002", "PO4", "80.00", "100.00", "complete"),
            ("PILOT002", "PO5", "80.00", "100.00", "complete"),
        )

        for number, code, score, coverage, status in cases:
            with self.subTest(student=number, outcome=code):
                student = Student.objects.get(
                    student_number=number,
                )
                outcome = ProgramOutcome.objects.get(
                    framework=self.framework,
                    code=code,
                )
                result = calculate_student_po_achievement(
                    student, outcome
                )

                if score is None:
                    self.assertIsNone(result["score"])
                else:
                    self.assertIsNotNone(result["score"])
                    self.assertEqual(
                        result["score"].quantize(Decimal("0.01")),
                        Decimal(score),
                    )

                self.assertEqual(
                    result["coverage"].quantize(Decimal("0.01")),
                    Decimal(coverage),
                )
                self.assertEqual(result["status"], status)
    def test_rerun_preserves_records_and_grade_edits(self):
        call_command("seed_demo", stdout=StringIO())

        grade = Grade.objects.get(
            enrollment__student__student_number="PILOT001",
            assessment__offering__course__code="PILOT321",
            assessment__name="Lab",
        )
        grade.score = Decimal("35")
        grade.save()

        models = (
            Program, POFramework, ProgramOutcome,
            Instructor, Course, CourseCurriculum, CourseOffering,
            LearningOutcome, Assessment, AssessmentLOMapping,
            LOPOMapping, CoursePOContribution,
            Student, Enrollment, Grade,
        )

        before = {
            model: list(
                model.objects.order_by("pk").values_list()
            )
            for model in models
        }

        call_command("seed_pilot", stdout=StringIO())

        for model in models:
            with self.subTest(model=model.__name__):
                self.assertEqual(
                    list(model.objects.order_by("pk").values_list()),
                    before[model],
                )

        grade.refresh_from_db()
        self.assertEqual(grade.score, Decimal("35"))
    def test_rejects_assessment_lo_from_another_curriculum(self):
        assessment = Assessment.objects.get(
            offering__course__code="PILOT321",
            offering__po_framework=self.framework,
            name="Midterm",
        )
        wrong_lo = LearningOutcome.objects.get(
            curriculum__course__code="PILOT311",
            curriculum__version_number=1,
            code="LO1",
        )

        with self.assertRaises(ValidationError):
            AssessmentLOMapping.objects.create(
                assessment=assessment,
                learning_outcome=wrong_lo,
                weight=100,
            )
    def pilot_page_urls(self):
        enrollment = Enrollment.objects.get(
            student__student_number="PILOT001",
            offering__course__code="PILOT321",
            offering__po_framework=self.framework,
        )

        return (
            reverse("student_list"),
            reverse(
                "student_outcomes",
                args=[enrollment.student_id, self.framework.pk],
            ),
            reverse("enrollment_outcomes", args=[enrollment.pk]),
        )

    def test_academic_pages_require_active_staff(self):
        user_model = get_user_model()
        users = (
            ("anonymous", None, False),
            (
                "non_staff",
                user_model.objects.create_user(
                    username="regular",
                    is_staff=False,
                ),
                False,
            ),
            (
                "staff",
                user_model.objects.create_user(
                    username="staff",
                    is_staff=True,
                ),
                True,
            ),
            (
                "inactive_staff",
                user_model.objects.create_user(
                    username="inactive",
                    is_staff=True,
                    is_active=False,
                ),
                False,
            ),
        )

        for label, user, allowed in users:
            self.client.logout()
            if user is not None:
                self.client.force_login(user)

            for url in self.pilot_page_urls():
                with self.subTest(user=label, url=url):
                    response = self.client.get(url)

                    if allowed:
                        self.assertEqual(response.status_code, 200)
                    else:
                        self.assertRedirects(
                            response,
                            f"{reverse('admin:login')}?next={url}",
                            fetch_redirect_response=False,
                        )
    def test_grade_editing_requires_change_permission(self):
        grade = Grade.objects.get(
            enrollment__student__student_number="PILOT001",
            assessment__offering__course__code="PILOT321",
            assessment__name="Midterm",
        )
        permission = Permission.objects.get(
            content_type__app_label="core",
            content_type__model="grade",
            codename="change_grade",
        )
        url = reverse("admin:core_grade_change", args=[grade.pk])

        for allowed in (False, True):
            with self.subTest(can_change_grade=allowed):
                user = get_user_model().objects.create_user(
                    username=f"grade_editor_{allowed}",
                    is_staff=True,
                )
                if allowed:
                    user.user_permissions.add(permission)

                self.client.force_login(user)
                page = self.client.get(
                    reverse(
                        "enrollment_outcomes",
                        args=[grade.enrollment_id],
                    )
                )
                edit_url = (
                    reverse("admin:core_grade_changelist")
                    + f"?enrollment__id__exact={grade.enrollment_id}"
                )

                self.assertEqual(page.status_code, 200)

                if allowed:
                    self.assertContains(page, edit_url)
                else:
                    self.assertNotContains(page, edit_url)
                response = self.client.post(url, {
                    "enrollment": grade.enrollment_id,
                    "assessment": grade.assessment_id,
                    "score": "35.00",
                    "_save": "Save",
                })

                self.assertEqual(
                    response.status_code,
                    302 if allowed else 403,
                )
                grade.refresh_from_db()
                self.assertEqual(
                    grade.score,
                    Decimal("35") if allowed else Decimal("0"),
                )
