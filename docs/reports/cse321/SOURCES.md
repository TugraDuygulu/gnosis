# Source register and claim boundaries

Reviewed for the November 1 working draft. Instructor PDFs control course requirements; source code controls implementation claims. The report is a checkpoint draft, not proof of approval or final completion.

| ID | Source | Use / exact location |
| --- | --- | --- |
| S1 | [CSE 321 - Report Format 2.pdf](https://chatgpt.com/library?file_id=libfile_691bc9e3490081919db12e921faa2465&account_id=personal), 2 pages | p.1: first-page team/member/repo header, no separate title page, 125% figure/code visibility, Sections 1–5; p.2: Section 6 and actual member tasks |
| S2 | [CSE 311 CSE 321 Team Project Guidelines.pdf](https://chatgpt.com/library?file_id=libfile_b86fbe41e8b0819189a39245ad7ea625&account_id=personal), October 22 upload, 19 pages | pp.2–4 purpose/Django/four-person team/eleven POs; pp.5–7 worked weights/example; p.10 AI allowed; p.14 November 12 architecture/class/data checkpoint; pp.15–18 final report, readability and six-section outlines |
| S3 | [CSE 311 CSE 321 Team Project Brief.pdf](https://chatgpt.com/library?file_id=libfile_a8e78eb74e788191bb55b7a7ef5ff160&account_id=personal), October 22 upload, 22 pages | p.1 purpose; pp.5–17 illustrative assessment→LO→PO flow; pp.18–20 course contribution scale; p.21 role/configuration questions remain design choices; p.22 shared Python+Django project |
| S4 | [SQLite: Isolation](https://www.sqlite.org/isolation.html), accessed 1 Nov 2026 | Isolation across connections, serialized writers and rollback journal semantics. Report describes only the measured default-style fresh file; no WAL deployment claim |
| S5 | [Django 6.1 database notes](https://docs.djangoproject.com/en/6.1/ref/databases/#sqlite-notes), accessed 1 Nov 2026; installed Django 6.1.2 backend source | SQLite select_for_update limitation; installed DatabaseWrapper transaction start and ModelAdmin changeform transaction inspected directly |

The Guidelines' weighted LO example is consistent with exact 86 and 580/7 before display rounding. The Brief's pages 13–17 use an early rounded 82 and illustrative outcome descriptions; these do not replace the implemented calculation policy or official PO definitions. Brief pages 2–4 contain image content whose text extraction is incomplete; this session requested those page images, but the connector returned asset pointers rather than locally inspectable pixels. Do not claim that this workspace independently re-OCRed/revalidated the full official PO table. Existing pilot definitions and their prior provenance remain in the seed and earlier source audit. The report does not introduce new PO wording or mapping approval.

## Implementation evidence

| Claim area | Authoritative repository source at baseline eb23586 |
| --- | --- |
| Settings, auth/session/CSRF middleware, database and entry points | config/settings.py, config/urls.py, config/asgi.py, config/wsgi.py |
| Routes and native staff permission checks | core/urls.py, core/views.py |
| Forms, revision token, field validation and writes | core/grade_editor.py, core/student_intake.py |
| Audit scope and Admin integration | core/grade_history.py, core/admin.py |
| Full schema | core/models.py, core/migrations/0001–0009; issue #3's fresh physical comparison |
| Calculation semantics/provenance | core/services/lo_calculator.py, po_calculator.py, student_po_calculator.py; docs/calculation_policy.md |
| Server-rendered UI | core/templates/core/*.html; native forms inspected for CSRF and contextual links |
| Existing regressions | core/tests.py and core/test_*.py; grade/history/intake tests include actual rollback/conflict/permission cases |
| CI scope | .github/workflows/django.yml; SQL 17-case verifier is not currently a workflow step |
| Pilot and measurements | seed_pilot.py; docs/data/pilot_2026-11-01/; sql/evidence/pilot_2026-11-01/ |

For exact hashes/commands/results produced by this workspace see [VALIDATION.md](VALIDATION.md) and evidence JSON. A code path inspection is not a load test; a mocked lock-error test is not a concurrent HTTP experiment; an ORM declaration is not necessarily a physical SQL constraint. Planned features and absent components are labeled accordingly.
