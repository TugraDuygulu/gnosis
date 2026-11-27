"""Independent integrity tests for the CSV grade import (#44).

These tests treat ``core.grade_import`` (#42) and its pages (#43) as a black box:
every rejection is checked against unchanged grade, grade-history, receipt,
enrollment, assessment and offering rows, and accepted imports are compared with
the authoritative LO/PO calculators. Data is the fictional ``seed_pilot`` pilot.
"""
import json
from base64 import b64encode
from decimal import Decimal
from fractions import Fraction
from io import BytesIO, StringIO
from unittest.mock import patch

from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from core.access import COORDINATOR_GROUP
from core.grade_editor import revision_token, snapshot
from core.grade_history import history_key, record_grade_change
from core.grade_import import MAX_BYTES, MAX_ROWS, confirm_grades, preview_grades
from core.models import (
    Assessment, CourseOffering, Enrollment, Grade, GradeImportReceipt, Instructor, LearningOutcome,
    POFramework, ProgramOutcome, Student,
)
from core.services.lo_calculator import calculate_lo_achievement
from core.services.po_calculator import calculate_course_po_achievement
from core.services.student_po_calculator import calculate_student_po_achievement

HEADER = "student_number,assessment_id,score"


def outcome_snapshot():
    """Every calculated LO, course-PO and student-PO score, coverage and status.

    POs with no LO mapping or course contribution are left out: no grade can change them,
    and their constant no_data result is asserted in CalculatorAgreementTests.
    """
    rows = []
    for enrollment in Enrollment.objects.select_related("offering", "student").order_by("pk"):
        offering = enrollment.offering
        for lo in LearningOutcome.objects.filter(curriculum=offering.curriculum).order_by("pk"):
            r = calculate_lo_achievement(enrollment, lo)
            rows.append(("LO", enrollment.pk, lo.pk, r["score"], r["coverage"], r["status"]))
        for po in ProgramOutcome.objects.filter(
                framework=offering.po_framework,
                lo_mappings__learning_outcome__curriculum=offering.curriculum).distinct().order_by("pk"):
            r = calculate_course_po_achievement(enrollment, po)
            rows.append(("course PO", enrollment.pk, po.pk, r["score"], r["coverage"], r["status"]))
    for student in Student.objects.filter(enrollments__isnull=False).distinct().order_by("pk"):
        for po in ProgramOutcome.objects.filter(
                framework__program=student.program, course_contributions__isnull=False).distinct().order_by("pk"):
            r = calculate_student_po_achievement(student, po)
            rows.append(("student PO", student.pk, po.pk, r["score"], r["coverage"], r["status"]))
    return rows


def state():
    """Every row and calculated result a rejected import must leave untouched."""
    tables = (Grade, LogEntry, GradeImportReceipt, Enrollment, Assessment, CourseOffering, Student,
              Instructor, Group)
    User = get_user_model()
    # last_login is left out: signing in is not a data change made by an import.
    accounts = User.objects.order_by("pk").values_list(
        "pk", "username", "password", "is_active", "is_staff", "is_superuser")
    memberships = User.groups.through.objects.order_by("pk").values_list("user_id", "group_id")
    permissions = User.user_permissions.through.objects.order_by("pk").values_list("user_id", "permission_id")
    return ([list(model.objects.order_by("pk").values_list()) for model in tables]
            + [list(accounts), list(memberships), list(permissions), outcome_snapshot()])


def csv(*rows, header=HEADER, eol="\n", bom=False):
    text = header + eol + "".join(row + eol for row in rows)
    return text.encode("utf-8-sig" if bom else "utf-8")


class ImportIntegrityBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        users = get_user_model().objects
        cls.offering = CourseOffering.objects.get(course__code="PILOT321")      # "O": imported into
        cls.other_offering = CourseOffering.objects.get(course__code="PILOT311")
        cls.instructor = users.create_user("import-owner")
        cls.instructor_record = Instructor.objects.create(
            full_name="Import owner", email="owner@example.test", user=cls.instructor)
        CourseOffering.objects.filter(pk=cls.offering.pk).update(instructor=cls.instructor_record)
        cls.offering.refresh_from_db()
        cls.other_instructor = users.create_user("import-other")
        Instructor.objects.filter(pk=cls.other_offering.instructor_id).update(user=cls.other_instructor)
        cls.idle_instructor = users.create_user("import-idle")
        Instructor.objects.create(full_name="Idle", email="idle@example.test", user=cls.idle_instructor)
        cls.student = users.create_user("import-student")
        Student.objects.filter(student_number="PILOT001").update(user=cls.student)
        cls.coordinator = users.create_user("import-coordinator")
        cls.coordinator.groups.add(Group.objects.create(name=COORDINATOR_GROUP))
        cls.admin = users.create_superuser("import-admin")
        cls.legacy = users.create_user("import-legacy", is_staff=True)
        cls.legacy.user_permissions.add(Permission.objects.get(
            content_type__app_label="core", codename="change_grade"))
        # Enrolled only in the other offering: a real student number that is foreign to "O".
        outsider = Student.objects.create(
            full_name="Outsider", student_number="PILOT009",
            program=Student.objects.get(student_number="PILOT001").program)
        Enrollment.objects.create(student=outsider, offering=cls.other_offering)

        cls.mid, cls.lab = cls.offering.assessments.order_by("pk")[:2]
        cls.foreign_assessment = cls.other_offering.assessments.order_by("pk").first()
        cls.e1 = Enrollment.objects.get(offering=cls.offering, student__student_number="PILOT001")
        cls.e2 = Enrollment.objects.get(offering=cls.offering, student__student_number="PILOT002")

    # Seed grades in "O": PILOT001 Midterm 0 (recorded zero), Lab NULL; PILOT002 Midterm 80, Lab 40.

    def score(self, enrollment, assessment):
        return Grade.objects.filter(enrollment=enrollment, assessment=assessment).values_list(
            "score", flat=True).first()

    def preview(self, data, *, user=None, offering=None):
        return preview_grades(user=user or self.instructor, offering_id=(offering or self.offering).pk,
                              upload=BytesIO(data))

    def confirm(self, data, token, *, user=None, offering=None):
        return confirm_grades(user=user or self.instructor, offering_id=(offering or self.offering).pk,
                              upload=BytesIO(data), token=token)

    def history_count(self):
        return LogEntry.objects.filter(object_repr__startswith="Gnosis grade history").count()

    def assert_unchanged(self, before):
        self.assertEqual(state(), before, "a rejected import changed data")


