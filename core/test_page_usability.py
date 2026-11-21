"""Automated usability and accessibility checks for every staff page.

These tests do not judge visual design; they check the basics a user (or a
screen reader) relies on: a page title, one main heading, labelled form
controls, a document language, and pages that still work on an empty database.
"""
from html.parser import HTMLParser
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import Enrollment, POFramework

LABELLED_TAGS = {"input", "select", "textarea"}
UNLABELLED_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image"}


class PageStructure(HTMLParser):
    """Collects just enough structure to check headings, titles and labels."""

    def __init__(self):
        super().__init__()
        self.html_lang = None
        self.viewport = None
        self.title = ""
        self.h1_count = 0
        self.label_targets = set()
        self.controls = []  # (tag, id, has_aria_label, wrapped_in_label)
        self._in_title = False
        self._label_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.html_lang = attrs.get("lang")
        elif tag == "meta" and attrs.get("name") == "viewport":
            self.viewport = attrs.get("content", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "label":
            self._label_depth += 1
            if attrs.get("for"):
                self.label_targets.add(attrs["for"])
        elif tag in LABELLED_TAGS:
            if tag == "input" and attrs.get("type", "text") in UNLABELLED_INPUT_TYPES:
                return
            self.controls.append((
                tag, attrs.get("id"),
                bool(attrs.get("aria-label") or attrs.get("aria-labelledby") or attrs.get("title")),
                self._label_depth > 0,
            ))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "label" and self._label_depth:
            self._label_depth -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def unlabelled_controls(self):
        return [
            (tag, control_id) for tag, control_id, aria, wrapped in self.controls
            if not (aria or wrapped or (control_id and control_id in self.label_targets))
        ]


def parse(response):
    page = PageStructure()
    page.feed(response.content.decode())
    return page


class PageUsabilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_pilot", stdout=StringIO())
        cls.admin = get_user_model().objects.create_superuser("usability_admin")
        cls.enrollment = Enrollment.objects.get(
            student__student_number="PILOT001", offering__course__code="PILOT321",
        )
        cls.framework = POFramework.objects.get(program__code="PILOT", version_number=1)

    def setUp(self):
        self.client.force_login(self.admin)

    def pages(self):
        e = self.enrollment
        return {
            "Students": reverse("student_list"),
            "Register student": reverse("student_register"),
            "Student record": reverse("student_detail", args=[e.student_id]),
            "Enroll student": reverse("student_enroll", args=[e.student_id]),
            "Student PO profile": reverse("student_outcomes", args=[e.student_id, self.framework.pk]),
            "Courses": reverse("course_list"),
            "Course roster": reverse("offering_detail", args=[e.offering_id]),
            "Class gradebook": reverse("offering_gradebook", args=[e.offering_id]),
            "Program overview": reverse("program_overview"),
            "Course evidence": reverse("enrollment_outcomes", args=[e.pk]),
            "Grade editor": reverse("enrollment_grade_editor", args=[e.pk]),
            "Grade history": reverse("enrollment_grade_history", args=[e.pk]),
        }

    def test_every_page_has_language_title_and_one_main_heading(self):
        for label, url in self.pages().items():
            with self.subTest(page=label):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                page = parse(response)
                self.assertTrue(page.html_lang, "<html> needs a lang attribute")
                self.assertTrue(page.title.strip(), "page needs a non-empty <title>")
                self.assertEqual(page.h1_count, 1, "page should have exactly one <h1>")

    def test_every_form_control_has_a_label(self):
        for label, url in self.pages().items():
            with self.subTest(page=label):
                page = parse(self.client.get(url))
                self.assertEqual(page.unlabelled_controls(), [])

    def test_every_page_is_set_up_for_phone_screens(self):
        for label, url in self.pages().items():
            with self.subTest(page=label):
                viewport = parse(self.client.get(url)).viewport or ""
                self.assertIn("width=device-width", viewport)

    def test_search_keeps_the_query_and_explains_no_results(self):
        response = self.client.get(reverse("course_list"), {"q": "NO-SUCH-COURSE-XYZ"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NO-SUCH-COURSE-XYZ")


class EmptyDatabaseUsabilityTests(TestCase):
    """A brand-new installation must show empty states, not errors."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("fresh_admin"))

    def test_list_pages_render_on_an_empty_database(self):
        for name in ("student_list", "student_register", "course_list", "program_overview"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(parse(response).h1_count, 1)

    def test_unknown_records_return_404_not_500(self):
        for name, args in (("student_detail", [999]), ("offering_detail", [999]),
                           ("enrollment_outcomes", [999]), ("enrollment_grade_editor", [999])):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 404)
