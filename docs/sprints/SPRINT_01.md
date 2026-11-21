# Sprint 1 — role accounts integrated and verified

**Scheduled: Monday 16 to Sunday 22 November 2026, Europe/Istanbul.**
**Status at creation: scheduled, not started.** This replaces the undated draft.
Dates, goal and initial ownership were set at the owner's request on 12 Nov;
actual availability, Planning Poker and Monday commitment still need recording.

**Live control thread:** [#32](https://github.com/TugraDuygulu/gnosis/issues/32).
Use that thread for planning, daily updates, scope changes, review and retrospective.
This Markdown is the starting brief, not a second task-status ledger.
[Six-week plan](SIX_WEEK_PLAN.md) / [roadmap #27](https://github.com/TugraDuygulu/gnosis/issues/27).

## Goal

Complete a fictional coordinator → assigned instructor → own-record student
journey on the integrated application, preserving calculations, evidence coverage,
permissions, grade history, atomic saves and stale-edit rejection.

## Initial allocation

| Issue | Work | Owner | Reviewer |
| --- | --- | --- | --- |
| [#38](https://github.com/TugraDuygulu/gnosis/issues/38) | Integrate existing account branch with current main and verify migration/data preservation | Tuğra | Emir |
| [#39](https://github.com/TugraDuygulu/gnosis/issues/39) | Complete role-specific navigation and screen gaps | Omar | Ramazan |
| [#40](https://github.com/TugraDuygulu/gnosis/issues/40) | Reconcile role/route permission matrix and denied-write tests | Emir | Tuğra |
| [#41](https://github.com/TugraDuygulu/gnosis/issues/41) | Independent fresh install and desktop/mobile pilot walkthrough | Ramazan | Omar |

PR #25 already contains implementation. Estimate remaining integration and
verification, not the earlier development. Coordinate #38/#40 on one role contract;
review UI and independent evidence before approved integration. Neither creating
this plan nor merging documentation merges the application branch.

## Planning and daily work

Before Monday, read acceptance criteria, identify dependencies and record available
time. Use independent 1/2/3/5/8 Poker votes; discuss differences, split oversized
items and record actual agreement. Monday's selected items/original points form
the baseline. Do not invent estimates or postpone the scheduled roadmap because
point values are still unknown. Later scope changes need a date, reason and effect
on the goal. Default one primary In progress item per person; help with blockers
and reviews before starting more.

Weekdays by **20:00 Istanbul**, comment in #32: date/name; completed evidence;
next action; blocker/help; goal confidence. No-work availability is valid. Urgent
blockers are raised immediately. This is asynchronous coordination, not a claim
that a formal synchronous Daily Scrum occurred.

## Review and retrospective — 22 November

Demonstrate coordinator provisioning, instructor assigned-course grading, student
own-results access, one forbidden request, and missing-versus-zero behavior.
Record exact integrated revision, CI, real browser evidence, goal outcome,
completed original points and carryover. Hold a separate retrospective and assign
one improvement. Planning participants, votes, review results and velocity remain
unrecorded until they actually happen. Apply the Definition of Done in the roadmap;
a draft PR or a passing old branch suite is not Done.
