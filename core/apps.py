from django.apps import AppConfig
from django.contrib.admin import apps as admin_apps


class CoreConfig(AppConfig):
    name = "core"


class GnosisAdminConfig(admin_apps.AdminConfig):
    default = False
    default_site = "core.admin_sites.SystemAdminSite"
