# Nous / Gnosis — six-week GitHub delivery plan

**Established 12 November 2026 at the project owner's request.** Six one-week
sprints start **16 November** and finish **27 December**. Timezone: Europe/Istanbul.
This is a forward plan, not a retrospective relabelling of earlier commits.

**Live entry point:** [roadmap #27](https://github.com/TugraDuygulu/gnosis/issues/27).
Issues own live work/evidence; this document records the release forecast and
operating defaults. All work items exist with an assignee, reviewer and acceptance
criteria. Points await real team Planning Poker, not invented estimates.

## Product goal and weekly increments

Deliver a usable outcome-management system with role-scoped accounts, safe
individual/bulk grading, explainable outcomes and reports, measured performance,
reproducible installation/recovery and accurate course evidence.

| Sprint | Inclusive dates | Goal / review demonstration | Live thread |
| --- | --- | --- | --- |
| 1 | 16-22 Nov | Coordinator provisions accounts; instructor grades assigned offerings; student sees own results; forbidden access rejected | [#32](https://github.com/TugraDuygulu/gnosis/issues/32) |
| 2 | 23-29 Nov | Upload one offering's CSV, inspect preview, reject invalid/stale files or atomically commit grades with history | [#33](https://github.com/TugraDuygulu/gnosis/issues/33) |
| 3 | 30 Nov-6 Dec | Inspect/print/export scoped student/cohort reports with truthful score/coverage/error states and reliable Turkish search | [#34](https://github.com/TugraDuygulu/gnosis/issues/34) |
| 4 | 7-13 Dec | Demonstrate measured query improvements and bounded gradebook saves with a larger fictional class | [#35](https://github.com/TugraDuygulu/gnosis/issues/35) |
| 5 | 14-20 Dec | Another teammate installs/restores a release candidate; both final-report first drafts are complete | [#36](https://github.com/TugraDuygulu/gnosis/issues/36) |
| 6 | 21-27 Dec | Accept and rehearse the exact final release; finalize reports and six-sprint evidence | [#37](https://github.com/TugraDuygulu/gnosis/issues/37) |

**Feature freeze target: 18 December.** Last-week capacity is deliberately lower
around the 22/24 December midterms. **28 December:** printing, backup and logistics
buffer. **29-30 December:** final demos and separate course reports. Each sprint
contains implementation where needed, tests, documentation and review; these are
not six sequential waterfall phases. Later-week scope is a forecast that can be
adjusted visibly, not six immutable commitments.

## Epics and work allocation

Epics describe larger outcomes and can span sprints. Do not estimate an epic and
its children, a sprint thread and its tasks, or an issue and its implementation PR.
The four epic trackers are [roles #28](https://github.com/TugraDuygulu/gnosis/issues/28),
[grading/reports #29](https://github.com/TugraDuygulu/gnosis/issues/29),
[reliability/delivery #30](https://github.com/TugraDuygulu/gnosis/issues/30) and
[final evidence #31](https://github.com/TugraDuygulu/gnosis/issues/31).

| Sprint | Tuğra | Omar | Emir | Ramazan |
| --- | --- | --- | --- | --- |
| 1 | [#38](https://github.com/TugraDuygulu/gnosis/issues/38) Role integration/migration | [#39](https://github.com/TugraDuygulu/gnosis/issues/39) Role navigation/UI | [#40](https://github.com/TugraDuygulu/gnosis/issues/40) Permission matrix | [#41](https://github.com/TugraDuygulu/gnosis/issues/41) Independent pilot |
| 2 | [#42](https://github.com/TugraDuygulu/gnosis/issues/42) CSV validation/atomic import | [#43](https://github.com/TugraDuygulu/gnosis/issues/43) Preview/confirmation UI | [#44](https://github.com/TugraDuygulu/gnosis/issues/44) Import integrity tests | [#45](https://github.com/TugraDuygulu/gnosis/issues/45) Fixtures/instructions/browser acceptance |
| 3 | [#46](https://github.com/TugraDuygulu/gnosis/issues/46) Report data/CSV export | [#47](https://github.com/TugraDuygulu/gnosis/issues/47) Evidence/print/chart UI | [#48](https://github.com/TugraDuygulu/gnosis/issues/48) Report/export tests | [#49](https://github.com/TugraDuygulu/gnosis/issues/49) Turkish search fix/acceptance |
| 4 | [#50](https://github.com/TugraDuygulu/gnosis/issues/50) Query optimization | [#51](https://github.com/TugraDuygulu/gnosis/issues/51) Bounded gradebook | [#52](https://github.com/TugraDuygulu/gnosis/issues/52) Performance/table metrics | [#53](https://github.com/TugraDuygulu/gnosis/issues/53) Consistency/failure probes |
| 5 | [#54](https://github.com/TugraDuygulu/gnosis/issues/54) Backup/restore/RC | [#55](https://github.com/TugraDuygulu/gnosis/issues/55) Release UI/design evidence | [#56](https://github.com/TugraDuygulu/gnosis/issues/56) Clean delivery/CSE311 draft | [#57](https://github.com/TugraDuygulu/gnosis/issues/57) Restore/CSE321 draft |
| 6 | [#58](https://github.com/TugraDuygulu/gnosis/issues/58) Release stabilization | [#59](https://github.com/TugraDuygulu/gnosis/issues/59) Demo/fallback/UX acceptance | [#60](https://github.com/TugraDuygulu/gnosis/issues/60) Final CSE311 report | [#61](https://github.com/TugraDuygulu/gnosis/issues/61) Final CSE321 report/acceptance |

These are initial accountable assignments, not completed contributions or recorded
availability agreement. Each issue names a reviewer. Teammates raise capacity
conflicts before planning; Tuğra coordinates reassignment rather than leaving all
work pending. Pair across roles, and split oversized issues into independently
verifiable leaves. Replace rather than double-count a split parent's estimate.

## Setup on 12-15 November

**Thursday 12:** record the instructor's actual feedback and inspect the roadmap,
assignments and context PR #26. The owner reports the presentation completed;
physical report submission and particular feedback are not inferred.

**Friday 13:** create/configure one GitHub Project board, add these existing
issues, and create six one-week iteration values beginning 16 Nov. Suggested fields:
Status, Sprint, Points, Priority, Reviewer; Assignees remain the human owners.
Status: Backlog -> Ready -> In progress -> Review/testing -> Done. Blocked is a
separate flag. Useful views: all backlog, current sprint, by assignee, and timeline.
Grant appropriate project access to the four existing collaborators, not public
write access. This UI/permission setup is not claimed done by documentation.

**Saturday 14:** each member verifies access/setup, reads the relevant issues and
records availability. Keep setup small around examinations; no new feature sprint
is expected this weekend.

**Sunday 15:** short kickoff and Sprint 1 Poker; clarify criteria, split oversized
items and propose a feasible commitment. Confirm/freeze that baseline at Monday
planning. Review/merge the documentation PR only with owner's separate approval;
application PR #25 remains separate.

## Weekly operating agreement

| When | Action | Record |
| --- | --- | --- |
| Monday, about 30 min | Confirm goal, availability, selected Ready issues and estimates | Control-thread planning comment with original scope/points |
| Each weekday, by 20:00 | Brief asynchronous coordination; read teammates' blockers | Done/evidence; next action; blocker/help; goal confidence |
| Midweek, about 15 min | Refine upcoming work, split uncertainty, inspect dependencies | Issue changes and dated scope decisions |
| Sunday, about 20 min | Demonstrate working increment, inspect acceptance and feedback | Goal outcome, revision/tests, accepted work, carryover |
| After review, about 10 min | Retrospective on how the team worked | One concrete improvement with an owner |

20:00 is a starting coordination deadline, not an automated reminder or a
requirement to code every day. 'No project work today; next ...' is valid. Urgent
blockers are raised immediately; unresolved problems get a short live discussion.
This asynchronous routine is a pragmatic adaptation, not a claim that a formal
synchronous Daily Scrum occurred. Review concerns the product; retrospective
concerns the team's process. Meeting clock times can fit classes without moving
the one-week date windows. Tuğra coordinates priorities and integration, but the
whole team estimates, helps, reviews and demonstrates its work.

## Issues and Planning Poker

Issues can be stories, technical tasks, bugs or bounded investigations. Express
real user value with 'As a ... I want ... so that ...'; avoid contrived stories for
purely technical work. Every Ready issue needs criteria, dependencies, owner and
reviewer. Use the repository work-item template for newly discovered work.

Use **1, 2, 3, 5, 8 relative points**. Read the issue, choose independently, reveal
together, discuss the highest/lowest reasoning, then revote and record agreement.
A short call/in-person countdown or simultaneous GitHub comments is sufficient;
sequential visible guesses are not independent voting. Split very large/unclear
work or time-box investigation. Agents can describe risks, not supply fictional
team votes. Estimate only remaining work and preserve original estimates.

One primary In progress issue per person is the initial work-in-progress limit.
Help blocked work and review queued PRs before starting more. A PR links its issue;
being pushed or opened does not make it Done.

## Definition of Done and measurement

Done requires acceptance criteria, applicable automated/CI/browser checks, real
human review, owner-approved integration for code, updated documentation/evidence,
and no unaccepted critical access/data-loss/calculation defect. Expected failures
are disclosed, not ordinary passes or a shortcut around bugs. Documentation-only
work still needs accuracy/readability review and a recorded accepted artifact.

At planning snapshot planned original points. During the week log scope changes
and remaining work in the sprint thread. At review sum original points only for
leaf items that met Done in that sprint. No partial points for nearly finished
work; cancelled work is not completed; carryover counts once in the sprint it
finishes. Track planned/completed/added/removed points, goal outcome and defects.
The first sprint is a baseline, not a quota or ranking of individual teammates.
A small daily remaining-points table can support a burndown; its values must come
from actual issue state, not a fabricated smooth curve.

## Scope and evidence boundaries

Preserve existing formulas, coverage, missing-vs-zero semantics, framework
isolation, audit/atomicity and stale protection. CSV and report extensions are
selected useful additions, not claims of existing implementation or mandatory
instructor technologies. No compulsory new frontend/API, cloud spend, real
institutional data, syllabus-AI import or retake-policy redesign. Changes to the
release forecast are recorded with a reason; do not silently sacrifice quality.

CSE311 evidence accumulates every week: backlog, actual work, estimates/sprints/
velocity, member and code-frequency charts, branching, Actions YAML/run summaries,
and specific Getting Real chapters tied to actual decisions. CSE321 evidence:
features, architecture/classes, schema/normalization, final rows/columns/raw-size
method, indexes/scalability/fault tolerance, transactions/actual isolation and
explicit contributions. Complete both six-section drafts in Sprint 5; refresh at
release in Sprint 6. The checkpoint's three-page/six-slide limits are not assumed
final limits. Existing issues #6/#9/#13/#14 retain their history.

## Setup status and references

Created on 12 Nov: **1 roadmap, 4 epic trackers, 6 sprint control threads and 24
assigned work issues**. Epic links/checklists are installed. Native Project board,
iteration fields, milestone objects and sub-issue relations are not configured by
the connected issue tools. Issue threads already support the working routine;
the board is the remaining interface setup, not a reason to delay Sprint 1.

Course basis: supplied CSE311 Report Format sections 1-6; CSE321 Report Format
sections 1-6; combined Team Project Guidelines (useful features p10, final p15).
External tool/framework references, not extra course requirements:
- [GitHub Issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/learning-about-issues/about-issues)
- [GitHub iteration fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-iteration-fields)
- [Scrum Guide](https://scrumguides.org/scrum-guide.html)

This plan does not start a sprint early, claim completed meetings, merge PR #25,
configure branch protection, or alter personal Notion/Calendar data. Original
working trees, databases and report previews remain protected.
