#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python_bin="${PYTHON_BIN:-python3}"
export PATH="$HOME/.local/bin:$PATH"

run_gate() {
	local label="$1"
	shift
	printf '\n==> %s\n' "$label"
	"$@"
}

command -v "$python_bin" >/dev/null 2>&1 || {
	printf 'Python executable not found: %s\n' "$python_bin" >&2
	exit 1
}

printf '\n==> Python syntax\n'
"$python_bin" - <<'PY'
import ast
from pathlib import Path

files = [Path("mcp_server.py"), Path("slurm_server.py"), Path("onboarding.py"), *sorted(Path("tests").glob("test_*.py"))]
for file in files:
    ast.parse(file.read_text(), filename=str(file))
print(f"Parsed {len(files)} Python files.")
PY

run_gate "Unit and concurrency tests" \
	env PYTHONDONTWRITEBYTECODE=1 "$python_bin" -m unittest discover -s tests -v

node_major=0
if command -v node >/dev/null 2>&1; then
	node_major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || printf '0')"
fi
if { [[ ! "$node_major" =~ ^[0-9]+$ ]] || ((node_major < 20)) || ! command -v openspec >/dev/null 2>&1; } && [[ -s "$HOME/.nvm/nvm.sh" ]]; then
	export NVM_DIR="$HOME/.nvm"
	# shellcheck source=/dev/null
	. "$NVM_DIR/nvm.sh"
	nvm use --silent 20 >/dev/null
fi
command -v openspec >/dev/null 2>&1 || {
	printf 'OpenSpec CLI is required for preflight.\n' >&2
	exit 1
}

run_gate "OpenSpec strict validation" openspec validate launch-platform-v1 --strict
run_gate "Wave workflow validation" bash scripts/validate-wave-workflow.sh
run_gate "Deployment configuration" bash scripts/validate-deployment-config.sh
run_gate "Rollout and rollback runbook" bash scripts/validate-rollout-runbook.sh
run_gate "Patch whitespace" git diff --check

printf '\nPlatform v1 preflight passed.\n'