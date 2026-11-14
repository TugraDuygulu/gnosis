"""Academic roles, object access, and navigation capabilities."""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.views.decorators.cache import never_cache

from .models import CourseOffering, Enrollment, Instructor, Student

COORDINATOR_GROUP = "Gnosis Coordinators"
ADMIN = "administrator"
COORDINATOR = "coordinator"
INSTRUCTOR = "instructor"
STUDENT = "student"
LEGACY = "legacy_staff"
MANAGERS = (ADMIN, COORDINATOR)
DIRECTORY = (*MANAGERS, LEGACY)
COURSES = (*DIRECTORY, INSTRUCTOR)
GRADERS = (ADMIN, INSTRUCTOR, LEGACY)


def role_for(user):
    if not user.is_authenticated or not user.is_active:
        return None
    if user.is_superuser:
        return ADMIN
    roles = []
    if user.groups.filter(name=COORDINATOR_GROUP).exists():
        roles.append(COORDINATOR)
    if Instructor.objects.filter(user_id=user.pk).exists():
        roles.append(INSTRUCTOR)
    if Student.objects.filter(user_id=user.pk).exists():
        roles.append(STUDENT)
    if roles:
        return roles[0] if len(roles) == 1 else None
    if user.is_staff:
        return LEGACY
    return None


def require_roles(*roles, legacy_permission=None):
    def decorator(view):
        @never_cache
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            role = role_for(request.user)
            if role is None:
                return redirect_to_login(request.get_full_path(), reverse("login"))
            if role not in roles or (
                role == LEGACY and legacy_permission and not request.user.has_perm(legacy_permission)
            ):
                raise PermissionDenied
            request.academic_role = role
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def offerings_for(request):
    offerings = CourseOffering.objects.all()
    if request.academic_role == INSTRUCTOR:
        return offerings.filter(instructor__user_id=request.user.pk)
    if request.academic_role in DIRECTORY:
        return offerings
    return offerings.none()


def enrollments_for(request):
    if request.academic_role == STUDENT:
        return Enrollment.objects.filter(student__user_id=request.user.pk)
    return Enrollment.objects.filter(offering__in=offerings_for(request))


def students_for(request):
    if request.academic_role == STUDENT:
        return Student.objects.filter(user_id=request.user.pk)
    if request.academic_role in DIRECTORY:
        return Student.objects.all()
    return Student.objects.none()


def academic_navigation(request):
    role = getattr(request, "academic_role", None) or role_for(request.user)

    def legacy_can(permission):
        return role == LEGACY and request.user.has_perm(permission)

    return {
        "academic_role": role,
        "academic_manager": role in MANAGERS,
        "academic_directory": role in DIRECTORY,
        "academic_system_admin": role in (ADMIN, LEGACY),
        "academic_can_grade": role in (ADMIN, INSTRUCTOR) or legacy_can("core.change_grade"),
        "academic_can_read_history": role in (*MANAGERS, INSTRUCTOR) or legacy_can("core.view_grade"),
        "academic_can_register": role in MANAGERS or legacy_can("core.add_student"),
        "academic_can_enroll": role in MANAGERS or legacy_can("core.add_enrollment"),
    }
