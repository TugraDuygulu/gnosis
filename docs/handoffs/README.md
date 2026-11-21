# Task handoffs

Use [TEMPLATE.md](TEMPLATE.md) when unfinished work must survive a new agent/session
or when a meaningful verification result needs a durable continuation record.
Routine progress belongs in the issue/PR; do not create a handoff for every message
or paste entire chat transcripts here.

## Write and resume

- Copy the template into a unique file such as
  `YYYY-MM-DD-issue-NN-topic-owner.md`; use `pr-NN` when the work is scoped to a PR.
  Replace placeholders, omit irrelevant fields and keep the record brief.
- Put the handoff on the task branch. Link it from the issue/PR so another agent can
  find it before merge. Other agents must read that branch's version, not assume it
  exists on main. Avoid multiple agents editing the same entry concurrently.
- Record exact source revision, uncommitted paths, approvals, commands and actual
  outcomes. Distinguish implementation, local checks, CI and browser/manual review.
- Keep failures and unknowns explicit. Do not convert an expected failure into a
  pass, a proposal into a decision, or an author's review into teammate sign-off.
- At integration, reconcile the dated [project snapshot](../PROJECT_CONTEXT.md)
  through an approved documentation update. Preserve old evidence; supersede an
  old handoff with a clearly dated correction rather than erasing its history.

Before resuming, read [AGENTS.md](../../AGENTS.md), inspect the real checkout/PR,
and compare it with the handoff's revision. A stale next step may already be done.
No record here authorizes merging, deployment or changes outside the current task.

## Share-safe content only

Use fictional fixtures and sanitized output. No credentials, .env contents,
personal schedules/health/study records, private Notion links or conversations,
real student data, private database copies, or unnecessary account identifiers.
Use repository-relative paths rather than exposing personal machine paths.