class InputMatrixTests(ImportIntegrityBase):
    """Acceptance 1: every input class has an explicit outcome, and preview never writes."""

    def test_valid_inputs_and_their_actions(self):
        mid, lab = self.mid.pk, self.lab.pk
        cases = {
            "change an existing score": ([f"PILOT002,{mid},12.5"], [("set", Decimal("80"), Decimal("12.5"))]),
            "record zero over NULL": ([f"PILOT001,{lab},0"], [("set", None, Decimal("0"))]),
            "recorded zero equals zero": ([f"PILOT001,{mid},0"], [("keep", Decimal("0"), Decimal("0"))]),
            "blank keeps a score": ([f"PILOT002,{mid},"], [("keep", Decimal("80"), None)]),
            "blank keeps NULL": ([f"PILOT001,{lab},"], [("keep", None, None)]),
            "equal value is a no-op": ([f"PILOT002,{lab},40.00"], [("keep", Decimal("40"), Decimal("40"))]),
            "exact maximum": ([f"PILOT002,{lab},{self.lab.max_score}"],
                              [("set", Decimal("40"), self.lab.max_score)]),
            "two decimal places": ([f"PILOT002,{mid},7.25"], [("set", Decimal("80"), Decimal("7.25"))]),
            "one student, two assessments": ([f"PILOT002,{mid},1", f"PILOT002,{lab},2"],
                                             [("set", Decimal("80"), Decimal("1")),
                                              ("set", Decimal("40"), Decimal("2"))]),
        }
        for label, (rows, expected) in cases.items():
            for variant in ({}, {"eol": "\r\n", "bom": True}):
                with self.subTest(case=label, **variant):
                    before = state()
                    result = self.preview(csv(*rows, **variant))
                    self.assertEqual(result.errors, [])
                    self.assertIsNotNone(result.confirmation_token)
                    self.assertEqual([(r.action, r.previous, r.proposed) for r in result.rows], expected)
                    self.assert_unchanged(before)

    def test_invalid_inputs_block_the_whole_file(self):
        mid, lab, foreign = self.mid.pk, self.lab.pk, self.foreign_assessment.pk
        row_cases = {
            "duplicate row, same value": ([f"PILOT002,{mid},5", f"PILOT002,{mid},5"], ["duplicate"]),
            "duplicate row, other value": ([f"PILOT002,{mid},5", f"PILOT002,{mid},6"], ["duplicate"]),
            "extra column": ([f"PILOT002,{mid},5,x"], ["column_count"]),
            "missing column": ([f"PILOT002,{mid}"], ["column_count"]),
            "blank record": ([f"PILOT002,{mid},5", ""], ["column_count"]),
            "unknown student": ([f"NOBODY,{mid},5"], ["unknown_student"]),
            "student of another offering": ([f"PILOT009,{mid},5"], ["unknown_student"]),
            "student number differs in case": ([f"pilot002,{mid},5"], ["unknown_student"]),
            "assessment of another offering": ([f"PILOT002,{foreign},5"], ["unknown_assessment"]),
            "nonexistent assessment": ([f"PILOT002,999999,5"], ["unknown_assessment"]),
            "mixed offerings in one file": ([f"PILOT002,{mid},5", f"PILOT002,{foreign},5"],
                                            ["unknown_assessment"]),
            "zero id": (["PILOT002,0,5"], ["invalid_id"]),
            "leading-zero id": ([f"PILOT002,0{mid},5"], ["invalid_id"]),
            "negative id": ([f"PILOT002,-{mid},5"], ["invalid_id"]),
            "decimal id": ([f"PILOT002,{mid}.0,5"], ["invalid_id"]),
            "id above int64": ([f"PILOT002,{2**63},5"], ["invalid_id"]),
            "negative score": ([f"PILOT002,{mid},-1"], ["min_value"]),
            "above maximum": ([f"PILOT002,{lab},{self.lab.max_score + Decimal('0.01')}"], ["max_value"]),
            "three decimal places": ([f"PILOT002,{mid},1.005"], ["max_decimal_places"]),
        }
        for raw in ("NaN", "nan", "Infinity", "-inf", "sNaN", "1e1", "1,5", " 5", "5 ", "five", "0x10"):
            row_cases[f"score {raw!r}"] = ([f'PILOT002,{mid},"{raw}"'], ["invalid_decimal"])
        file_cases = {
            "duplicate column": (csv(f"PILOT002,{mid},5,5", header=HEADER + ",score"), "invalid_header"),
            "reordered header": (csv(f"{mid},PILOT002,5", header="assessment_id,student_number,score"),
                                 "invalid_header"),
            "semicolon export": (f"student_number;assessment_id;score\nPILOT002;{mid};5\n".encode(),
                                 "invalid_header"),
            "no data rows": (csv(), "empty"),
            "unclosed quote": (csv(f'"PILOT002,{mid},5'), "malformed_csv"),
            "not UTF-8": (csv(f"PILOT002,{mid},5").replace(b"PILOT", b"\xff\xfe"), "encoding"),
            "too many rows": (csv(*[f"S{i},{mid},1" for i in range(MAX_ROWS + 1)]), "too_many_rows"),
            "too large": (csv(f"PILOT002,{mid},5") + b"x" * MAX_BYTES, "too_large"),
        }
        for label, (rows, codes) in row_cases.items():
            # A valid row first proves one bad line blocks an otherwise valid file.
            data = csv(f"PILOT001,{lab},7", *rows)
            with self.subTest(case=label):
                before = state()
                result = self.preview(data)
                self.assertEqual([p.code for p in result.errors], codes)
                self.assertIsNone(result.confirmation_token)
                self.assert_unchanged(before)
        for label, (data, code) in file_cases.items():
            with self.subTest(case=label):
                before = state()
                result = self.preview(data)
                self.assertEqual([p.code for p in result.errors], [code])
                self.assertIsNone(result.confirmation_token)
                self.assert_unchanged(before)

    def test_row_limit_is_inclusive(self):
        rows = [f"PILOT002,{self.mid.pk},1"] + [f"S{i},{self.mid.pk},1" for i in range(MAX_ROWS - 1)]
        result = self.preview(csv(*rows))
        self.assertEqual({p.code for p in result.errors}, {"unknown_student"})  # parsed, not too_many_rows


