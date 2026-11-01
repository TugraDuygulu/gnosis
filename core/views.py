from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.grade_editor import (
    EnrollmentGradeForm, revision_token, save_grades, snapshot, STALE_MESSAGE,
)
from core.grade_history import history_entries, history_row
from core.student_intake import StudentRegistrationForm, StudentEnrollmentForm, enroll_student

from core.models import (
    AssessmentLOMapping,
    CoursePOContribution,
    Enrollment,
    LearningOutcome,
    ProgramOutcome,
    Student,
    POFramework,
    Grade,
    LOPOMapping,
    CourseOffering,
)
from core.services.lo_calculator import calculate_lo_achievement
from core.services.po_calculator import calculate_course_po_achievement
from core.services.student_po_calculator import (
    calculate_student_po_achievement,
)


def evidence_state(result, has_source):
    """Display state for one result: full, some, none, unmeasured or error."""
    if result.get("error"):
        return "error"
    if not has_source:
        return "unmeasured"
    if result.get("score") is None:
        return "none"
    return "full" if result.get("status") == "complete" else "some"


def missing_assessments(enrollment):
    """Assessments of the enrollment's offering without a recorded score."""
    graded = set(Grade.objects.filter(
        enrollment=enrollment, score__isnull=False,
    ).values_list("assessment_id", flat=True))
    return [
        assessment
        for assessment in enrollment.offering.assessments.order_by("pk")
        if assessment.pk not in graded
    ]

@staff_member_required
@permission_required("core.view_grade", raise_exception=True)
@require_http_methods(["GET"])
def enrollment_grade_history(request, enrollment_id):
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("student", "offering__course"),
        pk=enrollment_id,
    )
    page = Paginator(history_entries(enrollment.pk), 50).get_page(request.GET.get("page"))
    return render(request, "core/enrollment_grade_history.html", {
        "enrollment": enrollment, "page": page,
        "history": [history_row(entry) for entry in page],
    })


@staff_member_required
@permission_required("core.add_student", raise_exception=True)
@require_http_methods(["GET", "POST"])
def student_register(request):
    form = StudentRegistrationForm(request.POST if request.method == "POST" else None, label_suffix="")
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                student = form.save()
        except IntegrityError:
            form.add_error(None, "This student number already exists or the program changed. Review the details.")
        except OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            form.add_error(None, "Another save is in progress. Nothing was saved. Try again.")
        else:
            messages.success(request, "Student registered. You can now enroll them in a course offering.")
            return redirect("student_detail", student_id=student.pk)
    return render(request, "core/intake_form.html", {
        "form": form, "page_title": "Register student", "submit_label": "Register student",
        "cancel_url": "student_list", "has_choices": form.fields["program"].queryset.exists(),
        "intro": "Create an academic student record. This does not create a login account.",
        "empty_message": "No programs configured. Ask an administrator to set up a program first.",
    })


@staff_member_required
@require_http_methods(["GET"])
def student_detail(request, student_id):
    student = get_object_or_404(Student.objects.select_related("program"), pk=student_id)
    enrollments = student.enrollments.select_related(
        "offering__course", "offering__po_framework",
    ).annotate(
        assessment_total=Count("offering__assessments", distinct=True),
        graded_total=Count("grades", filter=Q(grades__score__isnull=False), distinct=True),
    ).order_by("-offering__year", "offering__term", "offering__course__code", "pk")
    return render(request, "core/student_detail.html", {
        "student": student, "enrollments": enrollments,
        "frameworks": student.program.po_frameworks.order_by("version_number", "pk"),
    })


@staff_member_required
@permission_required("core.add_enrollment", raise_exception=True)
@require_http_methods(["GET", "POST"])
def student_enroll(request, student_id):
    student = get_object_or_404(Student.objects.select_related("program"), pk=student_id)
    form = StudentEnrollmentForm(student, request.POST if request.method == "POST" else None, label_suffix="")
    if request.method == "POST" and form.is_valid():
        try:
            enrollment = enroll_student(student.pk, form.cleaned_data["offering"].pk)
        except (Student.DoesNotExist, CourseOffering.DoesNotExist, IntegrityError):
            form.add_error(None, "The student, offering or enrollment changed. Reload before trying again.")
        except ValidationError as error:
            form.add_error(None, error)
        except OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            form.add_error(None, "Another save is in progress. Nothing was saved. Reload and try again.")
        else:
            messages.success(request, f"Enrolled in {enrollment.offering}. No grades have been recorded yet.")
            return redirect("student_detail", student_id=student.pk)
    return render(request, "core/intake_form.html", {
        "form": form, "student": student, "page_title": "Enroll student",
        "submit_label": "Enroll student", "cancel_url": "student_detail",
        "has_choices": form.fields["offering"].queryset.exists(),
        "intro": "Choose an existing offering with a framework for this student's program. Enrollment will be active.",
        "empty_message": "No eligible offerings. Existing enrollments and repeated active courses are excluded. "
                         "Ask an administrator to configure a same-program framework and matching course curriculum if needed.",
    })


