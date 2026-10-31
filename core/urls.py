from django.urls import path
from . import views

urlpatterns = [
    path("courses/", views.course_list, name="course_list"),
    path("offerings/<int:offering_id>/", views.offering_detail, name="offering_detail"),
    path(
        "enrollments/<int:enrollment_id>/grades/",
        views.enrollment_grade_editor,
        name="enrollment_grade_editor",
    ),
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
