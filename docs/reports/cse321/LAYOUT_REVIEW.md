# Representative page-layout review — 1 November 2026

This is a limited working-layout check, **not final submission QA**. The official wording is “125% visible” for illustrations and code (Report Format 2 p.1; Guidelines p.16). Neither source specifies a font-size minimum, paper size, screen DPI or final authoring format. A 125% viewing check is a practical review method here, not an invented institutional interpretation or instructor approval.

## Actual sample and observations

[Four-page sample PDF](evidence/readability-sample.pdf) uses A4, 36-point margins and explicit page orientations. It is labeled as a layout sample on every page. All four pages were rasterized at 1.25 pixels per PDF point (90 dpi, i.e. 125% relative to 72-point page coordinates) with macOS PDFKit and visually inspected. This establishes the stated digital sample, not an actual-size monitor calibration, printed-copy inspection or approval of the final report.

| Page | Material / placement | Observation at sample scale | Consequence |
| --- | --- | --- | --- |
| 1 | Existing component PNG, landscape A4 | Labels and dependency arrows readable; whole figure inside the page area | Viable representative layout; confirm again in final format |
| 2 | Existing grading-class PNG, portrait A4 | Class names/members visible, but small dependency labels and multiplicities are marginal | Do not mark final readability complete; use larger placement or split framework/form/Admin behavior from model associations |
| 3 | Full grade-workflow PNG, portrait A4 | No clipping, but full-height fitting makes messages/branch labels too small for comfortable report reading | Use split workflow figures or a suitably larger page; preserve branch/transaction continuity, not a shrunken full-page body figure |
| 4 | Exact original Query 1 SQL, 10-point monospaced text, landscape A4 | Complete lines and indentation readable, no clipped statement | Viable sample for this query only; check Queries 2/3 separately in final pagination |

The sequence's standalone SVG/PNG is readable at its natural size and preserves all five participants, 28 parsed events (messages, notes and branch boundaries), nested alternatives, rollback/commit and subsequent read calculation. It is a **custom source-derived SVG layout**, not a direct Mermaid-renderer export. The existing architecture/class SVGs remain unchanged sibling DOT layouts. No new classes or application components were added.

## Reproduction

Sequence exports use the existing optional renderer dependencies. From the repository root:

```sh
python3 docs/reports/cse321/tools/export_workflow.py
node docs/reports/cse321/tools/render_diagrams.mjs /tmp/gnosis-diagram-runtime
swift -module-cache-path /tmp/gnosis-swift-cache docs/reports/cse321/tools/build_layout_sample.swift . /tmp/gnosis-readability-sample.pdf
```

The Swift helper requires macOS AppKit/PDFKit; it creates the PDF and sibling `layout-page-N-125.png` inspection images at the chosen output location. These are documentation-only tools, not application dependencies. See the workspace README for optional Node dependency versions. The sample is derived from the exact diagrams and repository Query 1, not invented SQL or a private database.

## Still pending

Choose the actual submission format and permitted page sizes/orientations; resolve the class/sequence density in that layout; inspect all focused ERDs, SQL excerpts, captions and tables at the required visibility; verify all six sections together and inspect the printed output. Do not infer full-report compliance from these four sample pages. No final report PDF/DOCX is produced by this review.
