"""Coordinator workflows and restricted provisioning of academic logins."""

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, OperationalError, transaction
from django.forms import modelform_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .access import MANAGERS, require_roles
from .models import Course, CourseOffering, Enrollment, Instructor, Program, Student
from .student_intake import available_offerings

RECORDS = {
    "programs": (Program, "Program", ("code", "name"), ("code",)),
    "courses": (Course, "Course", ("code", "title", "credits"), ("code",)),
    "instructors": (Instructor, "Instructor", ("full_name", "email"), ("full_name", "pk")),
    "students": (Student, "Student", ("full_name", "student_number", "program"), ("full_name", "pk")),
    "offerings": (
        CourseOffering, "Offering",
        ("course", "curriculum", "instructor", "po_framework", "year", "term", "section", "status"),
        ("-year", "course__code", "term", "section"),
    ),
}
PEOPLE = ("students", "instructors")


def record_config(kind):
    try:
        return RECORDS[kind]
    except KeyError:
        raise Http404 from None


@require_roles(*MANAGERS)
@require_http_methods(["GET"])
def index(request):
    return render(request, "core/management_home.html", {
        "sections": [(kind, config[1]) for kind, config in RECORDS.items()],
    })


@require_roles(*MANAGERS)
@require_http_methods(["GET"])
def records(request, kind):
    model, label, _, order = record_config(kind)
    queryset = model.objects.order_by(*order)
    if kind in PEOPLE:
        queryset = queryset.select_related("user")
    elif kind == "offerings":
        queryset = queryset.select_related("course", "instructor")
    return render(request, "core/management_records.html", {
        "kind": kind, "label": label, "records": queryset, "has_accounts": kind in PEOPLE,
    })


def record_form(model, fields, record, data=None):
    form = modelform_factory(model, fields=fields)(data, instance=record)
    locked = ()
    if isinstance(record, Student) and record.enrollments.exists():
        locked = ("program",)
    if isinstance(record, CourseOffering):
        if record.enrollments.exists():
            locked = ("course", "curriculum", "po_framework", "year", "term", "section")
        elif record.assessments.exists():
            locked = ("course", "curriculum")
    for name in locked:
        form.fields[name].disabled = True
        form.fields[name].help_text = "Fixed because this record has related academic history."
    return form


@require_roles(*MANAGERS)
@require_http_methods(["GET", "POST"])
def edit(request, kind, pk=None):
    model, label, fields, _ = record_config(kind)
    record = get_object_or_404(model, pk=pk) if pk is not None else None
    form = record_form(model, fields, record)
    if request.method == "POST":
        saved = None
        try:
            with transaction.atomic():
                if pk is not None:
                    record = get_object_or_404(model.objects.select_for_update(), pk=pk)
                form = record_form(model, fields, record, request.POST)
                if form.is_valid():
                    saved = form.save()
        except IntegrityError:
            form.add_error(None, "This record conflicts with existing data. Review the fields.")
        except OperationalError as error:
            handle_lock_error(form, error)
        else:
            if saved is not None:
                messages.success(request, f"{label} saved.")
                if kind == "offerings":
                    return redirect("offering_detail", offering_id=saved.pk)
                if kind == "students":
                    return redirect("student_detail", student_id=saved.pk)
                return redirect("management_records", kind=kind)
    return render(request, "core/management_form.html", {
        "form": form, "label": label, "kind": kind, "editing": pk is not None,
    })


def handle_lock_error(form, error):
    if "locked" not in str(error).lower():
        raise error
    form.add_error(None, "Another save is in progress. Reload and try again.")


def manageable_user(record, other_model, *, lock=False):
    if record.user_id is None:
        return None
    users = get_user_model().objects.all()
    if lock:
        users = users.select_for_update()
    user = get_object_or_404(users, pk=record.user_id)
    # Coordinators can reset only dedicated academic logins.
    if (user.is_staff or user.is_superuser or user.groups.exists()
            or user.user_permissions.exists() or other_model.objects.filter(user=user).exists()):
        raise PermissionDenied
    return user