@staff_member_required
def enrollment_outcomes(request, enrollment_id):
    enrollment = get_object_or_404(
        Enrollment,
        pk=enrollment_id,
    )

    offering = enrollment.offering
    grades_by_assessment = {
        grade.assessment_id: grade
        for grade in Grade.objects.filter(enrollment=enrollment)
    }

    assessment_results = []
    lo_sources = {}
    for assessment in offering.assessments.order_by("pk"):
        grade = grades_by_assessment.get(assessment.pk)
        score = grade.score if grade is not None else None
        mappings = assessment.lo_mappings.select_related(
            "learning_outcome"
        ).order_by("learning_outcome__pk")

        assessment_results.append({
            "assessment": assessment,
            "score": score,
            "mappings": mappings,
        })
        for mapping in mappings:
            lo_sources.setdefault(mapping.learning_outcome_id, []).append({
                "assessment": assessment,
                "score": score,
                "weight": mapping.weight,
            })

    lo_results = []
    lo_by_id = {}
    for lo in LearningOutcome.objects.filter(
        curriculum=offering.curriculum
    ):
        result = calculate_lo_achievement(enrollment, lo)
        sources = lo_sources.get(lo.pk, [])
        row = {
            "outcome": lo,
            **result,
            "sources": sources,
            "state": evidence_state(result, bool(sources)),
        }
        lo_results.append(row)
        lo_by_id[lo.pk] = row

    po_results = []
    unmapped_po_count = 0
    if offering.po_framework:
        for po in ProgramOutcome.objects.filter(
            framework=offering.po_framework
        ):
            mappings = LOPOMapping.objects.filter(
                program_outcome=po,
                learning_outcome__curriculum=offering.curriculum,
            ).select_related(
                "learning_outcome"
            ).order_by("learning_outcome__pk")
            if not mappings:
                unmapped_po_count += 1
                continue
            result = calculate_course_po_achievement(enrollment, po)
            po_results.append({
                "outcome": po,
                **result,
                "mappings": mappings,
                "sources": [
                    {"mapping": mapping, "lo": lo_by_id.get(mapping.learning_outcome_id)}
                    for mapping in mappings
                ],
                "state": evidence_state(result, True),
            })
    missing = missing_assessments(enrollment)
    return render(request, "core/enrollment_outcomes.html", {
        "enrollment": enrollment,
        "lo_results": lo_results,
        "po_results": po_results,
        "unmapped_po_count": unmapped_po_count,
        "assessment_results": assessment_results,
        "missing": missing,
        "graded_count": len(assessment_results) - len(missing),
    })
@staff_member_required
def student_outcomes(request, student_id, framework_id):
    student = get_object_or_404(
        Student.objects.select_related("program"),
        pk=student_id,
    )
    framework = get_object_or_404(
        POFramework,
        pk=framework_id,
        program=student.program,
    )

    enrollments = student.enrollments.filter(
        status="active",
        offering__po_framework=framework,
    ).select_related("offering__course", "offering__instructor").order_by("offering__course__code", "pk")

    # Missing grades and the program outcomes each one holds back.
    contributions = set(CoursePOContribution.objects.filter(
        program_outcome__framework=framework,
    ).values_list("curriculum_id", "program_outcome_id"))
    attention = []
    missing_by_course_po = {}
    courses = []
    for enrollment in enrollments:
        missing = missing_assessments(enrollment)
        total = enrollment.offering.assessments.count()
        courses.append({
            "enrollment": enrollment,
            "total": total,
            "graded": total - len(missing),
        })
        for assessment in missing:
            po_ids = set(LOPOMapping.objects.filter(
                learning_outcome__assessment_mappings__assessment=assessment,
                program_outcome__framework=framework,
            ).values_list("program_outcome_id", flat=True))
            po_ids = {
                po_id for po_id in po_ids
                if (enrollment.offering.curriculum_id, po_id) in contributions
            }
            for po_id in po_ids:
                missing_by_course_po.setdefault((enrollment.pk, po_id), []).append(assessment)
            attention.append({
                "enrollment": enrollment,
                "assessment": assessment,
                "outcomes": sorted(
                    ProgramOutcome.objects.filter(pk__in=po_ids),
                    key=lambda outcome: (len(outcome.code), outcome.code),
                ),
            })

    po_results = []
    outcomes = sorted(
        framework.program_outcomes.all(),
        key=lambda outcome: (len(outcome.code), outcome.code),
    )
    for po in outcomes:
        row = {"outcome": po}

        try:
            row.update(
                calculate_student_po_achievement(student, po)
            )
        except ValueError as error:
            row["error"] = str(error)

        for course in row.get("courses", []):
            course["missing"] = missing_by_course_po.get((course["enrollment"].pk, po.pk), [])
        row["state"] = evidence_state(row, bool(row.get("courses")))
        po_results.append(row)

    states = [row["state"] for row in po_results]
    return render(request, "core/student_outcomes.html", {
        "student": student,
        "framework": framework,
        "frameworks": student.program.po_frameworks.order_by("version_number", "pk"),
        "enrollments": enrollments,
        "po_results": po_results,
        "courses": courses,
        "attention": attention,
        "attention_courses": len({item["enrollment"].pk for item in attention}),
        "scored_count": states.count("full") + states.count("some"),
        "pending_count": states.count("some") + states.count("none"),
        "unmeasured_count": states.count("unmeasured"),
    })