class AuthorizationTests(ImportIntegrityBase):
    """Acceptance 2: only the assigned instructor can preview or confirm, by service or by page."""

    def setUp(self):
        self.data = csv(f"PILOT002,{self.mid.pk},11")
        self.token = self.preview(self.data).confirmation_token
        self.assertIsNotNone(self.token)

    def test_service_refuses_every_other_actor(self):
        others = {
            "anonymous": AnonymousUser(), "student": self.student, "coordinator": self.coordinator,
            "superuser": self.admin, "legacy staff with change_grade": self.legacy,
            "instructor of another offering": self.other_instructor, "instructor without offerings":
            self.idle_instructor,
        }
        for label, user in others.items():
            with self.subTest(actor=label):
                before = state()
                with self.assertRaises(PermissionDenied):
                    self.preview(self.data, user=user)
                with self.assertRaises(PermissionDenied):
                    self.confirm(self.data, self.token, user=user)
                self.assert_unchanged(before)

    def test_access_lost_after_preview(self):
        changes = {
            "deactivated": lambda: get_user_model().objects.filter(pk=self.instructor.pk).update(is_active=False),
            "reassigned": lambda: CourseOffering.objects.filter(pk=self.offering.pk).update(
                instructor=Instructor.objects.get(user=self.idle_instructor)),
            "became a student too": lambda: Student.objects.filter(student_number="PILOT002").update(
                user=self.instructor),
        }
        for label, change in changes.items():
            with self.subTest(change=label), transaction.atomic():
                at_preview = state()
                change()
                before = state()
                self.assertNotEqual(before, at_preview, "the access change must be in the baseline")
                with self.assertRaises(PermissionDenied):
                    self.confirm(self.data, self.token)
                self.assert_unchanged(before)
                transaction.set_rollback(True)

    def test_new_instructor_cannot_use_the_old_instructors_preview(self):
        CourseOffering.objects.filter(pk=self.offering.pk).update(
            instructor=Instructor.objects.get(user=self.idle_instructor))
        before = state()
        with self.assertRaises(ValidationError) as caught:
            self.confirm(self.data, self.token, user=self.idle_instructor)
        self.assertEqual(caught.exception.code, "invalid_token")
        self.assert_unchanged(before)

    def test_tampered_token_file_and_offering(self):
        # The owner also teaches the other offering here, so only the token binding can refuse it.
        CourseOffering.objects.filter(pk=self.other_offering.pk).update(instructor=self.instructor_record)
        other_file = csv(f"PILOT002,{self.mid.pk},12")
        cases = {
            "token for another offering": (self.data, self.token, self.other_offering),
            "different file bytes": (other_file, self.token, None),
            "same rows, different line endings": (csv(f"PILOT002,{self.mid.pk},11", eol="\r\n"),
                                                  self.token, None),
            "truncated token": (self.data, self.token[:-4], None),
            "edited token payload": (self.data, "x" + self.token[1:], None),
            "token of another file": (self.data, self.preview(other_file).confirmation_token, None),
            "not a string": (self.data, None, None),
        }
        for label, (data, token, offering) in cases.items():
            with self.subTest(case=label):
                before = state()
                with self.assertRaises(ValidationError) as caught:
                    self.confirm(data, token, offering=offering)
                self.assertEqual(caught.exception.code, "invalid_token")
                self.assert_unchanged(before)

    def confirm_form(self, data=None, token=None):
        return {"token": token or self.token, "content": b64encode(data or self.data).decode(),
                "filename": "grades.csv"}

    def test_pages_refuse_other_actors_and_foreign_offerings(self):
        url = reverse("offering_grade_import", args=[self.offering.pk])
        other_url = reverse("offering_grade_import", args=[self.other_offering.pk])
        upload = {"file": BytesIO(self.data)}
        cases = [
            ("anonymous", None, url, 302), ("student", self.student, url, 403),
            ("coordinator", self.coordinator, url, 403), ("superuser", self.admin, url, 403),
            ("legacy staff", self.legacy, url, 403),
            ("instructor of another offering", self.other_instructor, url, 404),
            ("owner on an offering they do not teach", self.instructor, other_url, 404),
        ]
        for label, user, target, status in cases:
            with self.subTest(actor=label):
                self.client.logout()
                if user:
                    self.client.force_login(user)
                before = state()
                self.assertEqual(self.client.post(target, self.confirm_form()).status_code, status)
                upload["file"].seek(0)
                self.assertEqual(self.client.post(target, upload).status_code, status)
                self.assert_unchanged(before)

    def test_pages_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.instructor)
        url = reverse("offering_grade_import", args=[self.offering.pk])
        before = state()
        self.assertEqual(client.post(url, self.confirm_form()).status_code, 403)
        self.assertEqual(client.post(url, {"file": BytesIO(self.data)}).status_code, 403)
        self.assert_unchanged(before)

    def test_page_rejects_tampered_confirmation(self):
        self.client.force_login(self.instructor)
        url = reverse("offering_grade_import", args=[self.offering.pk])
        for label, form in {
            "other file": self.confirm_form(data=csv(f"PILOT002,{self.mid.pk},99")),
            "bad token": self.confirm_form(token="nope"),
            "bad base64": {**self.confirm_form(), "content": "%%%"},
            "oversized content": {**self.confirm_form(), "content": "A" * (MAX_BYTES * 2)},
        }.items():
            with self.subTest(case=label):
                before = state()
                response = self.client.post(url, form)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Nothing was saved")
                self.assert_unchanged(before)


