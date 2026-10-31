from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    Program, POFramework, ProgramOutcome,
    Instructor, Course, CourseCurriculum, CourseOffering,
    LearningOutcome, Assessment, AssessmentLOMapping,
    LOPOMapping, CoursePOContribution,
    Student, Enrollment, Grade,
)

# Source: instructor's Team Project Brief, PDF page 2.
OFFICIAL_PO_DESCRIPTIONS = (
    (
        "Gain adequate knowledge in mathematics, science and related "
        "engineering discipline subjects; ability to use theoretical "
        "and applied knowledge in these fields in complex engineering "
        "problems."
    ),
    (
        "Gain ability to identify, formulate and solve complex engineering "
        "problems; gain ability to choose and apply appropriate analysis "
        "and modeling methods for this purpose."
    ),
    (
        "Gain ability to design a complex system, process, device or "
        "product to meet certain requirements under realistic constraints "
        "and conditions; ability to apply modern design methods for "
        "this purpose."
    ),
    (
        "Analyze and create solutions to complex problems encountered "
        "in engineering applications of modern techniques and tools "
        "for development, have skills, gain the ability to use "
        "information technology effectively."
    ),
    (
        "Gain ability to design experiments, conduct experiments, "
        "collect data, analyze and interpret results for the study "
        "of complex engineering problems or discipline-specific "
        "research topics."
    ),
    (
        "Gain ability to work effectively in interdisciplinary and "
        "multidisciplinary teams; work individually."
    ),
    (
        "Gain ability to communicate effectively in Turkish oral and "
        "written; knowledge of at least one foreign language; ability "
        "to write effective reports and understand written report, "
        "design and production reports, make effective presentations, "
        "give and receive clear and understandable instructions."
    ),
    (
        "Gain awareness of the need for lifelong learning; the ability "
        "to access information, monitor developments in science and "
        "technology, and constantly renew oneself."
    ),
    (
        "Act in accordance with ethical principles, awareness of "
        "professional and ethical responsibility; gain knowledge of "
        "standards used in engineering applications"
    ),
    (
        "Gain knowledge of business practices such as Project Management, "
        "risk Management and change management; gain awareness about "
        "entrepreneurship, innovation; have information about "
        "sustainable development."
    ),
    (
        "Gain knowledge of the effects of engineering practices on "
        "health, environment and safety in Universal and social "
        "dimensions and the problems reflected in the field of "
        "engineering of the era; gain awareness of the legal "
        "consequences of engineering solutions."
    ),
)