@staff_member_required
def student_list(request):
    query = request.GET.get("q", "").strip()
    students = (
        Student.objects
        .select_related("program")
        .prefetch_related("program__po_frameworks")
        .annotate(active_courses=Count("enrollments", filter=Q(enrollments__status="active")))
        .order_by("full_name", "pk")
    )
    if query:
        students = students.filter(
            Q(full_name__icontains=query) | Q(student_number__icontains=query)
            | Q(program__name__icontains=query) | Q(program__code__icontains=query)
        )

    return render(request, "core/student_list.html", {
        "students": students,
        "query": query,
    })


@staff_member_required
@permission_required("core.change_grade", raise_exception=True)
@require_http_methods(["GET", "POST"])
def enrollment_grade_editor(request, enrollment_id):
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("student", "offering__course"),
        pk=enrollment_id,
    )
    assessments, grades, revision = snapshot(enrollment)
    form = EnrollmentGradeForm(
        assessments, grades,
        request.POST if request.method == "POST" else None,
        initial={"revision": revision_token(enrollment, request.user, revision)},
    )
    if request.method == "POST" and form.is_valid():
        try:
            save_grades(enrollment.pk, request.user, form)
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            form.add_error(None, STALE_MESSAGE)
        except OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            form.add_error(None, "Another save is in progress. Nothing was saved. "
                           "Reload grades and try again.")
        else:
            messages.success(request, "Grades saved. Outcome results are up to date.")
            return redirect("enrollment_outcomes", enrollment_id=enrollment.pk)
    feeds = {}
    for mapping in AssessmentLOMapping.objects.filter(
        assessment__in=assessments,
    ).select_related("learning_outcome").order_by("learning_outcome__code"):
        feeds.setdefault(mapping.assessment_id, []).append(mapping.learning_outcome.code)
    return render(request, "core/enrollment_grade_editor.html", {
        "enrollment": enrollment,
        "form": form,
        "has_assessments": bool(assessments),
        "rows": [
            {"field": form[f"score_{assessment.pk}"], "assessment": assessment,
             "feeds": feeds.get(assessment.pk, [])}
            for assessment in assessments
        ],
    })


@staff_member_required
@require_http_methods(["GET"])
def course_list(request):
    query = request.GET.get("q", "").strip()
    offerings = CourseOffering.objects.select_related(
        "course", "instructor", "po_framework__program",
    ).annotate(
        enrollment_count=Count("enrollments"),
        active_count=Count("enrollments", filter=Q(enrollments__status="active")),
    ).order_by("-year", "term", "course__code", "section", "pk")
    if query:
        match = (
            Q(course__code__icontains=query) | Q(course__title__icontains=query)
            | Q(instructor__full_name__icontains=query)
            | Q(term__icontains=query) | Q(section__icontains=query)
        )
        if query.isdecimal() and len(query) <= 4:
            match |= Q(year=int(query))
        offerings = offerings.filter(match)
    return render(request, "core/course_list.html", {
        "offerings": offerings,
        "query": query,
    })


@staff_member_required
@require_http_methods(["GET"])
def offering_detail(request, offering_id):
    offering = get_object_or_404(
        CourseOffering.objects.select_related(
            "course", "instructor", "curriculum", "po_framework__program",
        ),
        pk=offering_id,
    )
    enrollments = offering.enrollments.select_related(
        "student__program",
    ).annotate(
        graded_total=Count("grades", filter=Q(grades__score__isnull=False)),
    ).order_by("student__full_name", "student__student_number", "pk")
    return render(request, "core/offering_detail.html", {
        "offering": offering,
        "enrollments": enrollments,
        "assessment_total": offering.assessments.count(),
    })
