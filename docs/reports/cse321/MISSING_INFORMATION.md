# Remaining information and work before November 12

## Facts the team/user must supply

1. Registered team name and all four members' names; whether student IDs must appear. “Gnosis” is currently the product name, not assumed registration evidence.
2. Each person's actual completed work and review/design contribution, with commit/PR/document links where possible and their confirmation. Resolve attribution before filling Section 6; no assignments have been made by this draft.
3. Exact checkpoint submission channel/file format/copy requirements and allocated presentation duration. The official sources establish the November 12 in-class presentation/report and six-section structure, but this workspace does not invent a minute count or upload portal.
4. Who will present each portion and what each person has independently reviewed. Owner review/AI assistance is not formal team/instructor sign-off.

## Review and document preparation

- Review issue #3's closure record and approve whether to close it with the fresh verification links.
- Review Section 1's scope wording, architecture/class slice, grade workflow, SQL interpretation and transaction/isolation limits.
- Decide whether to add another focused class diagram (for intake/calculations) after reviewing the existing one. Calculators are module functions; do not invent service classes.
- Choose the intended paper/page size and final authoring format, then render and inspect every figure and SQL excerpt at the required 125% scale. Full ERD is supporting material; use focused figures in the body. The current SVGs are reusable working exports, not proof of final page readability.
- Render/export the sequence diagram if it will be pasted into a non-Mermaid report editor. Retain its source and ensure transaction/error paths survive the export.
- Verify the official full PO wording against an accessible rendering of the primary table if the final report reproduces it; this workspace cites purpose/flow without newly transcribing that image-only table.
- Refresh source/measurement dates if the application or fictional dataset changes before submission. Keep checkpoint sizes labeled as such; final-stage sizes require a later final snapshot.

## Technical investigations, only where a claim needs them

The existing small checks support correctness/consistency claims within their stated domain. Do not delay the November draft by implementing a speculative redesign.

- Concurrent browser/HTTP edits are not stress-tested here. If the report needs measured capacity or a stronger concurrency guarantee, define and run a separate isolated experiment.
- No query plan/latency/load baseline or successful backup/restore/failover exercise exists in this workspace. Either document these as absent or scope the experiment explicitly; do not invent performance or recovery results.
- Outcome pages perform multiple reads without a transaction-wide snapshot; editable configuration can change historical results. These are source-based limits, not fixes made by this task. A feature change requires separate agreement.

## Approval boundary

All draft/diagram/probe changes are local on docs/cse321-report-workspace. Commit, push, PR creation, merges and issue closure need explicit approval. #2/#4 merges/closures are already completed and must not be repeated. No model/migration/UI/configuration or development-data change is authorized by this report work.
