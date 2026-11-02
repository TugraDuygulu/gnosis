from django.urls import path
from . import views

urlpatterns = [
    path("students/new/", views.student_register, name="student_register"),
    path("students/<int:student_id>/", views.student_detail, name="student_detail"),
    path("students/<int:student_id>/enroll/", views.student_enroll, name="student_enroll"),
    path("enrollments/<int:enrollment_id>/grades/history/",
         views.enrollment_grade_history, name="enrollment_grade_history"),
    path("overview/", views.program_overview, name="program_overview"),
    path("courses/", views.course_list, name="course_list"),
    path("offerings/<int:offering_id>/", views.offering_detail, name="offering_detail"),
    path("offerings/<int:offering_id>/grades/", views.offering_gradebook, name="offering_gradebook"),
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
