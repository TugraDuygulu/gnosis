from unittest.mock import patch

from decimal import Decimal
from io import BytesIO, StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from core.grade_import import MAX_BYTES, confirm_grades, preview_grades
from core.grade_history import history_entries, history_row, record_grade_change
from core.models import Assessment, Enrollment, Grade, GradeImportReceipt


class PreviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        e = Enrollment.objects.get(student__student_number="PILOT001",
                                   offering__course__code="PILOT321")
        cls.offering = e.offering
        cls.user = get_user_model().objects.create_user("preview-instructor")
        instructor = cls.offering.instructor
        instructor.user = cls.user
        instructor.save()
        e.student.student_number = "0007"
        e.student.save()
        cls.a, cls.b = cls.offering.assessments.order_by("pk")[:2]
        Grade.objects.update_or_create(enrollment=e, assessment=cls.a,
                                       defaults={"score": Decimal("10.00")})

    def preview(self, data):
        with CaptureQueriesContext(connection) as captured:
            result = preview_grades(user=self.user, offering_id=self.offering.pk,
                                    upload=BytesIO(data))
        self.assertTrue(all(q["sql"].lstrip().startswith("SELECT") for q in captured))
        return result

    def csv(self, *rows):
        return self.preview(("student_number,assessment_id,score\r\n" +
                             "\r\n".join(rows)).encode("utf-8-sig"))

    def test_zero_blank_and_equal(self):
        for raw, value, action in [("0", Decimal(0), "set"), ("", None, "keep"),
                                   ("10.00", Decimal(10), "keep")]:
            with self.subTest(raw=raw):
                result = self.csv(f'"0007",{self.a.pk},{raw}')
                self.assertEqual(result.errors, [])
                row, = result.rows
                self.assertEqual((row.student_number, row.previous, row.proposed, row.action),
                                 ("0007", Decimal(10), value, action))

    def test_invalid_rows_keep_source_lines(self):
        foreign = Assessment.objects.exclude(offering=self.offering).first()
        result = self.csv(f"0007,{self.a.pk},4", f"0007,{self.a.pk},5",
                          f"7,{self.b.pk},0", f"0007,{foreign.pk},0", "wrong,width")
        self.assertEqual([(p.line, p.code) for p in result.errors],
                         [(3, "duplicate"), (4, "unknown_student"),
                          (5, "unknown_assessment"), (6, "column_count")])
        self.assertEqual(len(result.rows), 1)

    def test_score_and_format_errors(self):
        for score in ["NaN", "Infinity", "1e2", "1.001", "-1", "999999", " "]:
            with self.subTest(score=score):
                self.assertEqual(self.csv(f"0007,{self.a.pk},{score}").errors[0].field,
                                 "score")
        self.assertEqual(self.csv('"unterminated').errors[0].code, "malformed_csv")
        self.assertEqual(self.preview(b'bad,header').errors[0].code, "invalid_header")
        self.assertEqual(self.csv().errors[0].code, "empty")

    def test_boundaries(self):
        rows = [f"fictional{i},{self.a.pk},0" for i in range(100)]
        self.assertEqual([p.code for p in self.csv(*rows).errors], ["unknown_student"] * 100)
        self.assertEqual(self.csv(*rows, rows[0]).errors[0].code, "too_many_rows")
        self.assertEqual(self.preview(b'\xff' * MAX_BYTES).errors[0].code, "encoding")
        self.assertEqual(self.preview(b'x' * (MAX_BYTES + 1)).errors[0].code, "too_large")

    def test_denied_before_read(self):
        with self.assertRaises(PermissionDenied):
            preview_grades(user=self.user, offering_id=-1, upload=None)
        with self.assertRaises(PermissionDenied):
            preview_grades(user=get_user_model().objects.create_user("outsider"),
                           offering_id=self.offering.pk, upload=None)

    def file_for(self, *rows):
        return ("student_number,assessment_id,score\n" + "\n".join(rows)).encode()

    def confirm(self, data, token):
        return confirm_grades(user=self.user, offering_id=self.offering.pk,
                              upload=BytesIO(data), token=token)

    def rejected(self, data, token, code):
        with self.assertRaises(ValidationError) as caught:
            self.confirm(data, token)
        self.assertEqual(caught.exception.code, code)

    def test_confirm_changes_history_and_noops(self):
        e = Enrollment.objects.get(offering=self.offering, student__student_number="0007")
        another = Enrollment.objects.filter(offering=self.offering).exclude(pk=e.pk).first()
        Grade.objects.filter(enrollment=e, assessment=self.b).delete()
        Grade.objects.filter(enrollment=another, assessment=self.a).delete()
        equal, _ = Grade.objects.update_or_create(enrollment=another, assessment=self.b,
                                                  defaults={"score": Decimal("5")})
        n = another.student.student_number
        data = self.file_for(f"0007,{self.a.pk},2.50", f"0007,{self.b.pk},0",
                             f"{n},{self.a.pk},", f"{n},{self.b.pk},5")
        token = self.preview(data).confirmation_token
        self.assertEqual(self.confirm(data, token), 2)
        updated = Grade.objects.get(enrollment=e, assessment=self.a)
        zero = Grade.objects.get(enrollment=e, assessment=self.b)
        self.assertEqual((updated.score, zero.score), (Decimal("2.50"), Decimal("0")))
        self.assertFalse(Grade.objects.filter(enrollment=another, assessment=self.a).exists())
        equal.refresh_from_db()
        self.assertEqual(equal.score, Decimal(5))
        events = list(history_entries(e.pk).filter(user=self.user))
        self.assertEqual([entry.object_id for entry in events], [str(zero.pk), str(updated.pk)])
        for entry, old, new, operation in zip(events, [None, Decimal(10)],
                                               [Decimal(0), Decimal("2.50")], ["create", "change"]):
            row = history_row(entry)
            self.assertEqual((row["source"], row["operation"]), ("CSV import", operation))
            self.assertEqual(Decimal(row["new"]), new)
            self.assertEqual(None if row["old"] is None else Decimal(row["old"]), old)
        self.assertFalse(history_entries(another.pk).filter(user=self.user).exists())
        self.rejected(data, token, "replayed")

    def test_noop_preview_is_single_use(self):
        data = self.file_for(f"0007,{self.a.pk},10")
        token = self.preview(data).confirmation_token
        self.assertEqual(self.confirm(data, token), 0)
        self.rejected(data, token, "replayed")
        self.assertEqual(GradeImportReceipt.objects.count(), 1)

    def test_newer_grade_survives_rejection(self):
        data = self.file_for(f"0007,{self.a.pk},5")
        token = self.preview(data).confirmation_token
        grade = Grade.objects.get(enrollment__student__student_number="0007", assessment=self.a)
        grade.score = Decimal("7")
        grade.save()
        self.rejected(data, token, "stale")
        grade.refresh_from_db()
        self.assertEqual(grade.score, Decimal("7"))
        self.assertFalse(GradeImportReceipt.objects.exists())

    def test_assessment_and_enrollment_configuration(self):
        data = self.file_for(f"0007,{self.a.pk},5")
        token = self.preview(data).confirmation_token
        Assessment.objects.filter(pk=self.a.pk).update(max_score=60)
        self.rejected(data, token, "stale")
        token = self.preview(data).confirmation_token
        Enrollment.objects.filter(offering=self.offering).update(status="withdrawn")
        self.rejected(data, token, "stale")

    def test_confirmation_checks_file_signature_and_age(self):
        data = self.file_for(f"0007,{self.a.pk},5")
        with patch("django.core.signing.time.time", return_value=100):
            token = self.preview(data).confirmation_token
        self.rejected(data, token, "expired")
        token = self.preview(data).confirmation_token
        self.rejected(data, token + "x", "invalid_token")
        self.rejected(data + b"0", token, "invalid_token")
        self.assertIsNone(self.csv("invalid").confirmation_token)

    def test_recheck_permission_from_database(self):
        data = self.file_for(f"0007,{self.a.pk},5")
        token = self.preview(data).confirmation_token
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.confirm(data, token)
        self.assertFalse(GradeImportReceipt.objects.exists())

    def test_later_audit_failure_rolls_back_grades_events_and_nonce(self):
        data = self.file_for(f"0007,{self.a.pk},1", f"0007,{self.b.pk},2")
        token = self.preview(data).confirmation_token
        before = list(Grade.objects.order_by("pk").values())
        calls = []

        def fail_second(*args, **kwargs):
            calls.append(record_grade_change(*args, **kwargs))
            if len(calls) == 2:
                raise RuntimeError("injected audit failure")

        with patch("core.grade_editor.record_grade_change", side_effect=fail_second):
            with self.assertRaisesMessage(RuntimeError, "injected audit failure"):
                self.confirm(data, token)
        self.assertEqual(list(Grade.objects.order_by("pk").values()), before)
        self.assertFalse(type(calls[0]).objects.filter(pk__in=[e.pk for e in calls]).exists())
        self.assertFalse(GradeImportReceipt.objects.exists())
        self.assertEqual(self.confirm(data, token), 2)

    def test_audited_change_then_restore_invalidates_old_preview(self):
        original = self.file_for(f"0007,{self.a.pk},4")
        token = self.preview(original).confirmation_token
        for value in [7, 10]:
            data = self.file_for(f"0007,{self.a.pk},{value}")
            self.confirm(data, self.preview(data).confirmation_token)
        self.rejected(original, token, "stale")

    def test_assignment_revoked_after_preview(self):
        data = self.file_for(f"0007,{self.a.pk},5")
        token = self.preview(data).confirmation_token
        self.offering.instructor.user = None
        self.offering.instructor.save(update_fields=["user"])
        with self.assertRaises(PermissionDenied):
            self.confirm(data, token)
        self.assertFalse(GradeImportReceipt.objects.exists())

    def test_missing_and_null_grade_have_distinct_revisions(self):
        enrollment = Enrollment.objects.get(offering=self.offering, student__student_number="0007")
        target = Grade.objects.filter(enrollment=enrollment, assessment=self.b)
        target.delete()
        data = self.file_for(f"0007,{self.b.pk},")
        token = self.preview(data).confirmation_token
        null_grade = Grade.objects.create(enrollment=enrollment, assessment=self.b, score=None)
        self.rejected(data, token, "stale")
        null_grade.refresh_from_db()
        self.assertIsNone(null_grade.score)

    def test_token_scoped_to_actor_and_offering(self):
        data = self.file_for(f"0007,{self.a.pk},0")
        token = self.preview(data).confirmation_token
        other = Assessment.objects.exclude(offering=self.offering).first().offering
        other.instructor = self.offering.instructor
        other.save()
        with self.assertRaises(ValidationError) as caught:
            confirm_grades(user=self.user, offering_id=other.pk, upload=BytesIO(data), token=token)
        self.assertEqual(caught.exception.code, "invalid_token")
        replacement = get_user_model().objects.create_user("replacement")
        self.offering.instructor.user = replacement
        self.offering.instructor.save(update_fields=["user"])
        with self.assertRaises(ValidationError) as caught:
            confirm_grades(user=replacement, offering_id=self.offering.pk,
                           upload=BytesIO(data), token=token)
        self.assertEqual(caught.exception.code, "invalid_token")
        self.assertFalse(GradeImportReceipt.objects.exists())
