# Grade CSV Import Guide (Instructor Reference & Acceptance Fixtures)

This guide explains how an assigned instructor prepares a valid grade CSV file,
reviews the preview, confirms or cancels an import, and recovers from rejected
or stale uploads. All rules match the backend contract in `#42`
(`core.grade_import`, merged to `main` in PR `#69`).

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

1. **Prepare the file:** On the grade book, select **Import from CSV**. Next to
   each assessment, **Download CSV** gives a template that already lists every
   student with a blank score; fill in only the scores you want to set. A class
   with more than 100 rows gets the template in parts (`Students 1–100`,
   `Students 101–…`): import each part on its own. If you use Excel:
   - Opening a CSV in Excel drops leading zeros (`00202601` becomes `202601`,
     reported as an unknown student). Open it with **Data → From Text/CSV** and
     keep `student_number` as text, or edit the file in a text editor.
   - Before uploading, open the saved file in a text editor such as Notepad:
     columns must be separated by commas and decimals must use a dot. With
     Turkish regional settings Excel saves semicolons and decimal commas, and
     the import rejects them.
2. **Upload & Preview:** Choose the file and select **Preview import**. **No
   database changes happen during preview.**
3. **Inspect the preview:**
   - If **any** file-level or row-level error exists, the page lists the lines
     to fix and shows no **Import** button, so nothing can be saved.
   - Otherwise check each row's **Current score**, **Score in file** and
     **Result** (**New grade**, **Changes**, **No change, same score** or
     **No change, blank keeps it**). A blank cell shows as **Blank**; `0` shows
     as `0.00` marked "a real 0".
4. **Confirm or Cancel:**
   - **No-op / all-unchanged file:** If every row is blank or already matches the
     stored score (`0` grades to change), the UI displays **"Nothing to import"**
     and offers **no confirmation button** (the underlying service still supports
     single-use zero-change confirmation tokens, but the instructor screen
     prevents submitting a no-op import).
   - **Confirm:** When at least one grade changes, select **Import N grades**.
     The page sends the exact file you previewed, so you don't choose it again.
     A preview can be confirmed once, within **2 hours**. All changes, the
     receipt, and `CSV import` history entries commit atomically, or everything
     rolls back together.
   - **Cancel:** Returns to the grade book without saving and leaves all grades
     and history untouched.

## Recovering from rejected, stale, or failed imports

| Problem | Why it happened | How to recover |
| --- | --- | --- |
| **File-level error** (wrong header, semicolons, encoding, CSV syntax, empty file, >100 rows, >1 MB) | File structure or limits violated before row validation. | Start from the page's template, or save as UTF-8 CSV with the exact header `student_number,assessment_id,score`, commas between columns and dots for decimals. Remove blank lines and extra spaces, split files over 100 rows, and preview again. |
| **Row-level error** (bad column count, duplicate cell, unknown student, foreign/invalid `assessment_id`, invalid decimal, negative or above-max score) | One or more rows failed validation; the entire file is blocked from confirmation. | Fix the listed lines using the offering's roster and the assessment IDs on the upload page, save the file, and preview it again. |
| **"Nothing was saved. Grades or class settings changed after your preview."** | Another edit (native editor, Admin, or another import) changed the offering, enrollment, assessment, or a grade on an affected enrollment after your preview. | The page already shows a fresh preview with the current grades. Check it (**Open the grade book** shows the newer edit), then confirm again, or fix your CSV and preview it. |
| **"Nothing was saved. The preview was more than two hours old."** | The preview is older than 2 hours. | The page already shows a new preview of the same file: check it and confirm again. |
| **"Nothing was saved. The confirmation didn’t match the file you previewed."** | The submitted file or confirmation changed, or your password changed after the preview. | Choose the file again and preview it. |
| **"Nothing was saved this time. This preview was already confirmed…"** | This preview was already confirmed, for example from another tab or after going Back. | Check the grade book and Grade-change history before importing again. |
| **Permission denied (`403`)** | Account is not an active instructor assigned to this offering. | Confirm your offering assignment with a coordinator. |
| **"Nothing was saved. Another save was in progress."** | Another save was writing at the same moment. | The page already shows a fresh preview: check it and confirm again. |

---

## Fictional paired acceptance fixtures (`#45`)

All fixtures use **fictional data only** and are designed for a **separate
disposable database** seeded with `seed_pilot` (never reset an existing working
database).

### Disposable setup before testing

1. **Database setup:** On a fresh disposable database, run `migrate`,
   `seed_pilot` and `createsuperuser`. `seed_pilot` creates no sign-in
   accounts.
