"""Keep account administration separate from academic configuration."""

from django.contrib.admin import AdminSite
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from .access import ADMIN, LEGACY, MANAGERS, role_for


class SystemAdminSite(AdminSite):
    def has_permission(self, request):
        return super().has_permission(request) and role_for(request.user) in (ADMIN, LEGACY)


class AcademicAdminSite(AdminSite):
    site_header = "Gnosis academic configuration"
    site_title = "Academic configuration"
    site_url = "/manage/"

    def has_permission(self, request):
        return role_for(request.user) in MANAGERS

    def login(self, request, extra_context=None):
        if request.user.is_authenticated and not self.has_permission(request):
            raise PermissionDenied
        return redirect_to_login(
            request.GET.get("next") or reverse("academic_admin:index"), reverse("login"),
        )


academic_admin = AcademicAdminSite(name="academic_admin")