class StaleAndReplayTests(ImportIntegrityBase):
    """Acceptance 3: a change between preview and confirm, or a reused preview, writes nothing."""

    def setUp(self):
        self.data = csv(f"PILOT002,{self.mid.pk},11", f"PILOT001,{self.lab.pk},3")
        self.token = self.preview(self.data).confirmation_token

    def native_save(self, enrollment, scores, user=None):
        """Change grades through the native grade editor page (audited, independent path)."""
        user = user or self.instructor
        assessments, grades, revision = snapshot(enrollment)
        form = {"revision": revision_token(enrollment, user, revision)}
        for assessment in assessments:
            grade = grades.get(assessment.pk)
            value = scores.get(assessment.pk, grade.score if grade else None)
            form[f"score_{assessment.pk}"] = "" if value is None else str(value)
        self.client.force_login(user)
        response = self.client.post(reverse("enrollment_grade_editor", args=[enrollment.pk]), form)
        self.assertEqual(response.status_code, 302)

    def test_changes_between_preview_and_confirm_are_stale(self):
        changes = {
            "score edited directly": lambda: Grade.objects.filter(
                enrollment=self.e2, assessment=self.mid).update(score=Decimal("81")),
            "score edited in the grade editor": lambda: self.native_save(self.e2, {self.mid.pk: Decimal("81")}),
            "score edited and restored": lambda: (self.native_save(self.e2, {self.mid.pk: Decimal("81")}),
                                                  self.native_save(self.e2, {self.mid.pk: Decimal("80")})),
            "NULL grade filled": lambda: Grade.objects.filter(
                enrollment=self.e1, assessment=self.lab).update(score=Decimal("1")),
            "maximum lowered": lambda: Assessment.objects.filter(pk=self.lab.pk).update(max_score=Decimal("2")),
            "weight changed": lambda: Assessment.objects.filter(pk=self.mid.pk).update(
                course_grade_weight=Decimal("1")),
            "assessment renamed": lambda: Assessment.objects.filter(pk=self.mid.pk).update(name="Renamed"),
            "enrollment withdrawn": lambda: Enrollment.objects.filter(pk=self.e2.pk).update(status="withdrawn"),
            "student renumbered": lambda: Student.objects.filter(student_number="PILOT002").update(
                student_number="PILOT002X"),
            "offering section changed": lambda: CourseOffering.objects.filter(pk=self.offering.pk).update(
                section="OTHER"),
        }
        for label, change in changes.items():
            with self.subTest(change=label), transaction.atomic():
                at_preview = state()
                change()
                # Baseline after the legitimate edit, immediately before confirming.
                before = state()
                self.assertNotEqual(before, at_preview, "the intervening edit must be in the baseline")
                with self.assertRaises(ValidationError) as caught:
                    self.confirm(self.data, self.token)
                self.assertEqual(caught.exception.code, "stale")
                self.assert_unchanged(before)  # the newer edit survives; nothing else changes
                transaction.set_rollback(True)

    def test_unrelated_changes_do_not_block_confirmation(self):
        other = Enrollment.objects.get(offering=self.other_offering, student__student_number="PILOT002")
        self.native_save(other, {self.foreign_assessment.pk: Decimal("1")}, user=self.other_instructor)
        self.assertEqual(self.confirm(self.data, self.token), 2)

    def test_replay_writes_once(self):
        history = self.history_count()
        self.assertEqual(self.confirm(self.data, self.token), 2)
        after_first = state()
        self.assertEqual(self.history_count(), history + 2)
        with self.assertRaises(ValidationError) as caught:
            self.confirm(self.data, self.token)
        self.assertEqual(caught.exception.code, "replayed")
        self.assertEqual(state(), after_first)

    def test_second_preview_of_the_same_file_cannot_apply_twice(self):
        second = self.preview(self.data).confirmation_token
        self.assertEqual(self.confirm(self.data, self.token), 2)
        after_first = state()
        with self.assertRaises(ValidationError) as caught:
            self.confirm(self.data, second)
        self.assertEqual(caught.exception.code, "stale")
        self.assertEqual(state(), after_first)

    def test_all_unchanged_preview_is_single_use_and_writes_no_history(self):
        data = csv(f"PILOT001,{self.mid.pk},0", f"PILOT002,{self.lab.pk},", f"PILOT002,{self.mid.pk},80")
        token = self.preview(data).confirmation_token
        before = state()
        self.assertEqual(self.confirm(data, token), 0)
        after = state()
        self.assertEqual(after[:2], before[:2], "a no-op import changed grades or history")
        self.assertEqual(len(after[2]), len(before[2]) + 1)  # only the receipt
        with self.assertRaises(ValidationError) as caught:
            self.confirm(data, token)
        self.assertEqual(caught.exception.code, "replayed")
        self.assertEqual(state(), after)

    def test_page_replay_reports_and_changes_nothing(self):
        self.client.force_login(self.instructor)
        url = reverse("offering_grade_import", args=[self.offering.pk])
        form = {"token": self.token, "content": b64encode(self.data).decode(), "filename": "g.csv"}
        self.assertRedirects(self.client.post(url, form), reverse("offering_gradebook", args=[self.offering.pk]))
        after_first = state()
        response = self.client.post(url, form)
        self.assertContains(response, "already confirmed")
        self.assertEqual(state(), after_first)


