# November 1 report-workspace verification

Source baseline: `eb23586b2b2f635629d9a08f5db1cfa6b0dee53a`; Python 3.14.3, Django 6.1.2, SQLite 3.50.4. Tests/tools executed using the actual project virtualenv against a tracked-source copy with no development DB. Installation guards compare every existing source file with the live project before writing documentation.

## Current publication state — 1 November 2026

[Issue #3](https://github.com/TugraDuygulu/gnosis/issues/3) is **closed/completed** with owner-approved verification evidence. [PR #23](https://github.com/TugraDuygulu/gnosis/pull/23) is **open, awaiting merge review**; original report commit `e8bc8cafc693833f5e134beec147a2879607a03e` is published. [GitHub Actions run 41327877627](https://github.com/TugraDuygulu/gnosis/actions/runs/41327877627) passed all **69 Django tests** on that head. The **17 standalone SQL cases and SQLite/report probes were local checks**, not workflow steps. [Issue #13](https://github.com/TugraDuygulu/gnosis/issues/13) remains open; this is not a final submission. Review corrections after that commit require separate commit/push approval; that CI result does not certify later uncommitted edits.

## Historical pre-publication verification

The table and source-copy checks below record the initial preparation before commit e8bc8ca. Their original no-publication statement applies to that phase only.

| Check actually performed | Result | Evidence / limitation |
| --- | --- | --- |
| Actual PyCharm Git inspection | Clean sql/issue-4-queries at 95b7139; safe fetch/fast-forward main to eb23586; new docs/cse321-report-workspace | No previous merge/closure repeated; no commit/push/PR in this task |
| Django system check | Passed | Current baseline configuration, not production certification |
| Missing-migration dry run | No changes detected | No model/migration changes proposed |
| Existing Django suite | 69 tests passed | Separate isolated test DB; includes grade/history rollback and intake regressions |
| Standalone SQL verifier | 17 cases passed; 122 numeric comparisons; max difference ~4.28571428571e-15 percentage points | [Fresh rerun metadata](evidence/sql_verification.json); canonical outputs retained under sql/evidence/ |
| Fresh model/schema/diagram agreement | Passed | [alignment_verification.json](evidence/alignment_verification.json); 15 models/64 columns/20 FKs/14 unique +20 FK indexes |
| SQLite integrity/FK checks | Passed on fresh fictional schema | Not a new claim about private development database contents |
| Two-connection consistency probe | Expected isolation, writer/commit lock conflicts and rollback observed | [sqlite_consistency.json](evidence/sqlite_consistency.json); engine/atomic probe, no HTTP stress or WAL/crash test |
| Installed Django transaction source | Inspected | Atomic BEGIN path, no select_for_update support; ModelAdmin wraps write change-form handling |
| Three Mermaid sources | Parsed successfully with Mermaid 11.12.1 | DOM-aware parser needed for flow/class labels; sequence syntax corrected before final pass |
| Architecture/class SVG/PNG | Rendered with Viz 3.9.0 and resvg 2.6.2; visually inspected | Sibling DOT exports, not direct Mermaid render; final page-layout/125% QA pending |
| Official report sources | Required PDF text read; relevant checkpoint/report pages revisited | See SOURCES.md for image-only Brief-page extraction limitation |

To repeat the checks from a normal checkout with its existing environment:

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test --verbosity 1
.venv/bin/python sql/verify_queries.py --output-dir /tmp/gnosis-report-sql-review
.venv/bin/python docs/reports/cse321/tools/verify_model_alignment.py --output-dir /tmp/gnosis-report-model-review
.venv/bin/python docs/reports/cse321/tools/probe_sqlite_consistency.py --output /tmp/gnosis-report-consistency-review.json
```

Choose fresh output paths. The standard application tests use their own test database. The two report tools and SQL verifier always construct temporary fictional databases. They do not change the project's models, production configuration or development data. At the historical pre-publication checkpoint, no CI run for the then-uncommitted report files or issue #3 closure was claimed. Publication, successful CI and approved closure subsequently occurred as recorded above. Formal teammate review and final submission are still not claimed.

## PR #23 review corrections

See [REVIEW_CORRECTIONS.md](REVIEW_CORRECTIONS.md) for the current documentation checks and [LAYOUT_REVIEW.md](LAYOUT_REVIEW.md) for representative-page inspection. These local checks are separate from the published-head CI result.
