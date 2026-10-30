from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    Program, Student, Instructor, POFramework, ProgramOutcome,
    Course, CourseCurriculum, CourseOffering, Enrollment,
    Assessment, Grade, LearningOutcome,
    AssessmentLOMapping, LOPOMapping, CoursePOContribution,
)


class Command(BaseCommand):
    help = "Create fictional data for the two-course Gnosis demo."

    @transaction.atomic
    def handle(self, *args, **options):
        program, _ = Program.objects.get_or_create(
            code="DEMO",
            defaults={"name": "Fictional Engineering Demo"},
        )
        student, _ = Student.objects.get_or_create(
            student_number="DEMO001",
            defaults={
                "program": program,
                "full_name": "Demo Student",
            },
        )
        instructor, _ = Instructor.objects.get_or_create(
            email="instructor@example.invalid",
            defaults={"full_name": "Demo Instructor"},
        )
        framework, _ = POFramework.objects.get_or_create(
            program=program,
            version_number=1,
        )
        po, _ = ProgramOutcome.objects.get_or_create(
            framework=framework,
            code="PO1",
            defaults={
                "description": (
                    "Solve engineering problems "
                    "(fictional demonstration outcome)."
                ),
            },
        )

        course_specs = [
            ("DEMO311", "Software Engineering Demo", 80, 5),
            ("DEMO321", "Data Systems Demo", 60, 3),
        ]

        for code, title, score, weight in course_specs:
            course, _ = Course.objects.get_or_create(
                code=code,
                defaults={"title": title, "credits": 4},
            )
            curriculum, _ = CourseCurriculum.objects.get_or_create(
                course=course,
                version_number=1,
            )
            offering, _ = CourseOffering.objects.get_or_create(
                course=course,
                year=2026,
                term="Fall",
                section="DEMO",
                defaults={
                    "curriculum": curriculum,
                    "instructor": instructor,
                    "po_framework": framework,
                },
            )
            enrollment, _ = Enrollment.objects.get_or_create(
                student=student,
                offering=offering,
            )
            lo, _ = LearningOutcome.objects.get_or_create(
                curriculum=curriculum,
                code="LO1",
                defaults={
                    "description": f"Apply concepts from {title}.",
                },
            )
            assessment, _ = Assessment.objects.get_or_create(
                offering=offering,
                name="Demo Assessment",
                defaults={
                    "max_score": 100,
                    "course_grade_weight": 100,
                },
            )
            AssessmentLOMapping.objects.get_or_create(
                assessment=assessment,
                learning_outcome=lo,
                defaults={"weight": 100},
            )
            LOPOMapping.objects.get_or_create(
                learning_outcome=lo,
                program_outcome=po,
                defaults={"strength": 5},
            )
            CoursePOContribution.objects.get_or_create(
                curriculum=curriculum,
                program_outcome=po,
                defaults={"weight": weight},
            )
            Grade.objects.get_or_create(
                enrollment=enrollment,
                assessment=assessment,
                defaults={"score": score},
            )

        self.stdout.write(self.style.SUCCESS(
            "Demo records are ready. Open / and choose Demo Student."
        ))