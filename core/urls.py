from django.urls import path
from . import views

urlpatterns = [
    path(
        "enrollments/<int:enrollment_id>/outcomes/",
        views.enrollment_outcomes,
        name="enrollment_outcomes",
    ),
]