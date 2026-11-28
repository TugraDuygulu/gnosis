# Grade CSV Import Guide (Instructor Reference & Acceptance Fixtures)

This guide explains how an assigned instructor prepares a valid grade CSV file,
reviews the preview, confirms or cancels an import, and recovers from rejected
or stale uploads. All rules match the backend contract in `#42`
(`core.grade_import`, branch `codex/42-csv-preview` / PR `#69`).

## Who can import grades

- Only an active, unambiguous **Instructor** currently assigned to the target
  course offering can preview or confirm a CSV import for that offering.
- Existing enrollments in the offering are matched regardless of enrollment
  status, matching the native grade editor.

## Exact CSV format and limits

1. **Header (exact order required):**
   ```csv
   student_number,assessment_id,score
   ```
2. **Encoding and syntax:**
   - UTF-8 (optional BOM), comma (`,`) separator, standard double-quote
     escaping, LF or CRLF line endings.
   - Strict CSV parsing: **no automatic whitespace trimming** and **no ignored
     blank lines**.
3. **Upload bounds:**
   - At least **1** data row and at most **100** data rows (plus the header).
   - Maximum **1,000,000 raw bytes** (including BOM and line endings).
4. **Column rules:**
   - `student_number`: Must match the student's existing number literally,
     including **leading zeros** and letter case. Student names are not in the
     CSV because names can collide; names (including Turkish characters such as
     `Ç, Ğ, İ, Ö, Ş, Ü`) are displayed from the student's database record during
     preview.
   - `assessment_id`: Positive decimal database ID of an assessment belonging
     to the selected course offering. **Assessment IDs are installation-specific**
     — always read the offering's ID/name pairs from the upload screen before
     preparing your file.
   - `score`: Plain signed or unsigned decimal using a dot (`.`) separator, up
     to 7 digits total and at most 2 decimal places, from `0` through the
     assessment's maximum score (inclusive). No rounding, scientific notation,
     thousands separators, or non-finite values.

## Blank, zero, and overwrite semantics

| `score` cell value | Behavior on confirm | History (`Grade-change history`) |
| --- | --- | --- |
| **Empty** (e.g. `PILOT001,1,`) | **Keep current value** (no change; preserves existing score, ungraded, or NULL). CSV import **does not clear** grades. | No entry written |
| **`0`** (e.g. `00202601,2,0`) | **Set recorded zero** (`0.00`). Distinct from ungraded/missing. | One `CSV import` entry if value changed |
| **Equal numeric value** | **No-op** (keeps current score). | No entry written |
| **New valid score** | **Overwrites** the assessment cell for that enrollment. | One `CSV import` entry with actor, UTC time, old/new value |

- Repeating the same `student_number` across **different** assessments is valid.
- Repeating the exact same `(student_number, assessment_id)` target cell in the
  same file is rejected as a **duplicate**, even if both rows have the same
  score.

## Preview, confirm, and cancel workflow

1. **Upload & Preview:** Select the CSV file on the offering's grade import page
   and run **Preview**. **No database changes happen during preview.**
2. **Inspect the preview:**
   - If **any** file-level or row-level error exists, confirmation is disabled
     (no token is issued) and nothing can be saved.
   - If the preview is error-free, verify each row's previous value, proposed
     value, and action (`set` or `keep`). Note that a blank cell displays the
     previous value as the resulting value.
3. **Confirm or Cancel:**
   - **No-op / all-unchanged file:** If every row is blank or already matches the
     stored score (`0` grades to change), the UI displays **"Nothing to import"**
     and offers **no confirmation button** (the underlying service still supports
     single-use zero-change confirmation tokens, but the instructor screen
     prevents submitting a no-op import).
   - **Confirm:** When at least one grade changes, click **Import N grades** to
     submit the single-use `confirmation_token` (valid for **2 hours**) with the
     **exact same file bytes**. All changes, the receipt, and `CSV import`
     history entries commit atomically, or everything rolls back together.
   - **Cancel:** Returns to the grade book without saving and leaves all grades
     and history untouched.

## Recovering from rejected, stale, or failed imports

