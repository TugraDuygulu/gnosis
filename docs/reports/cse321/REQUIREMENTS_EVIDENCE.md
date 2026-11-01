# CSE321 requirements → evidence checklist

Status terms: **Drafted** = substantive text/source evidence prepared, owner review pending; **Verified** = a stated technical check actually passed; **Pending input** = a fact cannot be inferred; **Pending QA** = rendering/submission check not yet completed. None means the report is final or instructor-approved.

| Requirement | Official source | Prepared evidence / location | Status and remaining action |
| --- | --- | --- | --- |
| November 12 presentation + checkpoint report | Guidelines p.14 | REPORT_DRAFT header; all six required sections | Drafted; confirm exact submission channel, file format, copies and presentation duration |
| Four members; team/member/repository header | Format p.1; Guidelines pp.3,12,16 | Draft header and Section 6 | Pending input: registered team name, four names and IDs if required |
| No separate title page | Format p.1 | Draft begins with required header | Drafted; check eventual rendered document |
| Figures and code 125% visible | Format p.1; Guidelines p.16 | Reusable SVGs, focused ERD views, 84–87-character SQL sources | Pending QA at intended paper/page size and 125% viewing; no final export yet |
| §1 key features | Format §1 | Native staff journey, score/coverage/history and current limits | Drafted; owner wording review |
| §2 actual system components/interactions | Format §2; Guidelines p.14 | architecture.mmd/.svg, route/component table and grade workflow | Drafted; no speculative Vue/API/cloud tier |
| §2 separate class/object relationships | Format §2 | grading-classes.mmd/.svg: inheritance, behavior and dependencies | Drafted focused grading class view; confirm with team whether more class slices are useful |
| §2 meaningful workflow | Format §2 | grade-workflow.mmd and explanatory narrative | Diagram syntax verified; sequence source has no exported image yet |
| §2 auth, forms and Admin paths | Actual implementation supporting architecture | Staff/action permission table; Form/ModelForm/Admin descriptions | Source verified; instructor ownership remains unimplemented |
| §3 data model diagram | Format §3 | Complete 15-model ERD plus 3 focused figures from #2 | Alignment verified fresh; report layout QA pending |
| §3 tables and full fields | Format §3 | 15-table metrics table and linked complete 64-field dictionary | Verified; references reusable rather than duplicated field dictionary |
| §3 keys, constraints, cardinality | Format §3; issue #3 | DDL inventory, narrative SQL vs Django boundaries, alignment JSON | Verified: 20 FKs, 14 unique and 20 FK indexes; issue #3 closure needs approval |
| §3 normalization/schema shape | Format §3 | Operational relational design and offering redundancy discussion | Drafted; no blanket strict 3NF or warehouse claim |
| §3 row/column/raw size | Format §3, final-stage wording | Fictional checkpoint payload/table/index bytes, exact runtime and recipe | Verified checkpoint only; refresh dataset if changed and again at final stage |
| Three reproducible SQL questions | Issue #4's October 22 checklist record | Merged sql/README.md, statements, expected/actual tables, 17 tests | Existing evidence plus fresh rerun; #4 already closed, no duplicate backlink needed |
| §4 actual index types/use | Format §4 | 34 secondary indexes, rowid PK distinction and exact index inventory | Drafted/verified; no measured speedup claimed |
| §4 materialized views/cubes | Format §4 | Explicitly absent; request-time calculation explained | Source verified |
| §4 partitioning/replication | Format §4 | Explicitly absent; proposals distinguished | Source/config verified; no new implementation authorized |
| §4 scaling and failure behavior | Format §4 | ORM loop concern, SQLite writer limits, retries and operational gaps | Drafted; load/query-plan/backup-restore experiments pending if performance/recovery claims are added |
| §5 transaction boundaries | Format §5 | Native registration/enrollment/grade-history/Admin/seed table | Source verified; Django Admin framework transaction inspected |
| §5 specific isolation/concurrency | Format §5 | Fresh file probe, BEGIN/savepoint trace, private connections, BUSY observations | Verified within experiment limits; no real development DB journal-mode or HTTP stress claim |
| §5 page-level consistency limitations | Actual source boundary | Outcome reads lack enclosing snapshot; configurations editable | Documented source-based limitation; stronger claims require targeted reproduction |
| §6 actual member work | Format §6 | Pending contribution matrix and real PR links | Pending input from all four members; never infer tasks solely from author account |
| Source dates and truthful review/CI evidence | Issue #13 | Baseline SHA, SOURCES.md, validation, PR/run links | Drafted; owner review is not teammate review |

## Report workspace completion boundary

Prepared: a substantive six-section draft, architecture and focused behavior/class diagrams, workflow sequence, reusable ER/SQL material, fresh model-alignment and SQLite checks, and explicit evidence gaps. Not prepared: a final PDF/DOCX submission, invented member allocations, new app features, deployment configuration, load benchmark or final-stage measurements. No live issue status/checklist was changed in creating this workspace.
