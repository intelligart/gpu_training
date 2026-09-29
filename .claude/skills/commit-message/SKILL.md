---
name: commit-message
description: "Generate a focused commit message from staged GPU Platform changes. Use when: preparing a commit or reviewing staged scope."
license: MIT
metadata:
  author: gpu-platform
  version: "1.0"
---

# Generate a Commit Message

1. Read `git diff --staged --stat` and `git diff --staged` in the target repo.
2. If nothing is staged, say so and stop; never stage automatically.
3. Ensure the staged paths form one task lane and exclude runtime databases, secrets,
   local MCP settings, logs, build output, and unrelated repo changes.
4. Generate an imperative subject under 72 characters. Use `feat`, `fix`, `docs`,
   `test`, `refactor`, or `chore` only when it clarifies local history.
5. Add a body only for motivation, compatibility, risk, rollback, or a non-obvious
   cross-repo dependency. Include the OpenSpec change/task and verification when useful.
6. Return the proposed message. Never commit or push without a later explicit request.