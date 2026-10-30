from django.contrib import admin
from .models import (
    Program, Course, Instructor, Student,
    CourseCurriculum, CourseOffering, Enrollment,
    Assessment, Grade, LearningOutcome,
    AssessmentLOMapping, POFramework,
    ProgramOutcome, LOPOMapping,
    CoursePOContribution,
)

admin.site.register([
    Program, Course, Instructor, Student,
    CourseCurriculum, CourseOffering, Enrollment,
    Assessment, Grade, LearningOutcome,
    AssessmentLOMapping, POFramework,
    ProgramOutcome, LOPOMapping,
])
@admin.register(CoursePOContribution)
class CoursePOContributionAdmin(admin.ModelAdmin):
    list_display = ("curriculum", "program_outcome", "weight")
    list_select_related = (
        "curriculum__course",
        "program_outcome__framework",
    )