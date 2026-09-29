#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

manifest="deploy/platform-v1/artifact.json"
version="$(node -e 'const value=require("./deploy/platform-v1/artifact.json").artifact_version; if (!/^\d+\.\d+\.\d+$/.test(value)) process.exit(1); process.stdout.write(value)')"
output_dir="${ARTIFACT_OUTPUT_DIR:-$repo_root/dist}"
artifact_name="gpu-platform-v${version}"
staging_root="$(mktemp -d)"
trap 'rm -rf "$staging_root"' EXIT

mkdir -p "$staging_root/$artifact_name/deploy"
cp mcp_server.py slurm_server.py "$staging_root/$artifact_name/"
cp -a deploy/platform-v1 "$staging_root/$artifact_name/deploy/"

mkdir -p "$output_dir"
tar \
	--sort=name \
	--mtime='UTC 1970-01-01' \
	--owner=0 \
	--group=0 \
	--numeric-owner \
	-czf "$output_dir/$artifact_name.tar.gz" \
	-C "$staging_root" \
	"$artifact_name"

sha256sum "$output_dir/$artifact_name.tar.gz" > "$output_dir/$artifact_name.tar.gz.sha256"
printf '%s\n' "$output_dir/$artifact_name.tar.gz" "$output_dir/$artifact_name.tar.gz.sha256"