class RollbackTests(ImportIntegrityBase):
    """Acceptance 4: a failure after earlier writes rolls back every grade, event and the receipt."""

    def setUp(self):
        # Three real changes, written in order, so a failure can follow earlier writes.
        self.data = csv(f"PILOT002,{self.mid.pk},11", f"PILOT002,{self.lab.pk},12", f"PILOT001,{self.lab.pk},13")
        self.token = self.preview(self.data).confirmation_token

    def failing_on(self, call_number, error):
        calls = {"n": 0}

        def wrapper(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == call_number:
                raise error
            return record_grade_change(*args, **kwargs)
        return patch("core.grade_editor.record_grade_change", side_effect=wrapper)

    def test_failure_after_earlier_writes_rolls_everything_back(self):
        for call_number in (1, 2, 3):
            with self.subTest(failing_event=call_number):
                before = state()
                with self.failing_on(call_number, RuntimeError("audit store down")):
                    with self.assertRaises(RuntimeError):
                        self.confirm(self.data, self.token)
                self.assert_unchanged(before)

    def test_rolled_back_preview_can_still_be_confirmed_once(self):
        with self.failing_on(2, RuntimeError("audit store down")):
            with self.assertRaises(RuntimeError):
                self.confirm(self.data, self.token)
        history = self.history_count()
        self.assertEqual(self.confirm(self.data, self.token), 3)
        self.assertEqual(self.history_count(), history + 3)

    def test_page_reports_a_failed_write_and_saves_nothing(self):
        self.client.force_login(self.instructor)
        url = reverse("offering_grade_import", args=[self.offering.pk])
        before = state()
        with self.failing_on(2, IntegrityError("constraint")):
            response = self.client.post(url, {"token": self.token, "content": b64encode(self.data).decode(),
                                              "filename": "g.csv"})
        self.assertContains(response, "Nothing was saved")
        self.assert_unchanged(before)

    def test_only_changed_cells_are_audited(self):
        # Fixture: PILOT001 Midterm 0, Lab NULL row; PILOT002 Midterm 80, Lab 40 (row removed here).
        Grade.objects.filter(enrollment=self.e2, assessment=self.lab).delete()
        data = csv(f"PILOT002,{self.mid.pk},11",      # change 80 -> 11
                   f"PILOT001,{self.lab.pk},5",       # change NULL -> 5 on an existing row
                   f"PILOT002,{self.lab.pk},7",       # create a missing grade
                   f"PILOT001,{self.mid.pk},0")       # equal recorded zero: no audit
        token = self.preview(data).confirmation_token
        before = set(LogEntry.objects.values_list("pk", flat=True))
        self.assertEqual(self.confirm(data, token), 3)
        expected = {
            (self.e2.pk, self.mid.pk): ("change", CHANGE, Decimal("80"), Decimal("11")),
            (self.e1.pk, self.lab.pk): ("change", CHANGE, None, Decimal("5")),
            (self.e2.pk, self.lab.pk): ("create", ADDITION, None, Decimal("7")),
        }
        grade_type = ContentType.objects.get_for_model(Grade)
        audited = {}
        for entry in LogEntry.objects.exclude(pk__in=before).order_by("pk"):
            event = json.loads(entry.change_message)[1]["gnosis_grade_change"]
            after = event["after"]
            cell = (after["enrollment_id"], after["assessment_id"])
            self.assertNotIn(cell, audited, "a cell was audited twice")
            audited[cell] = (entry, event)
        self.assertEqual(set(audited), set(expected))
        for cell, (operation, flag, old, new) in expected.items():
            entry, event = audited[cell]
            grade = Grade.objects.get(enrollment_id=cell[0], assessment_id=cell[1])
            with self.subTest(cell=cell):
                self.assertEqual(entry.content_type_id, grade_type.pk)
                self.assertEqual(entry.object_id, str(grade.pk))
                self.assertEqual(entry.object_repr, history_key(cell[0]))
                self.assertEqual(entry.action_flag, flag)
                self.assertEqual(entry.user_id, self.instructor.pk)
                self.assertEqual(event["operation"], operation)
                self.assertEqual(event["source"], "CSV import")
                self.assertEqual((event["after"]["enrollment_id"], event["after"]["assessment_id"]), cell)
                self.assertEqual(Decimal(event["after"]["score"]), new)
                self.assertEqual(grade.score, new)
                if operation == "create":
                    self.assertIsNone(event["before"])
                else:
                    self.assertEqual((event["before"]["enrollment_id"], event["before"]["assessment_id"]), cell)
                    self.assertEqual(event["before"]["score"], None if old is None else str(old.quantize(Decimal("0.01"))))


class CalculatorAgreementTests(ImportIntegrityBase):
    """Acceptance 5: outcome results match hand-derived fixture values, before and after an import.

    Seed weights. PILOT311: LO1 <- Midterm/100 (60) + Project/50 (40); LO2 <- Midterm (40) + Project (100);
    PO2 <- LO1 (2) + LO2 (1); PO3 <- LO2 (5). PILOT321: LO1 <- Midterm/100 (100); LO2 <- Lab/50 (100);
    PO2 <- LO1 (2) + LO2 (1); PO4 <- LO1 (5); PO5 <- LO2 (5). Course contributions: PO2 = 5 (311) + 3 (321);
    PO3 = 5 (311); PO4 = 4 (321); PO5 = 4 (321). Expected values are exact fractions.
    """

    TOLERANCE = Fraction(1, 10**18)

    def assert_outcome(self, result, score, coverage, status, label):
        with self.subTest(outcome=label):
            self.assertEqual(result["status"], status)
            if score is None:
                self.assertIsNone(result["score"])
            else:
                self.assertLess(abs(Fraction(result["score"]) - score), self.TOLERANCE, result["score"])
            self.assertLess(abs(Fraction(result["coverage"]) - coverage), self.TOLERANCE, result["coverage"])

    def by_code(self, model, code, **filters):
        return model.objects.get(code=code, **filters)

    def check(self, expected):
        for (kind, who, code), (score, coverage, status) in expected.items():
            if kind == "LO":
                result = calculate_lo_achievement(
                    who, self.by_code(LearningOutcome, code, curriculum=who.offering.curriculum))
            elif kind == "course PO":
                result = calculate_course_po_achievement(who, self.by_code(ProgramOutcome, code))
            else:
                result = calculate_student_po_achievement(who, self.by_code(ProgramOutcome, code))
            self.assert_outcome(result, score, coverage, status, f"{kind} {code} {who}")

    def test_fixture_outcomes_before_import(self):
        F = Fraction
        p1 = Student.objects.get(student_number="PILOT001")
        self.check({
            # PILOT001 in PILOT321: Midterm is a recorded zero, Lab is a NULL (missing) score.
            ("LO", self.e1, "LO1"): (F(0), F(100), "complete"),
            ("LO", self.e1, "LO2"): (None, F(0), "no_data"),
            ("course PO", self.e1, "PO2"): (F(0), F(200, 3), "provisional"),
            ("course PO", self.e1, "PO4"): (F(0), F(100), "complete"),
            ("course PO", self.e1, "PO5"): (None, F(0), "no_data"),
            ("course PO", self.e1, "PO1"): (None, F(0), "no_data"),      # unmapped PO
            # PILOT002 in PILOT321: Midterm 80/100, Lab 40/50.
            ("LO", self.e2, "LO1"): (F(80), F(100), "complete"),
            ("LO", self.e2, "LO2"): (F(80), F(100), "complete"),
            ("course PO", self.e2, "PO2"): (F(80), F(100), "complete"),
            # PILOT001 across both courses; PILOT311 PO2 = 1784/21 (Midterm 90, Project 40/50).
            ("student PO", p1, "PO2"): (F(8920, 147), F(175, 2), "provisional"),
            ("student PO", p1, "PO3"): (F(580, 7), F(100), "complete"),
            ("student PO", p1, "PO4"): (F(0), F(100), "complete"),
            ("student PO", p1, "PO5"): (None, F(0), "no_data"),
        })

    def test_imported_scores_give_hand_derived_outcomes(self):
        F = Fraction
        p1 = Student.objects.get(student_number="PILOT001")
        p2 = Student.objects.get(student_number="PILOT002")
        data = csv(f"PILOT001,{self.lab.pk},0",     # NULL -> recorded zero
                   f"PILOT001,{self.mid.pk},",      # blank keeps the recorded zero
                   f"PILOT002,{self.mid.pk},",      # blank keeps 80
                   f"PILOT002,{self.lab.pk},25")    # 40 -> 25 of 50
        self.assertEqual(self.confirm(data, self.preview(data).confirmation_token), 2)
        self.check({
            ("LO", self.e1, "LO1"): (F(0), F(100), "complete"),
            ("LO", self.e1, "LO2"): (F(0), F(100), "complete"),
            ("course PO", self.e1, "PO2"): (F(0), F(100), "complete"),
            ("course PO", self.e1, "PO5"): (F(0), F(100), "complete"),
            ("LO", self.e2, "LO1"): (F(80), F(100), "complete"),
            ("LO", self.e2, "LO2"): (F(50), F(100), "complete"),
            ("course PO", self.e2, "PO2"): (F(70), F(100), "complete"),
            ("course PO", self.e2, "PO4"): (F(80), F(100), "complete"),
            ("course PO", self.e2, "PO5"): (F(50), F(100), "complete"),
            ("student PO", p1, "PO2"): (F(1115, 21), F(100), "complete"),
            ("student PO", p1, "PO5"): (F(0), F(100), "complete"),
            # PILOT002's PILOT311 Project is missing, so its PO2 there is 70 at 1040/21 % coverage.
            ("student PO", p2, "PO2"): (F(70), F(2875, 42), "provisional"),
            ("student PO", p2, "PO5"): (F(50), F(100), "complete"),
        })

    def test_imported_scores_match_direct_storage(self):
        scores = {(self.e1, self.mid): Decimal("55.5"), (self.e1, self.lab): Decimal("0"),
                  (self.e2, self.mid): Decimal("0"), (self.e2, self.lab): self.lab.max_score}
        baseline = outcome_snapshot()
        with transaction.atomic():
            for (enrollment, assessment), value in scores.items():
                Grade.objects.update_or_create(enrollment=enrollment, assessment=assessment,
                                               defaults={"score": value})
            expected = outcome_snapshot()
            transaction.set_rollback(True)
        self.assertEqual(outcome_snapshot(), baseline)
        changed = {(kind, who, po) for kind, who, po, *_ in expected} & {
            (row[0], row[1], row[2]) for row, old in zip(expected, baseline) if row != old}
        self.assertTrue(any(kind == "course PO" for kind, *_ in changed), "a course PO must change")
        self.assertTrue(any(kind == "student PO" for kind, *_ in changed), "a student PO must change")

        data = csv(*[f"{e.student.student_number},{a.pk},{v}" for (e, a), v in scores.items()])
        self.assertEqual(self.confirm(data, self.preview(data).confirmation_token), 4)
        for (enrollment, assessment), value in scores.items():
            self.assertEqual(self.score(enrollment, assessment), value)
        self.assertEqual(outcome_snapshot(), expected)

    def test_only_a_foreign_framework_outcome_raises(self):
        framework = POFramework.objects.create(program=self.offering.po_framework.program, version_number=2)
        foreign = ProgramOutcome.objects.create(framework=framework, code="PO1", description="Other version")
        with self.assertRaises(ValueError):
            calculate_course_po_achievement(self.e1, foreign)
        outcome_snapshot()  # every in-fixture calculation completes without an exception