2. **Coordinator steps:**
   - As the superuser, create a coordinator as in step 1 of
     [the academic roles walkthrough](academic_roles.md#fictional-walkthrough):
     in Django Admin, add the group `Gnosis Coordinators` and a non-staff user
     in it. Sign out and sign in as that **Coordinator**.
   - In **Academic management → Instructor records**, select **Create login**
     for `Fictional Pilot Instructor` with the username `inst_pilot`.
     `seed_pilot` already assigns this instructor to `PILOT311`
     (`Fall 2026, section PILOT`) and `PILOT321`.
   - Use **Register student** to add a fictional student with a **Turkish name**
     and **leading-zero student number**: Full name `Çağrı Şahin`, student
     number `00202601`, program `PILOT`. On the student's page, select
     **Enroll in a course offering** and choose `PILOT311`.
3. **Switch to the assigned instructor:** Sign out of the coordinator account
   and sign in as the assigned **Instructor** (`inst_pilot`) for all grade entry
   and CSV import steps below:
   - Enter initial `PILOT311` grades for `00202601` via the native grade editor:
     Midterm `80.00 / 100.00`, Project `40.00 / 50.00`.
   - Note `PILOT001` (`Pilot Student A`) Midterm in `PILOT311` (`90.00` from
     `seed_pilot`) as the unrelated blank-no-change control before import.
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
| 4 | `PILOT001` (`Pilot Student A`) | Midterm (`1`, max 100) | `90.00` | *(blank)* | `keep` | `90.00` (unchanged) | **No entry written** |

- **Expected outcome impact (`00202601` in `PILOT311`):** Because Project is now
  a recorded `0.00` (not missing), evidence coverage stays `100%` and LO/PO
  scores recalculate using Midterm `85/100` (`85%`) and Project `0/50` (`0%`):
  LO1 `51.00%`, LO2 `24.29%`, PO2 `42.10%` and PO3 `24.29%`, all graded. Before
  the import all four are `80.00%`.

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
- **Stale preview:** Save a one-row file, `stale.csv`, with the header and
  `00202601,1,88`, and preview it (Midterm `85.00` → `88.00` after the valid
  import). Before confirming, open a second tab, change `00202601`'s Midterm
  to `91` in the native grade editor and save. Return to the first tab and
  select **Import 1 grade** → "Nothing was saved. Grades or class settings
  changed after your preview." with a fresh preview (`91.00` current, `88.00`
  in file). The native `91.00` and its history entry are kept, and no
  `CSV import` entry is added.

---

## Independent browser walkthrough evidence (`#43` UI)

- **Verifier:** Ramazan (`@RA2127`)
- **Date:** 28 November 2026 (Europe/Istanbul)
- **Tested revision:** PR `#70` (`feature/43-import-ui` @ `38de715`, built on `#69` / `codex/42-csv-preview`)
- **Environment:** Windows 11 (`http://127.0.0.1:8000/`), separate disposable SQLite database (`migrate` + `seed_pilot`), fictional accounts/data only
- **Browser & viewports:** Desktop Microsoft Edge + mobile emulation (`390px` width)
- **Test setup:** Assigned instructor `inst_pilot` on `PILOT311` (`Fall 2026, section PILOT`); fictional student `Çağrı Şahin` (`00202601`) initially graded `80.00 / 100.00` (Midterm) and `40.00 / 50.00` (Project); `PILOT001` (`Pilot Student A`) kept as blank-no-change control.

### Actual results

1. **Before state (baseline):** Confirmed `00202601` (`Çağrı Şahin`) Midterm `80.00`, Project `40.00`, `100%` outcome coverage (`80.00%` LO/PO baseline), `PILOT001` existing Midterm score, and no `CSV import` entries in Grade-change history.
2. **Invalid import (`rejected.csv`):** Preview blocked confirmation (no Import button shown) and flagged all three errors (above-max score `75 > 50`, duplicate target cell, unknown student `99999999`). Returning to the gradebook confirmed row 1 (`90`) did **not** partially save (`00202601` stayed `80.00`), unrelated students/offerings and coverage stayed unchanged, and no `CSV import` history entry was written.
3. **Cancelled import (`valid.csv`):** Preview displayed `Çağrı Şahin`, `0.00` (recorded zero), and `PILOT001` blank-no-change without modifying the database. Clicking **Cancel** returned to the gradebook with all grades, outcomes, and history unchanged.
4. **Valid import (`valid.csv`):** Confirming **Import 2 grades** saved `00202601` Midterm `80.00 -> 85.00` and Project `40.00 -> 0.00` (recorded zero), while `PILOT001` remained unchanged. Grade-change history recorded exactly **2** `CSV import` entries for `00202601` and **0** entries for `PILOT001`. Outcomes recalculated for `00202601` while keeping `100%` coverage (recorded zero distinct from missing).
5. **Stale preview (`stale.csv`):** Previewed `00202601` Midterm `88` in tab 1, then saved Midterm `91` in the native editor in tab 2. Confirming tab 1 returned `"Nothing was saved..."`, retained `91.00` and its native-editor history entry, wrote no `CSV import` entry, and displayed a fresh preview reflecting `91.00`.
6. **Mobile (`390px`) & defects:** Verified upload and preview layouts at `390px` width with no horizontal overflow and readable card-style preview rows. No blocking defects observed.

### Second verifier

- **Verifier:** Omar (`@OmerV7`), 28 November 2026 (Europe/Istanbul)
- **Tested revision:** `main` @ `5f181ac` (#69, #70 and #71 merged) with this guide
- **Environment:** Windows 11, Microsoft Edge 156 scripted with Playwright at 1366×800 and 390×844 (emulated), fresh disposable SQLite database (`migrate`, `seed_pilot`, `createsuperuser`), fictional accounts only
- **Result:** Results 1–6 above reproduced with the same values, and the expected outcomes matched. Corrections from this run are in the #72 review.