def check_account_fields(data, fields=()):
    allowed = {"csrfmiddlewaretoken", "action", *fields}
    if data.keys() - allowed or any(len(values) != 1 for _, values in data.lists()):
        raise PermissionDenied


@require_roles(*MANAGERS)
@require_http_methods(["GET", "POST"])
def account(request, kind, pk):
    if kind not in PEOPLE:
        raise Http404
    model, label, _, _ = record_config(kind)
    other_model = Student if model is Instructor else Instructor
    record = get_object_or_404(model, pk=pk)
    user = manageable_user(record, other_model)
    form = SetPasswordForm(user) if user else UserCreationForm()
    if request.method == "POST":
        try:
            with transaction.atomic():
                record = get_object_or_404(model.objects.select_for_update(), pk=pk)
                user = manageable_user(record, other_model, lock=True)
                action = request.POST.get("action")
                if action == "create" and user is None:
                    form = UserCreationForm(request.POST)
                    check_account_fields(request.POST, form.fields)
                    if form.is_valid():
                        record.user = form.save()
                        record.save(update_fields=["user"])
                        messages.success(request, f"{label} login created.")
                        return redirect("management_account", kind=kind, pk=pk)
                elif action == "reset" and user is not None:
                    form = SetPasswordForm(user, request.POST)
                    check_account_fields(request.POST, form.fields)
                    if form.is_valid():
                        form.save()
                        messages.success(request, "Password updated.")
                        return redirect("management_account", kind=kind, pk=pk)
                elif action in ("enable", "disable") and user is not None:
                    check_account_fields(request.POST)
                    user.is_active = action == "enable"
                    if not user.is_active:
                        user.set_unusable_password()
                    user.save(update_fields=["is_active", "password"])
                    messages.success(request, "Login enabled." if user.is_active else "Login disabled.")
                    return redirect("management_account", kind=kind, pk=pk)
                else:
                    raise PermissionDenied
        except IntegrityError:
            form.add_error(None, "The username or record changed. Reload and try again.")
        except OperationalError as error:
            handle_lock_error(form, error)
    return render(request, "core/management_account.html", {
        "form": form, "label": label, "record": record, "account": user, "kind": kind,
    })


class EnrollmentStatusForm(forms.Form):
    status = forms.ChoiceField(choices=[("active", "Active"), ("withdrawn", "Withdrawn")])


@require_roles(*MANAGERS)
@require_http_methods(["GET", "POST"])
def enrollment_status(request, pk):
    enrollment = get_object_or_404(Enrollment.objects.select_related("student", "offering"), pk=pk)
    choices = list(EnrollmentStatusForm.base_fields["status"].choices)
    if enrollment.status not in dict(choices):
        choices.insert(0, (enrollment.status, enrollment.status))
    form = EnrollmentStatusForm(
        request.POST if request.method == "POST" else None, initial={"status": enrollment.status},
    )
    form.fields["status"].choices = choices
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                student = get_object_or_404(Student.objects.select_for_update(), pk=enrollment.student_id)
                offering = get_object_or_404(
                    CourseOffering.objects.select_for_update(), pk=enrollment.offering_id,
                )
                current = get_object_or_404(Enrollment.objects.select_for_update(), pk=pk)
                if current.student_id != student.pk or current.offering_id != offering.pk:
                    raise ValidationError("This enrollment changed. Reload and try again.")
                status = form.cleaned_data["status"]
                if status != current.status:
                    if status not in ("active", "withdrawn"):
                        raise ValidationError("This enrollment status changed. Reload and try again.")
                    if status == "active" and not available_offerings(
                        student, ignore_enrollment=current.pk,
                    ).filter(pk=offering.pk).exists():
                        raise ValidationError("This enrollment cannot be reactivated under current course rules.")
                    current.status = status
                    current.save(update_fields=["status"])
        except ValidationError as error:
            form.add_error(None, error)
        except OperationalError as error:
            handle_lock_error(form, error)
        else:
            messages.success(request, "Enrollment status updated.")
            return redirect("student_detail", student_id=enrollment.student_id)
    return render(request, "core/management_form.html", {
        "form": form, "label": "Enrollment status", "enrollment": enrollment, "editing": True,
    })
