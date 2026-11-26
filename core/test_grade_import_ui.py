"""Grade CSV import pages (#43): entry point, preview, confirmation and recovery."""

from base64 import b64decode, b64encode
from decimal import Decimal
from io import StringIO

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.grade_history import history_entries, history_row
from core.models import Assessment, Enrollment, Grade, GradeImportReceipt, Instructor
from core.test_page_usability import parse


class GradeImportPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.enrollment = Enrollment.objects.get(student__student_number="PILOT001",
                                                offering__course__code="PILOT321")
        cls.offering = cls.enrollment.offering
        cls.other = Enrollment.objects.get(student__student_number="PILOT002", offering=cls.offering)
        cls.user = get_user_model().objects.create_user("import-instructor")
        Instructor.objects.filter(pk=cls.offering.instructor_id).update(user=cls.user)
        student = cls.enrollment.student
        student.student_number = "0007"  # leading zeros must survive the round trip
        student.save()
        cls.a, cls.b = cls.offering.assessments.order_by("pk")[:2]
        # 0007: a real score and a missing one. The other student: a recorded zero and a score.
        Grade.objects.update_or_create(enrollment=cls.enrollment, assessment=cls.a,
                                       defaults={"score": Decimal("10")})
        Grade.objects.filter(enrollment=cls.enrollment, assessment=cls.b).delete()
        Grade.objects.update_or_create(enrollment=cls.other, assessment=cls.a, defaults={"score": Decimal("0")})
        Grade.objects.update_or_create(enrollment=cls.other, assessment=cls.b, defaults={"score": Decimal("40")})
        cls.n = cls.other.student.student_number
        cls.url = reverse("offering_grade_import", args=[cls.offering.pk])
        cls.gradebook = reverse("offering_gradebook", args=[cls.offering.pk])

    def setUp(self):
        self.client.force_login(self.user)

    @staticmethod
    def csv(*rows):
        return ("student_number,assessment_id,score\r\n" + "\r\n".join(rows)).encode()

    def upload(self, *rows, name="grades.csv"):
        return self.client.post(self.url, {"file": SimpleUploadedFile(name, self.csv(*rows), "text/csv")})

    def confirm(self, response, follow=False, **changes):
        result = response.context["result"]
        data = {"token": result["token"], "content": result["content"], "filename": result["filename"]}
        return self.client.post(self.url, {**data, **changes}, follow=follow)

    def state(self):
        return (list(Grade.objects.order_by("pk").values_list()), LogEntry.objects.count(),
                GradeImportReceipt.objects.count())

    def mixed(self):
        """One change, one new zero, one blank and one equal score."""
        return (f"0007,{self.a.pk},12.5", f"0007,{self.b.pk},0", f"{self.n},{self.a.pk},", f"{self.n},{self.b.pk},40")

    def test_gradebook_links_only_the_instructor_to_import(self):
        self.assertContains(self.client.get(self.gradebook), f'href="{self.url}"')
        self.client.force_login(get_user_model().objects.create_superuser("import-admin"))
        self.assertNotContains(self.client.get(self.gradebook), self.url)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_upload_page_shows_ids_limits_and_a_template_that_changes_nothing(self):
        response = self.client.get(self.url)
        page = parse(response)
        self.assertEqual((page.h1_count, page.unlabelled_controls()), (1, []))
        for text in ("student_number,assessment_id,score", "100 rows and 1 MB", f"<b>{self.a.pk}</b>",
                     'enctype="multipart/form-data"', "records a real zero"):
            self.assertContains(response, text)

        template = self.client.get(reverse("offering_grade_import_template", args=[self.offering.pk]),
                                   {"assessment": self.a.pk})
        self.assertEqual(template["Content-Type"], "text/csv; charset=utf-8")
        lines = template.content.decode("utf-8-sig").splitlines()
        self.assertEqual(lines, ["student_number,assessment_id,score", f"0007,{self.a.pk},", f"{self.n},{self.a.pk},"])
        before = self.state()
        response = self.client.post(self.url, {"file": SimpleUploadedFile("template.csv", template.content)})
        self.assertEqual((response.context["result"]["changes"], response.context["result"]["blank"]), (0, 2))
        self.assertContains(response, "Nothing to import")
        self.assertNotContains(response, 'name="token"')
        self.assertEqual(self.state(), before)

        foreign = Assessment.objects.exclude(offering=self.offering).first()
        self.assertEqual(self.client.get(reverse("offering_grade_import_template", args=[self.offering.pk]),
                                         {"assessment": foreign.pk}).status_code, 404)

    def test_preview_tells_missing_blank_zero_and_equal_apart_and_writes_nothing(self):
        before = self.state()
        response = self.upload(*self.mixed())
        self.assertEqual(self.state(), before)
        result = response.context["result"]
        self.assertEqual([row["kind"] for row in result["rows"]], ["change", "new", "blank", "same"])
        self.assertEqual((result["changes"], result["new"], result["blank"], result["same"]), (2, 1, 1, 1))
        self.assertEqual(b64decode(result["content"]), self.csv(*self.mixed()))
        rows = response.content.decode().split("<tbody>")[1].split("</tr>")
        expected = [("10.00", "12.50", "Changes"), ("Not graded", "0.00", "a real 0", "New grade"),
                    ("a real 0", "Blank", "blank keeps it"), ("40.00", "same score")]
        for row, texts in zip(rows, expected):
            for text in texts:
                self.assertIn(text, row)
        self.assertContains(response, "Import 2 grades")
        page = parse(response)
        self.assertEqual((page.h1_count, page.unlabelled_controls()), (1, []))
        # Cancel is a plain link back to the grade book.
        self.assertContains(response, f'<a class="btn btn-ghost" href="{self.gradebook}">Cancel</a>')
        self.client.get(self.gradebook)
        self.assertEqual(self.state(), before)

    def test_confirm_saves_the_preview_and_reports_a_truthful_count(self):
        response = self.upload(*self.mixed())
        done = self.confirm(response, follow=True)
        self.assertRedirects(done, self.gradebook)
        self.assertContains(done, "Import saved: 2 grades changed from grades.csv.")
        self.assertEqual(Grade.objects.get(enrollment=self.enrollment, assessment=self.a).score, Decimal("12.5"))
        self.assertEqual(Grade.objects.get(enrollment=self.enrollment, assessment=self.b).score, Decimal("0"))
        self.assertEqual(Grade.objects.get(enrollment=self.other, assessment=self.a).score, Decimal("0"))
        rows = [history_row(entry) for entry in history_entries(self.enrollment.pk).filter(user=self.user)]
        self.assertEqual([row["source"] for row in rows], ["CSV import", "CSV import"])
        self.assertFalse(history_entries(self.other.pk).filter(user=self.user).exists())

        before = self.state()
        again = self.confirm(response)
        self.assertContains(again, "This preview was already confirmed")
        self.assertEqual(self.state(), before)

    def test_one_invalid_row_blocks_the_whole_file(self):
        before = self.state()
        response = self.upload(f"0007,{self.a.pk},5", f"7,{self.a.pk},5", f"0007,{self.b.pk},9999", "only,two")
        self.assertEqual(self.state(), before)
        self.assertContains(response, "Nothing can be imported until every row is valid")
        for text in ("Line 3", "No student numbered “7” is in this class", "Line 4", "is above the maximum of",
                     "Line 5", "This line has 2 values"):
            self.assertContains(response, text)
        self.assertEqual(len(response.context["result"]["line_problems"]), 3)
        self.assertNotContains(response, 'name="token"')
        self.assertContains(response, "Choose another file")

    def test_file_problems_say_how_to_fix_the_file(self):
        excel = SimpleUploadedFile("excel.csv", b"student_number;assessment_id;score\r\n0007;1;5")
        response = self.client.post(self.url, {"file": excel})
        self.assertContains(response, "excel.csv can’t be imported. Nothing was saved.")
        self.assertContains(response, "semicolons")
        self.assertContains(self.client.post(self.url, {}), "This field is required.")

    def test_stale_confirmation_saves_nothing_and_shows_the_newer_grade(self):
        response = self.upload(f"0007,{self.a.pk},5")
        Grade.objects.filter(enrollment=self.enrollment, assessment=self.a).update(score=Decimal("7"))
        before = self.state()
        again = self.confirm(response)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(self.state(), before)
        self.assertContains(again, "Nothing was saved. Grades or class settings changed after your preview.")
        row, = again.context["result"]["rows"]
        self.assertEqual(row["previous"], Decimal("7"))
        self.assertNotEqual(again.context["result"]["token"], response.context["result"]["token"])
        self.assertRedirects(self.confirm(again), self.gradebook)
        self.assertEqual(Grade.objects.get(enrollment=self.enrollment, assessment=self.a).score, Decimal("5"))

    def test_a_changed_file_or_token_is_refused(self):
        response = self.upload(f"0007,{self.a.pk},5")
        before = self.state()
        altered = b64encode(self.csv(f"0007,{self.a.pk},6")).decode()
        for changes in ({"content": altered}, {"content": "not base64!"}, {"token": "forged"}):
            with self.subTest(changes=changes):
                self.assertContains(self.confirm(response, **changes), "didn’t match the file you previewed")
                self.assertEqual(self.state(), before)
