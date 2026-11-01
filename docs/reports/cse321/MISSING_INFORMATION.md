# Remaining information and work before November 12

## Current publication state — 1 November 2026

[Issue #3](https://github.com/TugraDuygulu/gnosis/issues/3) is **closed/completed** with owner-approved verification evidence. [PR #23](https://github.com/TugraDuygulu/gnosis/pull/23) is **open, awaiting merge review**; original report commit `e8bc8cafc693833f5e134beec147a2879607a03e` is published. [GitHub Actions run 41327877627](https://github.com/TugraDuygulu/gnosis/actions/runs/41327877627) passed all **69 Django tests** on that head. The **17 standalone SQL cases and SQLite/report probes were local checks**, not workflow steps. [Issue #13](https://github.com/TugraDuygulu/gnosis/issues/13) remains open; this is not a final submission. Review corrections after that commit require separate commit/push approval; that CI result does not certify later uncommitted edits.

## Facts the team/user must supply

1. Registered team name and all four members' names; whether student IDs must appear. “Gnosis” is currently the product name, not assumed registration evidence.
2. Each person's actual completed work and review/design contribution, with commit/PR/document links where possible and their confirmation. Resolve attribution before filling Section 6; no assignments have been made by this draft.
3. Exact checkpoint submission channel/file format, number of printed copies and allocated presentation duration. Format p.1 and Guidelines pp.14,16 already require the November 12 in-class presentation/report and a printed report brought to the demo. The six-section structure is established; an upload portal, minute count and copy count are not.
4. Who will present each portion and what each person has independently reviewed. Owner review/AI assistance is not formal team/instructor sign-off.

## Review and document preparation

- Review the recorded issue #3 closure evidence if needed; closure is already complete and must not be repeated.
- Review Section 1's scope wording, architecture/class slice, grade workflow, SQL interpretation and transaction/isolation limits.
- A second calculation class diagram was assessed during PR #23 review and is not added: the grading class view already demonstrates inheritance/behavior, Section 2 explains the actual module-function calls, and Section 3 covers the outcome model relationships. Another class slice would largely duplicate those views. Reconsider only for a concrete explanation gap; do not invent service classes.
- Choose the intended paper/page size and final authoring format, then render and inspect every figure and SQL excerpt at the required 125% scale. Full ERD is supporting material; use focused figures in the body. The current SVGs are reusable working exports, not proof of final page readability.
- The grade-workflow sequence now has source-derived SVG/PNG exports. Its full-height export needs a dedicated/split layout in the final report; do not shrink it into a small body figure. See [layout review](LAYOUT_REVIEW.md) for representative-page observations and remaining limits.
- Verify the official full PO wording against an accessible rendering of the primary table if the final report reproduces it; this workspace cites purpose/flow without newly transcribing that image-only table.
- Refresh source/measurement dates if the application or fictional dataset changes before submission. Keep checkpoint sizes labeled as such; final-stage sizes require a later final snapshot.

## Technical investigations, only where a claim needs them

The existing small checks support correctness/consistency claims within their stated domain. Do not delay the November draft by implementing a speculative redesign.

- Concurrent browser/HTTP edits are not stress-tested here. If the report needs measured capacity or a stronger concurrency guarantee, define and run a separate isolated experiment.
- No query plan/latency/load baseline or successful backup/restore/failover exercise exists in this workspace. Either document these as absent or scope the experiment explicitly; do not invent performance or recovery results.
- Outcome pages perform multiple reads without a transaction-wide snapshot; editable configuration can change historical results. These are source-based limits, not fixes made by this task. A feature change requires separate agreement.

## Approval boundary

The original report workspace is committed/pushed in open PR #23 on docs/cse321-report-workspace; issue #3 is already closed. Review corrections are prepared locally and require approval before a new commit/push. PR #23 merge is not authorized, and issue #13 stays open. #2/#4 merges/closures are already completed and must not be repeated. No model/migration/UI/configuration or development-data change is authorized by this report work.
