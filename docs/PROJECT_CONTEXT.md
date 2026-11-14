# Gnosis project context

**Team:** Nous. **Project:** Gnosis for CSE311 Software Engineering and CSE321 Data
& System Architecture. **Snapshot checked:** 12 November 2026. This project-only
summary is not a chat archive or substitute for current code. Read
[AGENTS.md](../AGENTS.md) first.

## Product and authoritative documents

Gnosis lets staff register/enroll students, maintain grades and trace evidence
through course learning outcomes (LOs), course program outcomes (POs) and a
student's multi-course PO profile. Attainment and evidence coverage are separate.
The pilot uses official PO descriptions with fictional students, grades, courses
and mappings; it is not a live institutional deployment or approved mapping set.

| Subject | Authoritative starting point |
| --- | --- |
| Setup and staff workflows | [README](../README.md), [v0.1 acceptance](v01_acceptance.md) |
| Architecture/schema | [Database design](database_design.md), [CSE321 workspace](reports/cse321/README.md), actual models/migrations |
| Formulae and selection boundaries | [Calculation policy](calculation_policy.md), `core/services/`, regression tests |
| UI | [DESIGN](../DESIGN.md) |
| Approvals and verification | [Development workflow](development_workflow.md) |
| Reproducible SQL | [SQL guide](../sql/README.md) |
| Live work and roadmap | [Issues](https://github.com/TugraDuygulu/gnosis/issues), [roadmap #27](https://github.com/TugraDuygulu/gnosis/issues/27) |
| Sprint context/continuation | [Six-week plan](sprints/SIX_WEEK_PLAN.md), [Sprint 1](sprints/SPRINT_01.md), [handoffs](handoffs/README.md) |

The implementation is server-rendered Django, shared calculation/write functions
and SQLite development storage, with pinned dependencies. No separate API/Vue,
external cache/queue, PostgreSQL deployment or production hosting is assumed.

## Verified application baseline versus branch work

| State | Evidence | Supported claim |
| --- | --- | --- |
| Main application | [`293cfbe`](https://github.com/TugraDuygulu/gnosis/commit/293cfbea178cf33ca7eb1257d79eceaa88602c7e); [CI job](https://github.com/TugraDuygulu/gnosis/actions/runs/43094134525/job/130778492080) | Staff workflow, merged frontend/gradebook/overview, grade history and teammate tests. On 11 Nov: **97 run, 96 passed, 1 expected failure**; dependency/configuration/migration checks passed. |
| Academic accounts | [Draft PR #25](https://github.com/TugraDuygulu/gnosis/pull/25), branch `feature/academic-role-accounts`, revision `fb4835a6382093db4dad93d124dac5451b89c175`; [earlier CI](https://github.com/TugraDuygulu/gnosis/actions/runs/42798966273) | Coordinator provisioning, assigned-instructor and own-student access implemented on branch, **not merged**. Earlier 91 local tests and CI success; browser verification pending. |
| SQL checks | [SQL evidence](../sql/README.md) | Three SQL reports and 17 separate local cases; not part of the 97/91 comparison or the earlier external frontend QA probes. |

Counts are revision-specific, not live counters. Do not add 97 and 91 or call an
expected failure an ordinary pass. The 81-test result belongs to `80fc76d`.
Main student registration creates an academic record, not a personal login.
Documentation-only commits do not imply new application testing or deployment.

## Recorded contributions

| Member | Contribution | Evidence |
| --- | --- | --- |
| Tuğra Duygulu | Backend/domain calculations, integration and owner review, AI-assisted implementation; account branch | Service/workflow history; [PR #25](https://github.com/TugraDuygulu/gnosis/pull/25) |
| Omar Vali | Responsive frontend, class gradebook and outcome visualizations | [Merged PR #24](https://github.com/TugraDuygulu/gnosis/pull/24), 39 authored branch commits |
| Emir Becerik | Five route-access methods and Windows setup notes | [`db43016`](https://github.com/TugraDuygulu/gnosis/commit/db43016123d466a195098edff1781a6f0bdd84d3), [`403eb3b`](https://github.com/TugraDuygulu/gnosis/commit/403eb3b1a94712573cf878a6e3302c8de1a508ac) |
| Ramazan Öztekin | Six page-structure/empty-state methods and five Turkish-text methods, including expected failure | [`293cfbe`](https://github.com/TugraDuygulu/gnosis/commit/293cfbea178cf33ca7eb1257d79eceaa88602c7e), [`6c28324`](https://github.com/TugraDuygulu/gnosis/commit/6c283246c918859cc3c138331d38504cf4369dfa) |

Automated contributions do not prove manual browser/accessibility sign-off. The
latest four test/README commits went directly to main, an exception to the
specified PR process. Do not rewrite that history as independent PR review.

## Current limitations and scheduled work

- The fixed 12-staff-route matrix conflicts with PR #25's new routes/access and
  redirects if combined unchanged. Source inspection identified this; no merged
  suite was run. Resolve through Sprint 1 issues #38-#41, then browser QA/review.
- Turkish case-insensitive search is an expected failure, not fixed. Sprint 3
  issue #49 owns the documented case-handling correction.
- PR #24's display/weight/filter/contrast follow-ups are scoped into #47;
  overview query growth and large gradebook limits into #50-#53. These are plans,
  not completed fixes.
- Existing independent-verification issues #6/#9 remain historical context for
  the new bounded work; do not repeat delivered features or claim past sign-offs.
- Useful CSV import and student/cohort reports are planned in Sprints 2-3.
  They are not current capabilities. No compulsory cloud or framework change.

## Six-week plan is scheduled, not indefinitely awaiting decisions

On 12 Nov the owner requested a concrete GitHub-only plan and initial assignments.
[Roadmap #27](https://github.com/TugraDuygulu/gnosis/issues/27) links four epics
(#28-#31), six weekly control threads (#32-#37) and 24 assigned work items
(#38-#61), with named reviewers and acceptance criteria. First sprint starts
**Monday 16 Nov**; the sixth ends **Sunday 27 Dec**. Setup is **12-15 Nov**.
Feature freeze target: **18 Dec**; final checking/printing buffer: **28 Dec**.

Initial owners are assigned. Team availability and real Poker votes are not yet
recorded; each Monday confirms a feasible subset without erasing the original
forecast. Do not fabricate estimates, active/completed sprints or velocity.
Digital weekday check-ins, refinement, review, retrospective and completion rules
are in the roadmap. Native GitHub Project/iteration/milestone/sub-issue settings
are not yet configured by these issue/documentation changes. No new app or
personal Notion sharing is needed.

## Course evidence and freshness

The owner reported the **12 November joint presentation completed**. Do not infer
physical report submission, grading or teacher feedback. The earlier Nov17 split
checkpoint wording is superseded. The checkpoint used six slides/eight minutes
and a combined report of at most three pages; those limits are not automatically
final-demo/report limits.

Final demos and **separate six-section printed reports** are scheduled for
**29-30 December** by the project guidelines. Capture genuine sprint and technical
evidence weekly; report tasks #55-#61 cover actual contributions, estimates,
charts, CI, Getting Real chapters, design/schema, final table statistics,
scalability/failure handling and actual transaction/isolation behavior.

Keep this summary short and revision-linked. Issues/PRs own live progress; preserve
branch-versus-main distinctions and update after approved integration. Do not
publish private planning conversations or real student data to fill gaps.
