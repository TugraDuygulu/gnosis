# Grade CSV preview · proposed Sprint 2 contract

23 November 2026 (Europe/Istanbul). Tuğra owns [#42](https://github.com/TugraDuygulu/gnosis/issues/42);
Emir reviews. This draft implements the read-only increment on
`codex/42-csv-preview`, based on main `2d50e56`. The PR records the exact
revision, checks and review state. Tuğra retains merge approval.

## Input

Pass an authenticated user, one gradebook offering PK, and a binary upload
positioned at byte zero to `core.grade_import.preview_grades`. The preview
checks the active, unambiguous instructor role and current offering assignment
before reading the stream. No other role is included in the proposed CSV pilot.
Look up existing enrollments irrespective of status, as in the native editor.
The upload contains one target cell per record. Example using fictional IDs:

```csv
student_number,assessment_id,score
0007,12,0
0007,19,
```

Require this exact header order. Match the student's existing number literally
(including leading zeros and case); assessment ID is its positive signed-64-bit
database PK in canonical decimal form. Names can collide. Resolve both inside
the selected offering. The UI should show instructors the assessment ID/name
pairs for that offering. IDs are installation-specific.

UTF-8 with optional BOM, comma separator, standard double-quote escaping,
LF or CRLF. Python's strict CSV reader accepts quoted fields and reports
structural parse failures. No whitespace trimming or ignored blank records.
At least one data record. Proposed limits are 100 records plus header and
1,000,000 raw bytes including BOM/newlines. The byte bound is checked before
decoding. The CSV reader also enforces its standard per-field limit. These
are pilot bounds tested at their edges, pending team acceptance and upload
handling checks in #43.

An empty score keeps the current cell, including an absent or NULL grade.
Zero proposes an assessed zero. An equal numeric value is a no-op. A plain
signed or unsigned decimal with a dot separator is validated using Django's
grade-editor constraints (7 digits, up to 2 decimal places, inclusive zero to
assessment maximum). No rounding, exponents, grouping, nonfinite values or
CSV clearing. Repeating a student across different assessments is valid.
Repeating a target cell flags the later row, even when its value matches.

## Output and integration

`Preview.rows` contains valid rows in file order, with first physical line,
student number, enrollment/assessment IDs, previous and proposed Decimal
scores (or None), and action `set` or `keep`. For a blank proposal, display
the previous score as the resulting value. `Preview.errors` contains
`(line, field, code)` objects. File-wide problems can have no line. Invalid
header, encoding, CSV syntax and bounds errors stop the file. Recoverable
row errors include bad width, duplicate, unknown student, invalid/foreign
assessment, invalid decimal and Django decimal-validation codes. The whole
preview is ineligible for confirmation if any error exists. Distinguish
file errors from counts of distinct invalid lines. A numeric zero must be
formatted explicitly. Escape user-controlled content when rendering.

## Handoff and remaining decisions

- Omar (#43): use this service directly for read-only preview. Count set/keep
  rows by action. Use field and code to render errors. No mutation endpoint
  or confirmation credential exists in this increment.
- Emir (#44): test another instructor, ambiguous/disabled accounts, foreign
  IDs, blank/zero/equal values, partial-invalid files and unchanged audit state.
- Ramazan (#45): resolve fictional assessment IDs from the disposable fixture
  database; include a padded student number, blank, zero and late invalid row.
- By Wednesday, review the long format, exact limits, assessment ID discovery
  and assigned-instructor scope with the team. Existing single-enrollment
  editing also supports other authorized roles; CSV access for those roles
  needs an explicit decision.

For Friday's confirmation, bind a signed expiring preview to the actor, offering,
contract version, original file digest and normalized targets. Capture student
number to enrollment mappings, enrollment status, assessment IDs/configuration,
and grade identities and scores (including absence versus NULL). The existing
`grade_editor.snapshot` supplies much of that state per enrollment. Re-resolve
assignment and identities, verify integrity and revisions under transaction
locks, reject stale or replayed confirmations, then write grades and matching
history together. Reuse grade-history and optimistic update semantics from the
editor. Never send unsigned client rows directly to a writer. Token design,
replay protection and concurrency tests remain open.

Local verification uses the pinned dependencies and Django's disposable test
database. See the draft PR for commands and results. No UI, browser acceptance,
human approval or integration is claimed here.
