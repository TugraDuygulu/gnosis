"""Turkish-language usability checks.

Acıbadem is the pilot customer, so staff will type Turkish names (ç ğ ı İ ö ş ü)
into forms and search boxes. These tests check that such names survive the
whole journey and record a known search limitation of the SQLite backend.
"""
import unittest
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import CourseOffering, Program, Student

TURKISH_NAME = "Ramazan Öztekin Çağrı Işıl Şükrü Güneş İnce"


class TurkishTextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.program = Program.objects.get(code="PILOT")
        cls.admin = get_user_model().objects.create_superuser("turkish_text_admin")
        cls.student = Student.objects.create(
            full_name="Şule Çelik", student_number="TR0001", program=cls.program,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def search_names(self, query):
        response = self.client.get(reverse("student_list"), {"q": query})
        self.assertEqual(response.status_code, 200)
        return [student.full_name for student in response.context["students"]]

    def test_registration_keeps_every_turkish_letter(self):
        response = self.client.post(reverse("student_register"), {
            "full_name": f"  {TURKISH_NAME}  ",
            "student_number": "TR0002",
            "program": self.program.pk,
        }, follow=True)
        student = Student.objects.get(student_number="TR0002")
        self.assertEqual(student.full_name, TURKISH_NAME)
        self.assertContains(response, TURKISH_NAME)

    def test_turkish_name_appears_on_roster_after_enrollment(self):
        offering = CourseOffering.objects.get(course__code="PILOT321")
        self.client.post(
            reverse("student_enroll", args=[self.student.pk]), {"offering": offering.pk},
        )
        roster = self.client.get(reverse("offering_detail", args=[offering.pk]))
        self.assertContains(roster, "Şule Çelik")

    def test_search_with_the_same_spelling_finds_the_student(self):
        for query in ("Şule", "Çelik", "Şule Çelik", "ule"):
            with self.subTest(query=query):
                self.assertIn("Şule Çelik", self.search_names(query))

    def test_search_ignores_case_for_ascii_letters(self):
        Student.objects.create(full_name="Pilot Ramazan", student_number="TR0003",
                               program=self.program)
        for query in ("ramazan", "RAMAZAN", "Ramazan"):
            with self.subTest(query=query):
                self.assertIn("Pilot Ramazan", self.search_names(query))

    @unittest.expectedFailure
    def test_search_ignores_case_for_turkish_letters(self):
        """Known issue: SQLite's case-insensitive LIKE only folds ASCII letters.

        Typing "çelik" or "ŞULE" does not find "Şule Çelik". Remove this
        decorator once search folds Turkish letters; the test will then pass.
        """
        for query in ("çelik", "şule", "ÇELİK", "ŞULE"):
            with self.subTest(query=query):
                self.assertIn("Şule Çelik", self.search_names(query))
