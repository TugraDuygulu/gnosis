from django.contrib import admin
from django.db import transaction
from core.grade_history import grade_state, record_grade_change
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
    Assessment, LearningOutcome,
    AssessmentLOMapping, POFramework,
    ProgramOutcome, LOPOMapping,
])


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "assessment", "score")
    list_select_related = ("enrollment__student", "enrollment__offering__course", "assessment")

    def get_readonly_fields(self, request, obj=None):
        # A correction changes a score, not the student or assessment identity.
        return ("enrollment", "assessment") if obj else ()

    def save_model(self, request, obj, form, change):
        before = grade_state(Grade.objects.select_for_update().get(pk=obj.pk)) if change else None
        super().save_model(request, obj, form, change)
        record_grade_change(request.user, obj, before, source="Django Admin",
                            operation="change" if change else "create")

    def log_addition(self, request, obj, message):
        pass  # Structured history was saved in save_model's Admin transaction.

    def log_change(self, request, obj, message):
        pass

    def log_deletions(self, request, queryset):
        pass  # Log inside delete_model/delete_queryset, including bulk deletion.

    @transaction.atomic
    def delete_model(self, request, obj):
        grade = Grade.objects.select_for_update().get(pk=obj.pk)
        record_grade_change(request.user, grade, grade_state(grade),
                            source="Django Admin", operation="delete")
        super().delete_model(request, grade)

    @transaction.atomic
    def delete_queryset(self, request, queryset):
        for grade in queryset.select_for_update():
            record_grade_change(request.user, grade, grade_state(grade),
                                source="Django Admin", operation="delete")
        super().delete_queryset(request, queryset)


@admin.register(CoursePOContribution)
class CoursePOContributionAdmin(admin.ModelAdmin):
    list_display = ("curriculum", "program_outcome", "weight")
    list_select_related = (
        "curriculum__course",
        "program_outcome__framework",
    )
