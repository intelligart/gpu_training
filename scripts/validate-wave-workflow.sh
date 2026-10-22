#!/usr/bin/env bash

set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

errors=0
warnings=0
active_changes=()

pass() { printf 'PASS  %s\n' "$1"; }
warn() { printf 'WARN  %s\n' "$1"; warnings=$((warnings + 1)); }
fail() { printf 'FAIL  %s\n' "$1"; errors=$((errors + 1)); }

required_files=(
	.claude/CLAUDE.md
	.claude/skills/wave-issues/SKILL.md
	.claude/skills/start-issue/SKILL.md
	.claude/skills/todo-priority/SKILL.md
	.claude/skills/commit-message/SKILL.md
	.github/copilot-instructions.md
	.github/prompts/wave-issues.prompt.md
	.github/prompts/start-issue.prompt.md
	.github/prompts/todo-priority.prompt.md
	.github/prompts/commit-message.prompt.md
	SUB_AGENT_CHEATSHEET.md
	ROADMAP.md
	ISSUES.md
	TEAM_LOG.md
	docs/platform-architecture.md
	docs/agent-training-integration.md
	docs/platform-v1-engineer-handoff.md
	docs/platform-v1-rollout.md
	MCP_GUIDE.md
	config/components.json
	deploy/platform-v1/artifact.json
	deploy/platform-v1/requirements-service.lock
	deploy/platform-v1/systemd/slurm-api.service
	deploy/platform-v1/systemd/slurm-mcp.service
	deploy/platform-v1/nginx/gpu-platform.conf
	openspec/config.yaml
	scripts/build-platform-v1-artifact.sh
	scripts/check-wave-github-target.sh
	scripts/lint-agent-integrations.sh
	scripts/preflight-v1.sh
	scripts/setup-wave-workspace.sh
	scripts/validate-components.sh
	scripts/validate-deployment-config.sh
	scripts/validate-rollout-runbook.sh
	scripts/validate-wave-workflow.sh
)

for file in "${required_files[@]}"; do
	[[ -s "$file" ]] || fail "missing required file: $file"
done
((errors == 0)) && pass "required Wave files exist"

local_config_files=(
	.env
	.claude/.mcp.json
	.claude/settings.local.json
	.vscode/mcp.json
	slurm_history.db
)
unignored_local_configs=()
for file in "${local_config_files[@]}"; do
	git check-ignore --quiet --no-index "$file" || unignored_local_configs+=("$file")
done
if ((${#unignored_local_configs[@]} == 0)); then
	pass "machine-local configuration and runtime database are ignored"
else
	fail "local files are not ignored: ${unignored_local_configs[*]}"
fi

for script in scripts/build-platform-v1-artifact.sh scripts/check-wave-github-target.sh scripts/lint-agent-integrations.sh scripts/preflight-v1.sh scripts/setup-wave-workspace.sh scripts/validate-components.sh scripts/validate-deployment-config.sh scripts/validate-rollout-runbook.sh scripts/validate-wave-workflow.sh; do
	if bash -n "$script"; then
		pass "$script syntax"
	else
		fail "$script syntax"
	fi
done

if bash scripts/lint-agent-integrations.sh >/dev/null; then
	pass "AI clients are restricted to MCP training submission"
else
	fail "AI client integration policy is invalid"
fi

if bash scripts/validate-components.sh >/dev/null; then
	pass "component registry matches local checkouts"
else
	fail "component registry does not match local checkouts"
fi

if env -u WAVE_GH_REPO bash scripts/check-wave-github-target.sh >/dev/null 2>&1; then
	fail "GitHub target guard accepted an unset target"
else
	pass "GitHub target guard rejects an unset target"
fi

for upstream in SchedMD/slurm Lightricks/LTX-2 NVIDIA/DCGM; do
	if WAVE_GH_REPO="$upstream" bash scripts/check-wave-github-target.sh >/dev/null 2>&1; then
		fail "GitHub target guard accepted upstream $upstream"
	else
		pass "GitHub target guard rejects upstream $upstream"
	fi
done

if WAVE_GH_REPO=internal/gpu-platform bash scripts/check-wave-github-target.sh >/dev/null; then
	pass "GitHub target guard accepts owner/repo form"
else
	fail "GitHub target guard rejected a valid internal target"
fi

github_workflow_files=(
	.claude/skills/wave-issues/SKILL.md
	.claude/skills/start-issue/SKILL.md
)
if /usr/bin/grep -q 'WAVE_GH_REPO' "${github_workflow_files[@]}" &&
	/usr/bin/grep -q -- '--repo' "${github_workflow_files[@]}"; then
	pass "GitHub mutation workflows require explicit repository targeting"
else
	fail "GitHub mutation workflows lack explicit repository targeting"
fi

for change_dir in openspec/changes/*; do
	[[ -d "$change_dir" ]] || continue
	[[ "$(basename "$change_dir")" == "archive" ]] && continue
	change_name="$(basename "$change_dir")"
	active_changes+=("$change_name")
	for artifact in proposal.md design.md tasks.md; do
		[[ -f "$change_dir/$artifact" ]] || fail "$change_name is missing $artifact"
	done
	# OpenSpec strict validation below enforces deltas and explicit skip_specs.
done

node_major=0
if command -v node >/dev/null 2>&1; then
	node_major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || printf '0')"
fi
if { [[ ! "$node_major" =~ ^[0-9]+$ ]] || ((node_major < 20)); } &&
	[[ -s "$HOME/.nvm/nvm.sh" ]] && [[ -f .nvmrc ]]; then
	export NVM_DIR="$HOME/.nvm"
	# shellcheck source=/dev/null
	. "$NVM_DIR/nvm.sh"
	nvm use --silent >/dev/null 2>&1 || true
	node_major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || printf '0')"
fi

if [[ "$node_major" =~ ^[0-9]+$ ]] && ((node_major >= 20)) &&
	command -v openspec >/dev/null 2>&1; then
	if openspec list >/dev/null 2>&1; then
		pass "OpenSpec CLI can read the project"
	else
		fail "OpenSpec CLI failed to read the project"
	fi
	for change_name in "${active_changes[@]}"; do
		if openspec validate "$change_name" --strict >/dev/null 2>&1; then
			pass "OpenSpec change is valid: $change_name"
		else
			fail "OpenSpec change is invalid: $change_name"
		fi
	done
else
	fail "Node.js 20+ and OpenSpec are required"
fi

printf '\nWave validation: %d error(s), %d warning(s)\n' "$errors" "$warnings"
((errors == 0))