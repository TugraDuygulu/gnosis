---
# gstack: design-md-format=spec
name: Gnosis
description: A calm academic workspace in navy and paper white where every result says how complete its evidence is and what to do next.
colors:
  primary: "#1F3A68"
  primary-hover: "#172C50"
  primary-soft: "#E8EDF6"
  on-primary: "#FFFFFF"
  sidebar: "#13254A"
  sidebar-text: "#C5D0E4"
  accent: "#C9A44C"
  background: "#F4F5F8"
  surface: "#FFFFFF"
  subtle: "#F8F9FB"
  border: "#E1E5EC"
  border-strong: "#C7CFDB"
  text: "#121C2E"
  text-muted: "#586276"
  text-faint: "#8F9AAD"
  alert: "#8A5A0B"
  alert-soft: "#FBF3E2"
  error: "#A12C2C"
  error-soft: "#FBEAEA"
  score-0: "#A63D3D"
  score-40: "#C2652A"
  score-60: "#C08A2B"
  score-75: "#7D8B35"
  score-85: "#3E7B55"
  score-100: "#2D6A4F"
typography:
  display:
    fontFamily: Source Serif 4
    fontWeight: 700
    fontSize: 2rem
    letterSpacing: -0.01em
  heading:
    fontFamily: Source Serif 4
    fontWeight: 700
    fontSize: 1.1875rem
  body:
    fontFamily: Source Sans 3
    fontSize: 1rem
    lineHeight: 1.5
  label:
    fontFamily: Source Sans 3
    fontWeight: 700
    fontSize: 0.8125rem
  mono:
    fontFamily: Source Sans 3
    fontFeature: tnum
rounded:
  sm: 6px
  md: 9px
  lg: 12px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 48px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-ghost:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border-strong}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
  input:
    borderColor: "{colors.border-strong}"
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
  card:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border}"
    rounded: "{rounded.lg}"
  nav-link:
    textColor: "{colors.sidebar-text}"
  nav-link-active:
    textColor: "#FFFFFF"
    indicatorColor: "{colors.accent}"
  status-fully-graded:
    backgroundColor: "{colors.primary-soft}"
    textColor: "{colors.primary-hover}"
    rounded: "{rounded.full}"
---

# Gnosis

## Overview

**Creative North Star:** A university office tool that reads like a well-kept faculty report: navy, paper white, serif headings. Each outcome shows three things, its score, how complete its evidence is and what to do next.
**Product context:** Server-rendered Django staff application for a university department. Instructors and accreditation coordinators register students, enter assessment grades and read Learning Outcome (LO) and Program Outcome (PO) achievement with evidence coverage. Peers: Anthology Outcomes, Blackboard Outcomes, LMS gradebooks. Built for the CSE321 team project; demoed on a classroom projector.
**Mode per surface:** Operate (student and course lists, roster, grade editor, forms). Read (student outcome profile, course evidence, grade history).
**Reference sites:** https://www.anthology.com/solutions/institutional-and-learning-effectiveness/outcomes , https://www.blackboard.com/blog/how-your-feedback-shaped-the-new-gradebook-grid-view , https://peer.asee.org/19074 , https://trends.daisyui.com/trend/data-dense-utilitarian-ui/
**Key characteristics:**
- Navy sidebar with a gold active marker; light content area; one white panel per task.
- Achievement percentages are coloured by value on a muted academic scale (brick, burnt orange, ochre, olive, forest green).
- Grading completeness is a separate, labelled status pill, never mixed with the score colour.
- Missing grades become a concrete next step ("Lab grade missing → Enter grade"), and a missing grade is never shown as zero.
- Every result can be opened to show where it comes from.

## Colors

**Strategy:** Full palette with a strict split. Navy (`primary`) is the interface colour: buttons, links, navigation, completeness pills. The `score-*` stops are reserved for achievement values only (bars, chart columns, the percentage text), interpolated by `core/templatetags/gnosis_ui.py` (`score_fill`, `score_text`) and mirrored in `gnosis.js` for the live grade preview. `alert` (ochre-brown) marks things that need attention, such as missing grades. `error` is for form validation only. `accent` gold appears only in the brand mark and the active navigation marker.
**Light or dark:** Light. Staff use it in daylight offices and it is demoed on a classroom projector; dark text on a light ground survives both.
Neutrals are cool greys derived from the navy. Hatching (`repeating-linear-gradient` in `--hatch`) marks configured-but-ungraded evidence; a dashed border marks "not measured by any course".

## Typography

