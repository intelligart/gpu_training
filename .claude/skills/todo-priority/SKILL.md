---
name: todo-priority
description: "Summarize recent platform work and rank unfinished OpenSpec changes and local issues. Use when: choosing the next Wave or preparing status."
license: MIT
metadata:
  author: gpu-platform
  version: "1.0"
---

# Summarize and Prioritize Work

This workflow is read-only. Output in Traditional Chinese.

1. Read the last seven days of commits in `gpu_training` and group them by theme.
2. Read the five newest `TEAM_LOG.md` entries.
3. List active `openspec/changes/` directories except `archive/`.
4. For every change, read its artifacts and count checked/unchecked tasks. Note target
   repos, dependencies, blockers, rollout risk, and missing validation.
5. Read open/in-progress `ISSUES.md` entries.
6. If `gh`, authentication, and a safe `WAVE_GH_REPO` are available, read issue state
   with explicit `--repo`; otherwise use local state only.
7. Rank safety/blockers first, user impact second, dependency order third, and completion
   leverage fourth. Live work lacking authorization or rollback remains blocked.

Return `過去 7 天摘要`, `未完成工作`, and `建議優先順序`. Do not edit files or mutate
GitHub.