# Grade CSV preview and confirmation · proposed Sprint 2 contract

Updated 25 November 2026 (Europe/Istanbul). Tuğra owns [#42](https://github.com/TugraDuygulu/gnosis/issues/42);
Emir reviews. This draft implements the backend preview and confirmation on
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

## Confirmation interface for #43

Keep the selected file available in the browser until the instructor confirms.
After an error-free preview, return its opaque `confirmation_token` to that
instructor. Invalid previews have a None token. On a separate, authenticated,
CSRF-protected POST, send the token and the same file bytes. Start the binary
stream at byte zero on each call. Take the integer offering ID from the route
and the actor from the authenticated request.

```python
from core.grade_import import confirm_grades

changed = confirm_grades(user=request.user, offering_id=offering_id,
                         upload=request.FILES["file"], token=request.POST["token"])
```

The return value counts committed grade changes. Zero is a successful
all-unchanged import and consumes the token. Cancel by discarding the token.
The signed payload binds actor, offering, a random nonce, original byte digest
and preview-state digest. The two-hour lifetime matches the native editor.
Signing uses a CSV-specific salt and the actor's Django session auth hash.
Treat tokens as private form data and configure a private Django secret key
for deployment. No server-side file storage is required.

**Errors and UI behavior**

- `PermissionDenied`: show the application's forbidden response. Account role,
  activity and current assignment are checked again against database records.
- `ValidationError` codes `invalid_token`, `expired`, `stale`, and `replayed`:
  show the code's reason and offer a fresh preview. A replay can follow an
  already successful confirmation. Reload the gradebook/history to inspect it.
- Persistence, audit and database-lock failures roll back the transaction.
  Return a recoverable failure to the user. After contention or a lost response,
  refresh the gradebook and preview before offering another confirmation.

## Transaction and concurrency boundaries

Migration 0011 adds a receipt with a unique random nonce and confirmation
timestamp. Claiming it is the first write of the transaction; a rejected or
failed import rolls it back. Current validators then reparse the file. The
revision includes offering identity/configuration, the target student's literal
number, enrollment identity/status, assessment name/maximum/weight and grade
identity/value. Missing and NULL have distinct revisions. The latest supported
grade-history entry for each affected enrollment catches audited score changes
followed by a restoration. This conservative rule can invalidate a preview
after a different assessment on the same enrollment is edited.

The native editor and CSV service share the grade writer, conditional update
and audit routine. Each changed grade gets one event with source `CSV import`.
Blanks and equal values produce zero grade or history writes. The receipt,
all grades and all events commit or roll back together.

SQLite serializes writers after the receipt insert. Lock contention can abort
a request. The checks exercise sequential stale/replay cases and injected
failure in SQLite. Simultaneous requests and other database backends still
need independent testing. Snapshot comparison cannot detect an unaudited
change restored to its exact previous state. Receipt cleanup is outside this
increment; retain receipts for at least the full token lifetime.

## Team handoff

- Omar (#43): retain the file for the confirm POST, display preview errors and
  counts, and wire the responses above. The service is available on draft #69.
- Emir (#44): verify independent success, stale and rollback controls, access
  changes, concurrent attempts and the no-op replay case against fictional data.
- Ramazan (#45): resolve assessment IDs from the disposable fixture database.
  Verify a changed score, zero and blank through gradebook, history and outcomes.
- Tuğra/Emir: review the provisional CSV format and bounds, assigned-instructor
  scope, two-hour lifetime, single-use receipt and same-file POST. Tuğra owns
  final integration approval. Browser evidence and independent team review are
  pending.
