from django.db import models

from django.core.exceptions import ValidationError

class Program(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.code} — {self.name}"


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    credits = models.DecimalField(
        max_digits=4,
        decimal_places=1,
    )

    def __str__(self):
        return f"{self.code} — {self.title}"


class Instructor(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.full_name
class Student(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name="students",
    )
    student_number = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.student_number} — {self.full_name}"


class CourseCurriculum(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="curriculum_versions",
    )
    version_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        default="draft",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "version_number"],
                name="unique_course_curriculum_version",
            )
        ]
    def __str__(self):
        return f"{self.course.code} - Curriculum v{self.version_number}"

class POFramework(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name="po_frameworks",
    )
    version_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default="draft")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["program", "version_number"],
                name="unique_program_po_framework_version",
            )
        ]

    def __str__(self):
        return f"{self.program.code} PO Framework v{self.version_number}"

class ProgramOutcome(models.Model):
    framework = models.ForeignKey(
        POFramework,
        on_delete=models.PROTECT,
        related_name="program_outcomes",
    )
    code = models.CharField(max_length=20)
    description = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["framework", "code"],
                name="unique_program_outcome_code_per_framework",
            )
        ]

    def __str__(self):
        return f"{self.framework} - {self.code}"

class CourseOffering(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="offerings",
    )
    curriculum = models.ForeignKey(
        CourseCurriculum,
        on_delete=models.PROTECT,
        related_name="offerings",
    )
    instructor = models.ForeignKey(
        Instructor,
        on_delete=models.PROTECT,
        related_name="offerings",
    )
    po_framework = models.ForeignKey(
        "POFramework",
        on_delete=models.PROTECT,
        related_name="offerings",
        null=True,
        blank=True,
    )
    year = models.PositiveIntegerField()
    term = models.CharField(max_length=20)
    section = models.CharField(max_length=10, default="1")
    status = models.CharField(max_length=20, default="draft")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "year", "term", "section"],
                name="unique_course_offering",
            )
        ]

    def clean(self):
        super().clean()

        if self.course_id and self.curriculum_id:
            if self.course_id != self.curriculum.course_id:
                raise ValidationError({
                    "curriculum": (
                        "The selected curriculum must belong "
                        "to the offering's course."
                    )
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.course.code} — "
            f"{self.term} {self.year} (Section {self.section})"
        )


class Enrollment(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    status = models.CharField(max_length=20, default="active")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "offering"],
                name="unique_student_enrollment",
            )
        ]

    def __str__(self):
        return f"{self.student.student_number} — {self.offering}"
class Assessment(models.Model):
    offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.PROTECT,
        related_name="assessments",
    )
    name = models.CharField(max_length=100)
    max_score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
    )
    course_grade_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_score__gt=0),
                name="positive_assessment_max_score",
            ),
        ]
    def __str__(self):
        return f"{self.offering} — {self.name}"


class Grade(models.Model):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="grades",
    )
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.PROTECT,
        related_name="grades",
    )
    score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    def clean(self):
        super().clean()

        if self.score is not None:
            if self.score < 0:
                raise ValidationError({
                    "score": "A grade cannot be negative."
                })

            if self.assessment_id and self.score > self.assessment.max_score:
                raise ValidationError({
                    "score": "A grade cannot exceed the assessment's maximum score."
                })

        if self.enrollment_id and self.assessment_id:
            if self.enrollment.offering_id != self.assessment.offering_id:
                raise ValidationError(
                    "The assessment and enrollment must belong to the same course offering."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "assessment"],
                name="unique_enrollment_assessment_grade",
            )
        ]

    def __str__(self):
        return f"{self.enrollment} — {self.assessment.name}: {self.score}"


class LearningOutcome(models.Model):
    curriculum = models.ForeignKey(
        CourseCurriculum,
        on_delete=models.PROTECT,
        related_name="learning_outcomes",
    )
    code = models.CharField(max_length=20)
    description = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["curriculum", "code"],
                name="unique_learning_outcome_per_curriculum",
            )
        ]

    def __str__(self):
        return f"{self.curriculum.course.code} {self.code}"
class AssessmentLOMapping(models.Model):
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.PROTECT,
        related_name="lo_mappings",
    )
    learning_outcome = models.ForeignKey(
        LearningOutcome,
        on_delete=models.PROTECT,
        related_name="assessment_mappings",
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "learning_outcome"],
                name="unique_assessment_lo_mapping",
            ),
            models.CheckConstraint(
                condition=models.Q(weight__gt=0),
                name="positive_assessment_lo_weight",
            ),
        ]
    def clean(self):
        super().clean()

        if self.assessment_id and self.learning_outcome_id:
            curriculum_id = self.assessment.offering.curriculum_id

            if self.learning_outcome.curriculum_id != curriculum_id:
                raise ValidationError({
                    "learning_outcome": (
                        "The learning outcome must belong to "
                        "the assessment offering's curriculum."
                    )
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.assessment.name} → "
            f"{self.learning_outcome.code} ({self.weight}%)"
        )
class LOPOMapping(models.Model):
    learning_outcome = models.ForeignKey(
        LearningOutcome,
        on_delete=models.PROTECT,
        related_name="po_mappings",
    )
    program_outcome = models.ForeignKey(
        ProgramOutcome,
        on_delete=models.PROTECT,
        related_name="lo_mappings",
    )
    strength = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["learning_outcome", "program_outcome"],
                name="unique_lo_po_mapping",
            ),
            models.CheckConstraint(
                condition=models.Q(strength__gte=1, strength__lte=5),
                name="lo_po_strength_between_1_and_5",
            ),
        ]

    def __str__(self):
        return (
            f"{self.learning_outcome.code} → "
            f"{self.program_outcome.code} "
            f"(strength {self.strength})"
        )

class CoursePOContribution(models.Model):
    curriculum = models.ForeignKey(
        CourseCurriculum,
        on_delete=models.PROTECT,
        related_name="po_contributions",
    )

    program_outcome = models.ForeignKey(
        ProgramOutcome,
        on_delete=models.PROTECT,
        related_name="course_contributions",
    )

    weight = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["curriculum", "program_outcome"],
                name="unique_course_po_contribution",
            ),
            models.CheckConstraint(
                condition=models.Q(weight__gte=1, weight__lte=5),
                name="course_po_weight_between_1_and_5",
            ),
        ]