| Problem | Why it happened | How to recover |
| --- | --- | --- |
| **File-level error** (invalid header, encoding, CSV syntax, empty file, >100 rows, >1 MB) | File structure or limits violated before row validation. | Save as UTF-8 CSV with exact header `student_number,assessment_id,score`, remove blank lines/extra spaces, split if >100 rows, and re-preview. |
| **Row-level error** (bad column count, duplicate cell, unknown student, foreign/invalid `assessment_id`, invalid decimal, negative or above-max score) | One or more rows failed validation; the entire file is blocked from confirmation. | Fix the reported line numbers using the offering's roster and assessment ID list, save the file, and run a fresh preview. |
| **`stale` on confirm** | Another edit (native editor, Admin, or another import) changed the offering, enrollment, assessment, or a grade on an affected enrollment after your preview. | Reload the gradebook/history to review the newer edit, adjust your CSV if needed, and run a **fresh preview**. |
| **`expired` or `invalid_token`** | Preview is older than 2 hours, the file bytes changed, or the session changed. | Upload the file again to generate a fresh preview and token. |
| **`replayed`** | This preview token was already used (possibly by an earlier successful confirmation). | Reload the gradebook and Grade-change history first to verify whether the import already applied before re-uploading. |
| **Permission denied (`403`)** | Account is not an active instructor assigned to this offering. | Confirm your offering assignment with a coordinator. |
| **Lock / save failure** | Concurrent write contention rolled back the transaction. | Refresh the gradebook/history and run a fresh preview before confirming again. |

---

## Fictional paired acceptance fixtures (`#45`)

All fixtures use **fictional data only** and are designed for a **separate
disposable database** seeded with `seed_pilot` (never reset an existing working
database).

### Disposable setup before testing

1. **Database setup:** On a fresh disposable database, run `migrate` and
   `seed_pilot`.
2. **Coordinator steps:** Sign in as a **Coordinator** to set up the pilot
   roster and assignment:
   - Verify or assign an active instructor account (for example `inst_pilot`) to
     `PILOT311` (`Fall 2026, section PILOT`).
   - Create a fictional student with a **Turkish name** and **leading-zero
     student number**: Full name `Çağrı Şahin`, student number `00202601`,
     program `PILOT`, and enroll them in `PILOT311`.
3. **Switch to the assigned instructor:** Sign out of the coordinator account
   and sign in as the assigned **Instructor** (`inst_pilot`) for all grade entry
   and CSV import steps below:
   - Enter initial `PILOT311` grades for `00202601` via the native grade editor:
     Midterm `80.00 / 100.00`, Project `40.00 / 50.00`.
   - Note existing `PILOT001` (`Pilot Student A`) Midterm grade in `PILOT311` as
     the unrelated blank-no-change control before import.
   - Open **Import from CSV** on the `PILOT311` grade book to read the actual
     `assessment_id` values for Midterm (max `100`) and Project (max `50`). The
     fixture files below use `1` (Midterm) and `2` (Project) as example IDs —
     replace them with your disposable database's actual IDs if they differ.

### 1. Valid paired fixture (`docs/fixtures/grade_csv/valid_paired_example.csv`)

```csv
student_number,assessment_id,score
00202601,1,85
00202601,2,0
PILOT001,1,
```

**Expected cells and audit entries after confirmation:**

| Line | Student | Assessment | Before | Proposed | Action | Expected after confirm | Expected `Grade-change history` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | `00202601` (`Çağrı Şahin`) | Midterm (`1`, max 100) | `80.00` | `85` | `set` | `85.00` | 1 entry: `Change`, `80.00 -> 85.00`, source `CSV import` |
| 3 | `00202601` (`Çağrı Şahin`) | Project (`2`, max 50) | `40.00` | `0` | `set` | `0.00` (recorded zero) | 1 entry: `Change`, `40.00 -> 0.00`, source `CSV import` |
| 4 | `PILOT001` (`Pilot Student A`) | Midterm (`1`, max 100) | Existing value | *(blank)* | `keep` | Unchanged | **No entry written** |

- **Expected outcome impact (`00202601` in `PILOT311`):** Because Project is now
  a recorded `0.00` (not missing), evidence coverage stays `100%` and LO/PO
  scores recalculate using Midterm `85/100` (`85%`) and Project `0/50` (`0%`).

### 2. Rejected paired fixture (`docs/fixtures/grade_csv/rejected_paired_example.csv`)

