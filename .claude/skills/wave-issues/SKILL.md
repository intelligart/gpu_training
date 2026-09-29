---
name: wave-issues
description: "Create or reconcile one GitHub issue per unfinished OpenSpec task lane. Use when: publishing an approved Wave or checking lane issue coverage."
license: MIT
compatibility: Requires gh, authenticated GitHub access, WAVE_GH_REPO, and OpenSpec.
metadata:
  author: gpu-platform
  version: "1.0"
---

# Publish OpenSpec Lanes as GitHub Issues

Create one claim issue for each selected unfinished `##` lane. `tasks.md` remains the
only authoritative checklist.

## Input

One existing OpenSpec change name. Reject path separators and traversal.

## Safety Contract

- Run `scripts/check-wave-github-target.sh`; never infer a target from Git remotes.
- Refuse official upstream repositories: `SchedMD/slurm`, `Lightricks/LTX-2`, and
  `NVIDIA/DCGM`.
- Validate the change before publishing.
- Show the resolved repo and complete create/reuse/skip plan, then obtain one explicit
  confirmation before any mutation.
- Every `gh` command MUST include `--repo "$WAVE_GH_REPO"`.
- Reruns MUST compare exact titles and reuse existing issues.

## Steps

1. Read `.claude/CLAUDE.md`, `SUB_AGENT_CHEATSHEET.md`, proposal, design, specs,
   and tasks for the selected change.
2. Run the target guard, `gh auth status --hostname github.com`, and
   `gh repo view "$WAVE_GH_REPO" --json nameWithOwner,hasIssuesEnabled,url`.
3. Run `openspec validate <change> --strict` and stop on failure.
4. Treat every `## <number>. <heading>` with unchecked tasks as one candidate lane.
   Confirm each task states target repo/file scope and verification before publishing.
5. Use title `<change> §<number> <heading>`. Query all issue states with explicit
   `--repo`, then compare exact titles rather than trusting fuzzy search.
6. Display lane, title, unchecked count, target repo, and create/reuse/skip action.
   Ask for confirmation at this mutation boundary.
7. Create approved missing issues with `gh issue create --repo "$WAVE_GH_REPO"`.
   The body links the exact tasks heading and states that `tasks.md` is authoritative,
   contributors record focused validation, and only a reviewer marks verified.
8. Add one `GitHub issue: <url>` line below each published lane heading. Reuse an
   existing mapping on reruns.
9. Report all successful mutations and stop immediately on partial failure so a rerun
   can safely reconcile them.

Do not auto-assign lanes. Claiming is a separate `/start-issue` operation.