class Command(BaseCommand):
    help = "Create the representative fictional Gnosis pilot."

    @transaction.atomic
    def handle(self, *args, **options):
        program, _ = Program.objects.get_or_create(
            code="PILOT",
            defaults={"name": "Fictional Computer Engineering Pilot"},
        )
        framework, _ = POFramework.objects.get_or_create(
            program=program,
            version_number=1,
        )
        for number, description in enumerate(
            OFFICIAL_PO_DESCRIPTIONS,
            start=1,
        ):
            ProgramOutcome.objects.get_or_create(
                framework=framework,
                code=f"PO{number}",
                defaults={"description": description},
            )
        instructor, _ = Instructor.objects.get_or_create(
            email="pilot.instructor@example.invalid",
            defaults={"full_name": "Fictional Pilot Instructor"},
        )

        course_specs = (
            ("PILOT311", "Software Engineering (fictional pilot)"),
            ("PILOT321", "Data Systems (fictional pilot)"),
        )

        for code, title in course_specs:
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
                section="PILOT",
                defaults={
                    "curriculum": curriculum,
                    "instructor": instructor,
                    "po_framework": framework,
                },
            )
            lo_descriptions = {
                "PILOT311": (
                    "Analyze software requirements and constraints.",
                    "Design software that satisfies stated requirements.",
                ),
                "PILOT321": (
                    "Analyze relational data models and queries.",
                    "Investigate database behavior through experiments.",
                ),
            }

            for number, description in enumerate(
                lo_descriptions[code],
                start=1,
            ):
                LearningOutcome.objects.get_or_create(
                    curriculum=curriculum,
                    code=f"LO{number}",
                    defaults={"description": description},
                )

            practical_name = (
                "Project" if code == "PILOT311" else "Lab"
            )
            assessment_specs = (
                ("Midterm", 100, 40),
                (practical_name, 50, 60),
            )

            for name, maximum, grade_weight in assessment_specs:
                Assessment.objects.get_or_create(
                    offering=offering,
                    name=name,
                    defaults={
                        "max_score": maximum,
                        "course_grade_weight": grade_weight,
                    },
                )
            assessment_lo_specs = {
                "PILOT311": (
                    ("Midterm", "LO1", 60),
                    ("Project", "LO1", 40),
                    ("Midterm", "LO2", 40),
                    ("Project", "LO2", 100),
                ),
                "PILOT321": (
                    ("Midterm", "LO1", 100),
                    ("Lab", "LO2", 100),
                ),
            }

            for assessment_name, lo_code, weight in (
                assessment_lo_specs[code]
            ):
                assessment = Assessment.objects.get(
                    offering=offering,
                    name=assessment_name,
                )
                lo = LearningOutcome.objects.get(
                    curriculum=curriculum,
                    code=lo_code,
                )
                AssessmentLOMapping.objects.get_or_create(
                    assessment=assessment,
                    learning_outcome=lo,
                    defaults={"weight": weight},
                )
            lo_po_specs = {
                "PILOT311": (
                    ("LO1", "PO2", 2),
                    ("LO2", "PO2", 1),
                    ("LO2", "PO3", 5),
                ),
                "PILOT321": (
                    ("LO1", "PO2", 2),
                    ("LO2", "PO2", 1),
                    ("LO1", "PO4", 5),
                    ("LO2", "PO5", 5),
                ),
            }

            for lo_code, po_code, strength in lo_po_specs[code]:
                lo = LearningOutcome.objects.get(
                    curriculum=curriculum,
                    code=lo_code,
                )
                po = ProgramOutcome.objects.get(
                    framework=framework,
                    code=po_code,
                )
                LOPOMapping.objects.get_or_create(
                    learning_outcome=lo,
                    program_outcome=po,
                    defaults={"strength": strength},
                )

            contribution_specs = {
                "PILOT311": (("PO2", 5), ("PO3", 5)),
                "PILOT321": (("PO2", 3), ("PO4", 4), ("PO5", 4)),
            }

            for po_code, weight in contribution_specs[code]:
                po = ProgramOutcome.objects.get(
                    framework=framework,
                    code=po_code,
                )
                CoursePOContribution.objects.get_or_create(
                    curriculum=curriculum,
                    program_outcome=po,
                    defaults={"weight": weight},
                )
            self.stdout.write(f"Course offering ready: {offering}")
        student_specs = (
            (
                "PILOT001",
                "Pilot Student A",
                (
                    ("PILOT311", "Midterm", 90),
                    ("PILOT311", "Project", 40),
                    ("PILOT321", "Midterm", 0),
                    ("PILOT321", "Lab", None),
                ),
            ),
            (
                "PILOT002",
                "Pilot Student B",
                (
                    ("PILOT311", "Midterm", 70),
                    ("PILOT311", "Project", None),
                    ("PILOT321", "Midterm", 80),
                    ("PILOT321", "Lab", 40),
                ),
            ),
        )

        for student_number, full_name, grade_specs in student_specs:
            student, _ = Student.objects.get_or_create(
                student_number=student_number,
                defaults={
                    "program": program,
                    "full_name": full_name,
                },
            )

            for course_code, assessment_name, score in grade_specs:
                offering = CourseOffering.objects.get(
                    course__code=course_code,
                    year=2026,
                    term="Fall",
                    section="PILOT",
                    po_framework=framework,
                )
                enrollment, _ = Enrollment.objects.get_or_create(
                    student=student,
                    offering=offering,
                )
                assessment = Assessment.objects.get(
                    offering=offering,
                    name=assessment_name,
                )
                Grade.objects.get_or_create(
                    enrollment=enrollment,
                    assessment=assessment,
                    defaults={"score": score},
                )

            self.stdout.write(f"Pilot student ready: {student}")
        self.stdout.write(self.style.SUCCESS(
            f"Pilot framework ready: {framework}"
        ))