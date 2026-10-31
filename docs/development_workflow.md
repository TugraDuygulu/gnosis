# Development workflow and evidence

This is the workflow approved by Tuğra for his AI-assisted Gnosis development
on October 31, 2026. Adoption by the full four-person team, reviewer ownership
and branch-protection rules still require team agreement.

## One bounded change

1. Agree on the user story and testable acceptance criteria. Create or update
   the relevant GitHub issue before implementation; keep its original history.
2. Inspect the current working tree and relevant code. Use a feature branch
   from current main, preserving unrelated local changes.
3. Implement the agreed scope. Run the checks below and inspect the diff.
4. With explicit approval, commit, push and open a PR linked to the issue.
   State the resulting behavior, actual test commands/results and limitations.
5. Obtain a real review where feasible. Tuğra gives final approval for merging.
   An owner review or self-merge must not be described as teammate peer review.
6. After approved merge, close issues whose criteria are met; otherwise record
   the remaining work. Record substantial decisions in the Work → Chat handoff.

Approvals for related commits, pushes, PRs and merges can be requested as one
batch with clear conditions. Approval of implementation alone does not grant
permission for these actions. Assignments, team policy and deployment also
require explicit approval.

## Local checks and CI

Use Python 3.14 and the pinned `requirements.txt` in a virtual environment:

```bash
python -m pip install -r requirements.txt
python -m pip check
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --verbosity 2
git diff --check
```

The Django checks workflow runs the dependency, configuration, migration and
test checks on Ubuntu with SQLite for pushes and pull requests. Tests create
their own database using migrations; they do not use local student records.
This checks the development configuration. It does not certify production
deployment or cross-database compatibility.

After pushing, inspect the actual Actions result for the PR's current revision
and attach its run link to the PR or issue. A local pass is not a successful
GitHub CI run. Preserve failed runs and describe fixes truthfully. Do not merge
while required checks fail. Branch protection is not configured by this change.

## Report evidence

Keep links to issues, commits, PR diffs, real reviews and Actions runs as work
happens. Record who actually contributed or reviewed. Never reconstruct sprint
history, velocity, peer approvals or CI results that did not occur. Use closing
keywords such as `Closes #5` only when the PR satisfies the issue on merge;
otherwise use a reference and list the unfinished criteria.
