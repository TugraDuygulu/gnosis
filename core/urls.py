from django.urls import path
from . import views

urlpatterns = [
    path(
        "enrollments/<int:enrollment_id>/outcomes/",
        views.enrollment_outcomes,
        name="enrollment_outcomes",
    ),
    path(
        "students/<int:student_id>/frameworks/<int:framework_id>/outcomes/",
        views.student_outcomes,
        name="student_outcomes",
    ),
    path("", views.student_list, name="student_list"),
]