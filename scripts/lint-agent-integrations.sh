#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

files=(
	.claude/CLAUDE.md
	.github/copilot-instructions.md
	README.md
	MCP_GUIDE.md
	docs/agent-training-integration.md
)

user_docs=(
	README.md
	MCP_GUIDE.md
	docs/agent-training-integration.md
	docs/platform-v1-engineer-handoff.md
)

for file in "${files[@]}"; do
	[[ -s "$file" ]] || { printf 'Missing agent integration policy: %s\n' "$file" >&2; exit 1; }
done

if /usr/bin/grep -nE '(curl|httpx|requests).*(/submit|:8765)|https?://[^ ]+:8765' "${files[@]}"; then
	printf 'Agent-facing documentation exposes a raw submission endpoint.\n' >&2
	exit 1
fi

for file in .claude/CLAUDE.md .github/copilot-instructions.md MCP_GUIDE.md docs/agent-training-integration.md; do
	/usr/bin/grep -qi 'MCP' "$file" || { printf '%s lacks the MCP-only contract.\n' "$file" >&2; exit 1; }
done

for file in "${user_docs[@]}"; do
	/usr/bin/grep -q 'username.*venv\|`username`.*`venv`' "$file" || {
		printf '%s does not require username and venv.\n' "$file" >&2
		exit 1
	}
done

if /usr/bin/grep -nE '\|[[:space:]]*`venv`[[:space:]]*\|[[:space:]]*否|每次 job 執行前會自動.*git pull|Job log 只能讀' "${user_docs[@]}"; then
	printf 'User documentation contains an obsolete platform behavior.\n' >&2
	exit 1
fi

/usr/bin/grep -qi '不得.*降級\|Never fall back' .claude/CLAUDE.md .github/copilot-instructions.md MCP_GUIDE.md docs/agent-training-integration.md || {
	printf 'Agent integration docs lack the no-fallback rule.\n' >&2
	exit 1
}

printf 'Agent integration policy is valid.\n'