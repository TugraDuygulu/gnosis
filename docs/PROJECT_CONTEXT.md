# Gnosis project context

**Team:** Nous. **Purpose:** one academic-outcome application for CSE311 Software
Engineering and CSE321 Data & System Architecture. **Snapshot checked:** 12 November
2026. This is a project-only entry summary, not a full chat archive or a substitute
for the current repository. Read [AGENTS.md](../AGENTS.md) first.

## Product and authoritative documents

Gnosis lets academic staff register/enroll students, maintain assessment grades and
trace evidence through course learning outcomes (LOs), course program outcomes
(POs) and a student's multi-course PO profile. Attainment and evidence coverage are
reported separately. The representative pilot uses official PO descriptions with
fictional students, grades, courses and mappings; it is not a live institutional
pilot or an institution-approved mapping set.

| Subject | Source to read rather than duplicate |
| --- | --- |
| Setup and existing staff workflows | [README](../README.md), [v0.1 acceptance](v01_acceptance.md) |
| Architecture, schema and versioned relationships | [Database design](database_design.md), [CSE321 workspace](reports/cse321/README.md), actual models/migrations |
| Formulae, coverage, missing vs zero, selection boundaries | [Calculation policy](calculation_policy.md), `core/services/` and regression tests |
| UI conventions | [DESIGN](../DESIGN.md) |
| Change approvals and verification commands | [Development workflow](development_workflow.md) |
| Reproducible SQL results | [SQL guide](../sql/README.md) |
| Work item status | [GitHub Issues](https://github.com/TugraDuygulu/gnosis/issues) and linked PRs |
| Sprint commitment / continuation | [Sprint 1 draft](sprints/SPRINT_01.md), [handoffs](handoffs/README.md) |

Django serves HTML templates, with shared calculation/write functions and SQLite for
development. Dependencies are pinned in `requirements.txt`. Do not assume a Vue
frontend, separate API, external cache/queue, PostgreSQL deployment or production
hosting exists because it appeared in an earlier proposal.

## Verified baseline versus branch work

These are revision-specific observations, not automatically refreshed counters.

| State | Revision and evidence | What can be claimed |
| --- | --- | --- |
| Main application baseline | [`293cfbe`](https://github.com/TugraDuygulu/gnosis/commit/293cfbea178cf33ca7eb1257d79eceaa88602c7e); [CI job](https://github.com/TugraDuygulu/gnosis/actions/runs/43094134525/job/130778492080) | Staff workflow, Omar's merged frontend/gradebook/overview, grade history and new teammate tests. CI on 11 November ran **97 tests: 96 passed, 1 expected failure**, with clean dependency/configuration/migration checks. |
| Academic accounts | [Draft PR #25](https://github.com/TugraDuygulu/gnosis/pull/25), `feature/academic-role-accounts` at `fb4835a6382093db4dad93d124dac5451b89c175`; [earlier CI](https://github.com/TugraDuygulu/gnosis/actions/runs/42798966273) | Coordinator provisioning, instructor assigned-offering access and student own-record access implemented on the branch; **not merged**. PR reports 91 local tests and CI success at its own revision. Desktop/mobile browser walkthrough remains unchecked. |
| SQL verification | [Saved evidence and reproduction](../sql/README.md) | Three executable SQL reports; 17 standalone local cases. Separate from Django's suite and the earlier external frontend QA probes. |

Do not add 97 and 91, call the expected failure a pass, or claim a combined-branch
run. The 81-test main result belongs to the earlier `80fc76d` snapshot.
The existing main registration flow creates an academic Student record, not a
personal login. Full academic roles are still branch work at this snapshot.

## Contributions supported by repository evidence

| Member | Recorded contribution | Evidence |
| --- | --- | --- |
| Tuğra Duygulu | Backend/domain calculations, integration and owner review, with AI-assisted implementation; account-role branch | Existing service/workflow history; [PR #25](https://github.com/TugraDuygulu/gnosis/pull/25) |
| Omar Vali | Responsive frontend, class gradebook and outcome visualizations | [Merged PR #24](https://github.com/TugraDuygulu/gnosis/pull/24), 39 authored branch commits |
| Emir Becerik | Five route-access test methods and Windows setup notes | [`db43016`](https://github.com/TugraDuygulu/gnosis/commit/db43016123d466a195098edff1781a6f0bdd84d3), [`403eb3b`](https://github.com/TugraDuygulu/gnosis/commit/403eb3b1a94712573cf878a6e3302c8de1a508ac) |
| Ramazan Öztekin | Six page-structure/empty-state test methods and five Turkish-text methods, including the expected failure | [`293cfbe`](https://github.com/TugraDuygulu/gnosis/commit/293cfbea178cf33ca7eb1257d79eceaa88602c7e), [`6c28324`](https://github.com/TugraDuygulu/gnosis/commit/6c283246c918859cc3c138331d38504cf4369dfa) |

These contributions do not automatically establish manual usability/accessibility
sign-off. The latest four test/documentation commits went directly to main; do not
rewrite that history as PR-reviewed integration. The documented PR workflow is a
working rule, not a claim that every historical change followed it.

## Open limitations and next decisions

1. **Integration:** `core/test_route_access.py` has a fixed matrix for the 12 staff
   routes; PR #25 adds login/logout/management routes and different access rules.
   Source inspection identifies incompatible assumptions if combined unchanged.
   Update the matrix to the approved role policy, keep denied-write checks, run the
   combined suite, then perform browser QA and review. This is not an executed
   combined-branch failure report or authorization to merge.
2. **Turkish search:** `test_search_ignores_case_for_turkish_letters` is an expected
   failure; Unicode case-insensitive search is not fixed by that annotation.
3. **Frontend follow-ups:** [PR #24](https://github.com/TugraDuygulu/gnosis/pull/24)
   records query growth, large gradebook submissions, error-vs-unmeasured display,
   chart navigation under filters, weight/coverage wording and faint-text contrast.
   They are recorded limitations, not all completed fixes or current sprint scope.
4. **Independent verification:** [#9](https://github.com/TugraDuygulu/gnosis/issues/9)
   and [#6](https://github.com/TugraDuygulu/gnosis/issues/6) remain open. Their older
   descriptions must be reconciled with current implementation before selecting
   remaining work; do not repeat already delivered features.
5. **Planning:** no agreed first-sprint dates, estimates or measured velocity are
   recorded here. [Sprint 1](sprints/SPRINT_01.md) is a proposal awaiting team
   agreement, not an active sprint or retroactive label on earlier development.

## Course evidence and freshness

The supplied instructor announcement combines the 12 November checkpoint for both
courses: at most six Google Slides, no title slide, eight minutes; one printed
report of at most three pages, no title page, with team/members/repository atop page
1. Page 1 uses CSE311 sections 1-2, page 2 CSE321 sections 1-2; diagrams/code must be
legible at 125%. This supersedes older split checkpoint wording in
[#13](https://github.com/TugraDuygulu/gnosis/issues/13) and
[#14](https://github.com/TugraDuygulu/gnosis/issues/14). No completed presentation,
printing, submission or sprint is inferred from preparation. Final-report work
remains distinct from this checkpoint.

Keep actual member contributions, estimates, sprint dates/reviews and CI links as
work happens. Do not publish private planning conversations or course/student
records to fill documentation gaps.

## Updating this summary

Keep it short. Update the verified main snapshot after integration through an
approved documentation change, and retain evidence links for older test results.
Keep unmerged progress in the relevant PR/task handoff. Record approved decisions
with date and issue/PR link; label proposals and unknowns explicitly. A new
instruction file or handoff cannot approve work on behalf of a human.
