# CSE321 midterm report workspace

Working material for the **12 November 2026** Data & System Architecture checkpoint. Baseline: merged main `eb23586b2b2f635629d9a08f5db1cfa6b0dee53a`. This directory is not a final submission.

Start with:

- [Six-section report draft](REPORT_DRAFT.md) — substantive features, system design, data model, physical design, consistency and pending member evidence.
- [Requirements/evidence checklist](REQUIREMENTS_EVIDENCE.md) — official requirements mapped to evidence and gaps.
- [Missing information and next work](MISSING_INFORMATION.md).
- [Issue #3 completed verification record](ISSUE_3_VERIFICATION.md).
- [Validation record](VALIDATION.md) and [sources](SOURCES.md).

## Current publication state — 1 November 2026

[Issue #3](https://github.com/TugraDuygulu/gnosis/issues/3) is **closed/completed** with owner-approved verification evidence. [PR #23](https://github.com/TugraDuygulu/gnosis/pull/23) is **open, awaiting merge review**; original report commit `e8bc8cafc693833f5e134beec147a2879607a03e` is published. [GitHub Actions run 41327877627](https://github.com/TugraDuygulu/gnosis/actions/runs/41327877627) passed all **69 Django tests** on that head. The **17 standalone SQL cases and SQLite/report probes were local checks**, not workflow steps. [Issue #13](https://github.com/TugraDuygulu/gnosis/issues/13) remains open; this is not a final submission. Review corrections after that commit require separate commit/push approval; that CI result does not certify later uncommitted edits.

[Review correction record](REVIEW_CORRECTIONS.md) documents the subsequent local cleanup and approval boundary.

## Figures

| Figure | Editable source | Reusable export |
| --- | --- | --- |
| Application components | [architecture.mmd](diagrams/architecture.mmd) | [SVG](diagrams/architecture.svg), [PNG](diagrams/architecture.png) |
| Selected grading classes | [grading-classes.mmd](diagrams/grading-classes.mmd) | [SVG](diagrams/grading-classes.svg), [PNG](diagrams/grading-classes.png) |
| Grade save → result inspection | [grade-workflow.mmd](diagrams/grade-workflow.mmd) | [SVG](diagrams/grade-workflow.svg), [PNG](diagrams/grade-workflow.png) |
| Complete/focused relational ERDs | [Existing diagram sources](../../diagrams/) | Existing SVGs reused in the draft |

The class view shows behavior and inheritance beyond the relational ERD. Calculation services are functions, not classes. The component diagram is one Django application and a local database, not a proposed microservice deployment. DOT/Graphviz exports are sibling layouts of the same components/classes, not direct Mermaid SVG rendering. All three Mermaid sources were syntax-checked with Mermaid 11.12.1. The sequence SVG is a source-derived custom layout, not a direct Mermaid render. [Representative-page review](LAYOUT_REVIEW.md) records 125% viewing observations; full final-format/page-layout QA remains pending.

## Reproduce the new evidence

Use a new output path for each run. Both tools always create temporary databases; neither accepts a development database path:

```sh
.venv/bin/python docs/reports/cse321/tools/verify_model_alignment.py --output-dir /tmp/gnosis-alignment-review
.venv/bin/python docs/reports/cse321/tools/probe_sqlite_consistency.py --output /tmp/gnosis-consistency-review.json
```

Alignment invokes the existing migration/pilot measurement helper, compares physical/schema metadata to the reviewed inventory and checks the full ERD/dictionary. The consistency probe captures Django/SQLite settings and controlled two-connection/atomic observations, not an application stress test.

For diagram export maintenance only:

```sh
python3 docs/reports/cse321/tools/build_diagram_exports.py
python3 docs/reports/cse321/tools/export_workflow.py
npm install --prefix /tmp/gnosis-diagram-runtime @viz-js/viz@3.9.0 @resvg/resvg-js@2.6.2
node docs/reports/cse321/tools/render_diagrams.mjs /tmp/gnosis-diagram-runtime
```

These are optional documentation dependencies, not application requirements. Keep Mermaid and sibling DOT layouts consistent when editing the diagrams. Review changes before any publication or issue closure.
