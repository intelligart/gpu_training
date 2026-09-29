#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

runbook="${RUNBOOK_PATH:-docs/platform-v1-rollout.md}"
[[ -s "$runbook" ]] || { printf 'Missing rollout runbook.\n' >&2; exit 1; }

required_patterns=(
	'Target node'
	'Maintenance window'
	'Owner approval'
	'Expected impact'
	'Artifact SHA-256'
	'Previous release'
	'Backup directory'
	'Rollback command'
	'## Rollout'
	'## Rollback'
	'read-only health'
	'127.0.0.1:8765/health'
	'MUST NOT'
	'SQLite submission history'
	'run directories'
	'logs'
	'Slurm spool'
	'既有 jobs'
)

for pattern in "${required_patterns[@]}"; do
	if ! /usr/bin/grep -Fq "$pattern" "$runbook"; then
		printf 'Runbook is missing required content: %s\n' "$pattern" >&2
		exit 1
	fi
done

forbidden_patterns=(
	'rm -rf /var/spool/slurm'
	'rm -rf /storage/Internal_NAS/logs'
	'rm -rf /storage/Internal_NAS/slurm-runs'
	'rm -f /storage/SSD2/hank/gpu_training/slurm_history.db'
	'scancel '
	'systemctl restart slurmctld'
	'systemctl restart slurmd'
)

for pattern in "${forbidden_patterns[@]}"; do
	if /usr/bin/grep -Fq "$pattern" "$runbook"; then
		printf 'Runbook contains a forbidden destructive operation: %s\n' "$pattern" >&2
		exit 1
	fi
done

printf 'Rollout runbook is valid.\n'