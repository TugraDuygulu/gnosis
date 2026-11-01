# PR #23 review corrections — 1 November 2026

## Scope and review provenance

The owner supplied Chat's independent review of published commit `e8bc8cafc693833f5e134beec147a2879607a03e`. Chat reported the six-section technical content and diagrams sound overall and confirmed the 69-test CI run. This cleanup addresses publication-state wording, portable academic references and diagram reuse/readability. It does not imply formal team or instructor approval.

Live readback before editing confirmed: clean local `docs/cse321-report-workspace` at e8bc8ca; PR #23 open/unmerged on that head; issue #3 closed; run 41327877627 successful. Issue #13 remains open. Existing history and original evidence JSON are retained.

## Necessary corrections

- Updated ISSUE_3_VERIFICATION, MISSING_INFORMATION, VALIDATION and REQUIREMENTS_EVIDENCE, plus their README entry, to separate current published/closed state from historical pre-publication records. Published-head CI is distinguished from local SQL/SQLite/report checks and later uncommitted edits.
- Replaced personal Library URLs for all three instructor PDFs with exact titles, established edition/date information and page-specific requirements. No course/repository availability, publication date or URL was invented. Retained the brief's image-only PO-page extraction limitation.
- Rechecked component/class/sequence content against actual routing, forms, models, Admin hooks and calculation modules. No factual diagram correction or application change was needed. A second calculation class diagram would duplicate the existing function explanation and focused outcome ERDs, so it was not added.
- Added source-derived grade-workflow SVG/PNG, an exporter that fails on unsupported sequence syntax, and links from the report/README. Only the sequence-export link changed in the substantive report draft.
- Added an actual four-page representative PDF and reproducible macOS layout helper. The component/SQL samples are readable; class labels and the full sequence need larger/split final placement. See LAYOUT_REVIEW.md; final-format QA remains pending.

## Verification and limits

Local cleanup checks: all three Mermaid sources parse; sequence export preserves every participant, message, note and alternative; its source hash is embedded in the SVG; all new Python syntax checks pass; both JavaScript render-helper syntax and the Swift PDF generation/readback pass. All four PDF pages and the standalone sequence image were visually inspected. Local Markdown file targets resolve when checked against the complete checkout plus these changes; no personal Library links remain in the source register. Diff/whitespace and original-source preservation checks pass.

These are documentation-only corrections; no application tests or database/calculation probes were rerun for unchanged application code. The previous 69 Django tests and 17 SQL cases remain dated verification results; CI run 41327877627 applies to published e8bc8ca, not this uncommitted cleanup. No model/migration/settings/SQL/application file or development database was modified. Existing architecture/class assets, original evidence JSON and all three Mermaid sources remain byte-identical.

## Approval boundary and next checkpoint

Corrections are prepared locally for owner review. **No cleanup commit/push, merge or issue #13 closure is authorized yet.** After approval, commit and push this documentation cleanup to the existing PR #23 branch, verify its new-head CI and request/confirm merge approval separately. Do not recreate the PR or repeat issue #3 closure.

Organizational inputs remain pending: registered team name/four-person roster, factual individual contributions, presentation responsibilities, submission logistics beyond the already stated printed-report requirement. The report is a working checkpoint draft, not a final submission.
