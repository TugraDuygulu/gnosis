# Issue #3 — model/documentation alignment completion record

Prepared 1 November 2026 against actual local source `eb23586b2b2f635629d9a08f5db1cfa6b0dee53a`. This is technical alignment verification, not evidence of formal team or instructor sign-off.

## Current publication state — 1 November 2026

[Issue #3](https://github.com/TugraDuygulu/gnosis/issues/3) is **closed/completed** with owner-approved verification evidence. [PR #23](https://github.com/TugraDuygulu/gnosis/pull/23) is **open, awaiting merge review**; original report commit `e8bc8cafc693833f5e134beec147a2879607a03e` is published. [GitHub Actions run 41327877627](https://github.com/TugraDuygulu/gnosis/actions/runs/41327877627) passed all **69 Django tests** on that head. The **17 standalone SQL cases and SQLite/report probes were local checks**, not workflow steps. [Issue #13](https://github.com/TugraDuygulu/gnosis/issues/13) remains open; this is not a final submission. Review corrections after that commit require separate commit/push approval; that CI result does not certify later uncommitted edits.


## Checks performed

The actual PyCharm project was clean on `sql/issue-4-queries` at `95b7139`. Local main was safely fast-forwarded to the reported merged remote commit; report work is isolated on `docs/cse321-report-workspace`. No recovery patch or previous merge/issue closure was repeated.

The [verification helper](tools/verify_model_alignment.py) invokes the existing schema measurement tool against a new temporary database. It migrates core.0001–0009, seeds the fictional pilot once, and checks:

| Check | Observed result |
| --- | --- |
| Models vs migrated model state | Agreement, checked by field deconstruction in measure_schema.py |
| Entities/columns | 15 application models; all 64 columns covered in inventory, ERD and field dictionary |
| Relationships | All 20 FK endpoint/column/cardinality declarations match the Mermaid ERD |
| Nullable columns | Only CourseOffering.po_framework_id and Grade.score |
| Physical constraints | Fresh DDL, FK metadata and columns exactly match the documented inventory |
| Indexes | All names/columns/uniqueness agree: 14 unique and 20 nonunique FK secondary indexes; PKs are rowid aliases |
| Fresh seed | 60 application rows across the 15 tables; related records created successfully |
| Integrity / FK checks | `ok` / no violations |
| Source provenance | Models, migrations, calculation services and pilot seed hashes match the reviewed inventory |

See [alignment_verification.json](evidence/alignment_verification.json). Reproduce with the project virtualenv:

```sh
.venv/bin/python docs/reports/cse321/tools/verify_model_alignment.py --output-dir /tmp/gnosis-alignment-review
```

Use a new output directory. The full fresh schema metadata is written there for inspection; it is not a copy of the development database. Existing [canonical DDL/inventory](../../data/pilot_2026-11-01/schema_inventory.json) and [field dictionary](../../data/pilot_2026-11-01/field_dictionary.md) remain unchanged.

## Manual narrative checks

[database_design.md](../../database_design.md) correctly separates named SQL CHECKs/UNIQUEs/NOT NULL/FKs from Django validating saves, ModelForms, native enrollment eligibility and calculator guards. SQL has no grade upper-bound or cross-table curriculum/program equality constraint. All FK model declarations use PROTECT, whereas SQLite DDL has deferred NO ACTION references. Positive integer fields allow zero at SQL level; explicit strength/contribution range checks enforce 1–5. Python defaults and Django length/decimal validation are not overstated as SQLite defaults or strict fixed-point storage.

The text acknowledges the offering's redundant course/curriculum references, raw/bulk-write bypasses, editable historical configuration, retake/equivalence selection, version-publication rules and institution-wide coverage policy. No schema redesign or newly approved domain policy is implied. Dated older “pending” sentences in historical verification/acceptance documents are not evidence that the already merged #2/#4 work should be repeated.

No blocking model/schema documentation discrepancy was found. Historical issue #3 text saying 42 tests is a dated October 31 record, not the current count. The separate latest test record is retained in [VALIDATION.md](VALIDATION.md).

## Exact implementation and verification links

- [Models at verified main](https://github.com/TugraDuygulu/gnosis/blob/eb23586b2b2f635629d9a08f5db1cfa6b0dee53a/core/models.py), [migrations](https://github.com/TugraDuygulu/gnosis/tree/eb23586b2b2f635629d9a08f5db1cfa6b0dee53a/core/migrations).
- [Verified database documentation](https://github.com/TugraDuygulu/gnosis/blob/eb23586b2b2f635629d9a08f5db1cfa6b0dee53a/docs/database_design.md), [field dictionary](https://github.com/TugraDuygulu/gnosis/blob/eb23586b2b2f635629d9a08f5db1cfa6b0dee53a/docs/data/pilot_2026-11-01/field_dictionary.md).
- [PR #21](https://github.com/TugraDuygulu/gnosis/pull/21), merged documentation; [PR #22](https://github.com/TugraDuygulu/gnosis/pull/22), merged SQL evidence.
- [Original academic structure 9bf65d8](https://github.com/TugraDuygulu/gnosis/commit/9bf65d8), [assessment/grade/LO f87f0da](https://github.com/TugraDuygulu/gnosis/commit/f87f0da), [framework work 3555fc4](https://github.com/TugraDuygulu/gnosis/commit/3555fc4), [framework work d01a221](https://github.com/TugraDuygulu/gnosis/commit/d01a221), [course contribution 907e695](https://github.com/TugraDuygulu/gnosis/commit/907e695), [curriculum validation 0e72f58](https://github.com/TugraDuygulu/gnosis/commit/0e72f58). These identifiers are preserved from issue #3's delivered-evidence record; they are not new work or invented team approvals.

## Historical proposed closure wording — superseded by approved closure

The following paragraph was drafted before publication and owner approval. It is retained as a historical proposal, not a current instruction to close the issue again. The actual dated completion record is on [issue #3](https://github.com/TugraDuygulu/gnosis/issues/3).

Issue #3's documented model-alignment work is complete at source eb23586. A fresh isolated migrate+pilot run confirmed 15 models, 64 columns, 20 FK relationships, 14 unique plus 20 FK indexes, agreement of model/migration state and documented physical DDL, complete ERD/dictionary coverage, and successful integrity/FK checks. SQL-enforced rules, application validations and unresolved policies remain distinguished. No model, migration or application behavior changed. The report workspace records reproducible verification and exact implementation/documentation links. This establishes technical alignment; formal team/instructor schema sign-off is not claimed. Close only after owner approval, preserving the original issue history.
