from django.contrib.auth import views as auth_views
from django.urls import path
from . import management_views as management, views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("manage/", management.index, name="management_home"),
    path("manage/<str:kind>/", management.records, name="management_records"),
    path("manage/<str:kind>/new/", management.edit, name="management_create"),
    path("manage/<str:kind>/<int:pk>/", management.edit, name="management_edit"),
    path("manage/<str:kind>/<int:pk>/account/", management.account, name="management_account"),
    path("enrollments/<int:pk>/status/", management.enrollment_status, name="management_enrollment_status"),
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
