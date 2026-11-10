from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group
from django.db import transaction

from core.access import MANAGERS, role_for
from core.admin_sites import academic_admin
from core.grade_history import grade_state, record_grade_change
from .models import (
    Program, Course, Instructor, Student,
    CourseCurriculum, CourseOffering, Enrollment,
    Assessment, Grade, LearningOutcome,
    AssessmentLOMapping, POFramework,
    ProgramOutcome, LOPOMapping,
    CoursePOContribution,
)

admin.site.site_header = "Gnosis administration"
admin.site.site_title = "Gnosis admin"
admin.site.index_title = "Courses, outcomes and mappings"
admin.site.site_url = "/"
# Give the full Admin login the workspace look.
admin.site.login_template = "core/login.html"

admin.site.register([
    Program, Course,
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


class AcademicPersonAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return () if request.user.is_superuser else ("user",)


admin.site.register([Instructor, Student], AcademicPersonAdmin)


class AdministratorOnly:
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    has_add_permission = has_change_permission = has_delete_permission = has_view_permission


class SystemUserAdmin(AdministratorOnly, UserAdmin):
    pass


class SystemGroupAdmin(AdministratorOnly, GroupAdmin):
    pass


admin.site.unregister(get_user_model())
admin.site.unregister(Group)
admin.site.register(get_user_model(), SystemUserAdmin)
admin.site.register(Group, SystemGroupAdmin)


class AcademicConfigurationAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return role_for(request.user) in MANAGERS

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    has_change_permission = has_view_permission
    has_add_permission = has_module_permission

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        if obj is None or request.user.is_superuser:
            return ()
        fields = [field.name for field in obj._meta.fields if field.many_to_one]
        if isinstance(obj, Assessment) and Grade.objects.filter(assessment=obj).exists():
            fields.append("max_score")
        return fields


academic_admin.register([
    CourseCurriculum, POFramework, ProgramOutcome, Assessment, LearningOutcome,
    AssessmentLOMapping, LOPOMapping, CoursePOContribution,
], AcademicConfigurationAdmin)
