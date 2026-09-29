---
name: start-issue
description: "Safely claim an existing GPU Platform Wave or local GitHub issue. Use when: beginning an assigned lane and preventing duplicate work."
license: MIT
compatibility: Requires gh, authenticated GitHub access, and WAVE_GH_REPO.
metadata:
  author: gpu-platform
  version: "1.0"
---

# Claim a Wave Issue

## Input

A GitHub issue number in the explicitly configured internal repository.

## Steps

1. Read `.claude/CLAUDE.md`, `SUB_AGENT_CHEATSHEET.md`, and
   `scripts/check-wave-github-target.sh`.
2. Require a numeric issue number and run the target guard. Never infer the repo from
   `origin` or another checkout.
3. Read the issue using
   `gh issue view <number> --repo "$WAVE_GH_REPO" --json number,title,body,state,assignees,url`.
4. Require an open issue whose body links either an exact OpenSpec tasks lane or an
   `ISSUES.md` entry. Read that local source of truth and identify target repo, branch,
   file scope, dependencies, and focused validation.
5. If assigned to someone else, stop. If scope is missing or ambiguous, stop and ask
   the coordinator to repair the source task.
6. Show the target repo and proposed claim/local-status/branch actions, then obtain
   explicit confirmation before mutation.
7. Claim with
   `gh issue edit <number> --repo "$WAVE_GH_REPO" --add-assignee @me`.
8. Only after a successful claim, add or update the issue mapping under the exact lane.
   Do not copy the checklist into GitHub.
9. Inspect the target repo worktree. Create `wave/<issue>-<short-slug>` only when clean;
   when dirty, continue in place only with explicit user direction.
10. Report issue URL, target repo/branch, lane, allowed files, dependencies, and the
    first focused validation. Do not commit or push unless separately requested.

On partial failure, preserve completed external actions and report them. Never recreate
an issue merely to make local state look consistent.