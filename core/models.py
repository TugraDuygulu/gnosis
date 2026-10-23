from django.db import models


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
        return f"{self.course.code} — Curriculum v{self.version_number}"
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