```csv
student_number,assessment_id,score
00202601,1,90
00202601,2,75
00202601,1,85
99999999,1,70
```

**Expected preview errors and post-rejection state:**

| Line | Field | Expected error reason |
| --- | --- | --- |
| 2 | — | Valid row (`00202601` Midterm `90`) — **must NOT partially save** |
| 3 | `score` | Above assessment maximum (`75 > 50`) |
| 4 | `student_number` / target cell | Duplicate `(00202601, 1)` target cell |
| 5 | `student_number` | Unknown student (`99999999` not enrolled in offering) |

- **Expected state:** Confirmation is blocked (`confirmation_token` is `None`).
  Line 2 (`90`) is **not** saved; `00202601` keeps its previous Midterm score,
  all unrelated student/offering records and coverage remain unchanged, and
  **no** `CSV import` history entry appears.

### 3. Cancelled and stale preview checks

- **Cancelled import:** Preview `valid_paired_example.csv` (with a new valid
  score), then click **Cancel** without confirming → gradebook, outcomes, and
  history remain unchanged.
- **Stale preview:** Preview a valid CSV for `00202601`. Before confirming, open
  a second tab and edit `00202601`'s grade in the native editor and save. Return
  to the first tab and click **Confirm** → rejected as `stale`; the newer native
  editor score and its history entry are retained, and no `CSV import` entry is
  added.

---

## Independent browser walkthrough evidence (`#43` UI)

- **Verifier:** Ramazan (`@RA2127`)
- **Date:** 28 November 2026 (Europe/Istanbul)
- **Tested revision:** PR `#70` (`feature/43-import-ui` @ `38de715`, built on `#69` / `codex/42-csv-preview`)
- **Environment:** Windows 11 (`http://127.0.0.1:8000/`), separate disposable SQLite database (`migrate` + `seed_pilot`), fictional accounts/data only
- **Browser & viewports:** Desktop [Chrome / Edge] + mobile emulation (`390px` width)
- **Test setup:** Assigned instructor `inst_pilot` on `PILOT311` (`Fall 2026, section PILOT`); fictional student `Çağrı Şahin` (`00202601`) initially graded `80.00 / 100.00` (Midterm) and `40.00 / 50.00` (Project); `PILOT001` (`Pilot Student A`) kept as blank-no-change control.

### Actual results

1. **Before state (baseline):** Confirmed `00202601` (`Çağrı Şahin`) Midterm `80.00`, Project `40.00`, `100%` outcome coverage (`80.00%` LO/PO baseline), `PILOT001` existing Midterm score, and no `CSV import` entries in Grade-change history.
2. **Invalid import (`rejected.csv`):** Preview blocked confirmation (no Import button shown) and flagged all three errors (above-max score `75 > 50`, duplicate target cell, unknown student `99999999`). Returning to the gradebook confirmed row 1 (`90`) did **not** partially save (`00202601` stayed `80.00`), unrelated students/offerings and coverage stayed unchanged, and no `CSV import` history entry was written.
3. **Cancelled import (`valid.csv`):** Preview displayed `Çağrı Şahin`, `0.00` (recorded zero), and `PILOT001` blank-no-change without modifying the database. Clicking **Cancel** returned to the gradebook with all grades, outcomes, and history unchanged.
4. **Valid import (`valid.csv`):** Confirming **Import 2 grades** saved `00202601` Midterm `80.00 -> 85.00` and Project `40.00 -> 0.00` (recorded zero), while `PILOT001` remained unchanged. Grade-change history recorded exactly **2** `CSV import` entries for `00202601` and **0** entries for `PILOT001`. Outcomes recalculated for `00202601` while keeping `100%` coverage (recorded zero distinct from missing).
5. **Stale preview (`stale.csv`):** Previewed `00202601` Midterm `88` in tab 1, then saved Midterm `91` in the native editor in tab 2. Confirming tab 1 returned `"Nothing was saved..."`, retained `91.00` and its native-editor history entry, wrote no `CSV import` entry, and displayed a fresh preview reflecting `91.00`.
6. **Mobile (`390px`) & defects:** Verified upload and preview layouts at `390px` width with no horizontal overflow and readable card-style preview rows. No blocking defects observed.
