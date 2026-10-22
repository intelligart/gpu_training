#!/usr/bin/env bash

set -euo pipefail

target="${WAVE_GH_REPO:-}"

if [[ -z "$target" ]]; then
	printf 'ERROR: WAVE_GH_REPO is required for GitHub mutations.\n' >&2
	exit 2
fi

if [[ ! "$target" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
	printf 'ERROR: WAVE_GH_REPO must use owner/repo form: %s\n' "$target" >&2
	exit 2
fi

case "${target,,}" in
	schedmd/slurm|lightricks/ltx-2|nvidia/dcgm)
		printf 'ERROR: internal Wave mutations must not target upstream %s.\n' "$target" >&2
		exit 3
		;;
esac

printf 'Wave GitHub target: %s\n' "$target"