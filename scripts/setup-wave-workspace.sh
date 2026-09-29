#!/usr/bin/env bash

set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

errors=0
warnings=0

pass() { printf 'PASS  %s\n' "$1"; }
warn() { printf 'WARN  %s\n' "$1"; warnings=$((warnings + 1)); }
fail() { printf 'FAIL  %s\n' "$1"; errors=$((errors + 1)); }

printf 'GPU Platform Wave workspace check\n'

for tool in git bash; do
	if command -v "$tool" >/dev/null 2>&1; then
		pass "$tool is available"
	else
		fail "$tool is required"
	fi
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

if [[ "$node_major" =~ ^[0-9]+$ ]] && ((node_major >= 20)); then
	pass "Node.js $(node --version) supports OpenSpec"
else
	fail "Node.js 20+ is required by OpenSpec"
fi

if command -v openspec >/dev/null 2>&1 && openspec --version >/dev/null 2>&1; then
	pass "OpenSpec CLI starts successfully"
else
	fail "OpenSpec CLI is unavailable"
fi

if command -v gh >/dev/null 2>&1; then
	pass "GitHub CLI is installed"
	if gh auth status --hostname github.com >/dev/null 2>&1; then
		pass "GitHub CLI is authenticated"
	else
		warn "GitHub CLI is not authenticated"
	fi
else
	warn "GitHub CLI is missing; issue workflows are unavailable"
fi

if [[ -n "${WAVE_GH_REPO:-}" ]]; then
	if bash scripts/check-wave-github-target.sh >/dev/null; then
		pass "GitHub issue target is safe: $WAVE_GH_REPO"
	else
		fail "GitHub issue target is unsafe"
	fi
else
	warn "WAVE_GH_REPO is unset; GitHub mutations will be refused"
fi

if bash scripts/validate-wave-workflow.sh; then
	pass "Wave workflow files are valid"
else
	fail "Wave workflow validation failed"
fi

printf '\nSummary: %d error(s), %d warning(s)\n' "$errors" "$warnings"
printf 'This script does not modify components, services, or live cluster state.\n'
((errors == 0))