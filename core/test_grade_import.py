from decimal import Decimal
from io import BytesIO, StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from core.grade_import import MAX_BYTES, preview_grades
from core.models import Assessment, Enrollment, Grade


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
