# Sprint 1 - academic-account integration and verification

**Status: DRAFT - not started.** Prepared 12 November 2026 for team discussion.
Creating or merging this document does not start a sprint, assign work or approve
PR #25. The current baseline is in [PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md).

## Proposed goal

Make the academic-account workflow ready for a controlled fictional pilot:
coordinators can provision accounts, instructors can grade only their assigned
offerings, and students can view only their own records, with integrated behavior
verified and the existing attainment/coverage policy preserved.

This is remaining integration and verification work around an already implemented
branch, not a claim that its earlier implementation happened during Sprint 1.

## Team agreement required before activation

| Planning field | Current value |
| --- | --- |
| Start / end, Europe/Istanbul | Not agreed |
| Duration | One week proposed; not agreed |
| Team availability / capacity | Not recorded; discuss before selecting work |
| Final goal and selected scope | Proposed below; not committed |
| Human owners / reviewers | Unassigned |
| Estimate method | Relative 1, 2, 3, 5, 8 points proposed |
| Planned points | Not estimated; do not enter zero as an estimate |
| Planning participants / agreement evidence | Not recorded |
| Review and retrospective | Not scheduled |
| Velocity | Not measured; no completed documented sprint is claimed |

Record the actual planning agreement (date, participants and issue/PR comment
link), fill these fields and select a feasible subset before changing status to
ACTIVE. Proposed cadence: short planning; brief working-day coordination on goal,
next work and blockers; a demonstration/review and retrospective at the end. This
is a lightweight sprint proposal, not a claim of full Scrum adoption.

## Candidate work - not assignments or a second backlog

GitHub Issues/PRs hold detailed acceptance criteria and current work status.
Confirm current scope before reusing older issues, and create a bounded linked
issue only when needed and approved. Every candidate below is currently
**not selected, unassigned and unestimated**.

| Candidate | Existing context | Proposed completion evidence |
| --- | --- | --- |
| Integrate the role branch with current access tests | [PR #25](https://github.com/TugraDuygulu/gnosis/pull/25); `core/test_route_access.py` | Approved role/route matrix; correct redirects and server-side permission checks; unauthorized writes leave data unchanged; full combined suite and exact-revision CI recorded. |
| Verify role-specific UI journeys | [#6](https://github.com/TugraDuygulu/gnosis/issues/6), PR #25 | Fictional coordinator -> instructor -> student journey on desktop/mobile; negative/tampered access and navigation checked; findings and any fixes linked to the tested revision. Automated HTML checks alone do not complete browser QA. |
| Independently reproduce the integrated pilot | [#9](https://github.com/TugraDuygulu/gnosis/issues/9), [verification checklist](../teammate_verification.md) | An actual teammate uses an isolated environment and fictional database; records source/runtime, setup, login, grades, missing vs zero, outcomes and history results. No copied private database/credentials. |
| Record the release decision and sprint evidence | [#14](https://github.com/TugraDuygulu/gnosis/issues/14); linked PRs | Human review and owner integration decision, accurate current-context update, demonstration results and retrospective. No completed sprint/velocity claimed before the review. |

Do not automatically pull in the six older frontend follow-ups, a search fix,
PostgreSQL/hosting, a new API/frontend, import/email services or changes to formulas
and retake policy. A known defect can become a selected issue after agreement;
otherwise record its impact and do not hide it to satisfy the sprint goal.

## Proposed working agreement

**Ready:** a selected issue has testable acceptance criteria, dependencies, a human
owner, a reviewer, an agreed estimate for remaining work, and a safe test setup.

**Flow:** Backlog -> Ready -> In progress -> Review/testing -> Done. Track blocked
work explicitly with a reason and next action. These are proposed status meanings;
this file does not configure a GitHub Project board or labels.

**Definition of Done (agree at planning):**

- Acceptance criteria satisfied, including relevant failure/permission cases.
- Applicable dependency, system, migration, test and diff checks recorded.
- CI checked for the actual proposed revision; expected failures disclosed, not
  added as a shortcut or counted as ordinary passes.
- Applicable browser verification completed with evidence and human reviewer.
- No unaccepted release-blocking defect; remaining limitations explicitly recorded.
- Documentation/handoff reflects the result; no secrets or real student data added.
- Owner-approved integration completed and the included revision identified.

A test run passing is not a manual sign-off. A draft PR is not Done. Scope can be
renegotiated with the team; record who agreed, why and the effect on the goal.

## Estimate and review record

At planning, agree estimates with the people doing the work; split oversized or
unclear items. Estimate effort/complexity/uncertainty, not commits or lines of code.
Record only the remaining work on partially implemented features. Freeze the
original estimate for reporting; record changes separately and avoid double
counting a parent issue and its subtasks.

| Selected issue | Human owner | Reviewer | Original points | Added/removed scope and agreement | Done evidence / integrated revision |
| --- | --- | --- | --- | --- | --- |
| None selected yet | - | - | Not estimated | - | - |

At the actual review, fill in:

- Goal outcome and demonstration evidence: not reviewed.
- Completed items / accepted revisions: none recorded.
- Incomplete or removed items and reasons: not reviewed.
- Planned points / completed points: not yet available.
- Proposed velocity measure: sum original points of items meeting the agreed
  Definition of Done within this sprint. Incomplete items contribute no completed
  points; do not manufacture estimates after completion. If estimation was not
  adopted, report velocity as unavailable rather than inventing it.
- Retrospective: one thing to keep, one problem, and one agreed improvement with an
  owner. No retrospective has occurred yet.

This record will provide genuine evidence for the course report; it must never
backdate a planning meeting or convert old commits into a fictional sprint.