Source Serif 4 (headings and big figures) and Source Sans 3 (everything else) are one Adobe family designed together, so the academic serif headings sit naturally on a highly legible sans. Numbers use Source Sans 3 tabular figures so percentages align in tables. Loaded from Google Fonts in `core/templates/core/base.html`; self-host the woff2 files under `core/static/core/fonts/` if the demo network is unreliable.
Scale: page title 32px serif, panel heading 19px serif, body 16px, table and secondary text 13.5-15px, labels 13px bold.

## Layout

Two-column shell: 248px navy sidebar (Students, Courses, Register student when permitted, Django Admin, user and log out) and a content column with a sticky search bar. Content max width 1260px with 36px side padding (16px on phones, where the sidebar becomes a top bar). Pages start with breadcrumbs, then a header (avatar or title, a one-line plain-language summary, actions on the right). Detail pages use a main column plus a 320px side column for "Needs attention" and course progress. Collapses to one column below 1140px.

## Elevation & Depth

Flat panels with a 1px border and a very soft shadow (`0 1px 2px` + `0 1px 3px`, 4-5% alpha). Tooltips and the "?" explanations are dark popovers with a larger soft shadow. No glows, no gradients except the score legend.

## Shapes

Panels 12px radius, buttons and inputs 9px, small chips 6px, status pills fully rounded. Bars are 8px tall pills; chart columns 6px radius.

## Components

- **Status pill (completeness):** Fully graded (navy soft, check icon), Some grades missing (white with navy outline, half-circle icon), Not graded yet (grey, dashed-circle icon), Not measured (outlined, dash icon), Needs attention (error). Rendered by `core/_state.html`.
- **Score:** bar plus percentage in the score colour, with a short note ("87.5% of evidence graded", "a recorded zero"). Missing evidence shows a hatched track and "No graded evidence"; not measured shows an empty outlined track. Rendered by `core/_score.html`.
- **Outcome row:** a `<details>` element; the summary shows code badge, description (two lines), score and status; the open state lists contributing courses, LOs or assessments with weights and an "Enter grade" button where a grade is missing.
- **Outcome overview:** one column per PO, height = achievement, colour = score scale; hatched column = not graded yet; dashed = not measured; hover tooltip shows the description.
- **Needs attention:** one item per missing assessment, naming the course and the outcomes it holds back, with a direct "Enter grade" action (only for users with `change_grade`).
- **Grade editor:** one row per assessment with LO links and help text; an empty input is hatched with the placeholder "Not graded"; the live column shows the percentage in the score colour or an inline error; the sticky save bar counts unsaved changes and the page warns before leaving with unsaved edits.
- **Buttons:** primary (navy), ghost (white with border), small variant for inline actions. Focus-visible: 3px navy ring at 45% alpha on every interactive element.

## Do's and Don'ts

- Do keep score colour and completeness status as two separate signals on every result.
- Do turn every missing grade into a named next step with a link to the grade editor (permission-gated).
- Do show a recorded zero as `0.00%` with the note "a recorded zero"; never show a missing grade as 0 or as an empty bar.
- Do keep the texts that tests rely on ("No graded evidence", two-decimal percentages, "Nothing was saved", "Out of 50.00").
- Don't use the score colours for buttons, links or status pills, or navy for scores.
- Don't add inline `<style>` blocks to templates; extend `core/base.html` and use `core/static/core/gnosis.css`.
- Don't put `type="submit"` buttons in the shared layout (the enroll page must render none when nothing is eligible).

## Motion

- **Approach:** minimal-functional
- **Easing:** enter(ease-out) exit(ease-in) move(ease-in-out)
- **Duration:** micro(50-100ms) short(150-250ms) medium(250-400ms) long(400-700ms)
- **The one authored moment:** opening an outcome row slides its "where this comes from" detail in (180ms) while the chevron turns; disabled under `prefers-reduced-motion`.

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-11-01 | Initial design system created | Created by /design-consultation from the product brief, web research on outcome tools and gradebooks, and an independent Claude subagent proposal (Codex unavailable). |
| 2026-11-01 | Two-ink "Evidence Sheet" direction rejected | User found it hard to use; asked for something more user friendly. |
| 2026-11-01 | Modern workspace layout (sidebar, overview chart, needs-attention panel) chosen | User picked direction A of three HTML directions and asked for an improved version. |
| 2026-11-01 | Achievement coloured by value | User asked for different colours per percentage; implemented as a muted academic scale separate from completeness. |
| 2026-11-01 | Navy, gold accent and Source Serif 4 / Source Sans 3 | User asked for colours more suitable for an academic setting. |
