#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

required_files=(
	deploy/platform-v1/artifact.json
	deploy/platform-v1/python-version
	deploy/platform-v1/requirements-service.lock
	deploy/platform-v1/systemd/slurm-api.service
	deploy/platform-v1/systemd/slurm-api-vpn-bind.conf
	deploy/platform-v1/systemd/slurm-mcp.service
	deploy/platform-v1/systemd/slurm-mcp-vpn-backend.conf
	deploy/platform-v1/nginx/gpu-platform.conf
	deploy/platform-v1/smoke-mcp.sh
	scripts/build-platform-v1-artifact.sh
)

for file in "${required_files[@]}"; do
	[[ -s "$file" ]] || { printf 'Missing deployment file: %s\n' "$file" >&2; exit 1; }
done

node <<'NODE'
const fs = require('fs');
const manifest = JSON.parse(fs.readFileSync('deploy/platform-v1/artifact.json', 'utf8'));
if (manifest.schema_version !== 1) throw new Error('unsupported artifact schema');
if (!/^\d+\.\d+\.\d+$/.test(manifest.artifact_version)) throw new Error('invalid artifact version');
if (manifest.python_version !== fs.readFileSync('deploy/platform-v1/python-version', 'utf8').trim()) {
  throw new Error('Python version files disagree');
}
if (manifest.services['slurm-api'].bind !== '127.0.0.1:8765') {
	throw new Error(`unexpected API bind: ${manifest.services['slurm-api'].bind}`);
}
if (manifest.services['slurm-mcp'].bind !== '192.168.51.48:8766') {
	throw new Error(`unexpected MCP pilot bind: ${manifest.services['slurm-mcp'].bind}`);
}
const vpnProfile = manifest.profiles?.trusted_vpn;
if (vpnProfile?.api_bind !== '192.168.51.48:8765') {
	throw new Error(`unexpected trusted VPN API bind: ${vpnProfile?.api_bind}`);
}
if (vpnProfile?.mcp_bind !== '192.168.51.48:8766') {
	throw new Error(`unexpected trusted VPN MCP bind: ${vpnProfile?.mcp_bind}`);
}
if (vpnProfile?.api_drop_in !== 'deploy/platform-v1/systemd/slurm-api-vpn-bind.conf' ||
	vpnProfile?.mcp_drop_in !== 'deploy/platform-v1/systemd/slurm-mcp-vpn-backend.conf') {
	throw new Error('trusted VPN profile references unexpected drop-ins');
}
if (!manifest.gateway.bind.startsWith('127.0.0.1:')) {
	throw new Error(`non-loopback gateway example: ${manifest.gateway.bind}`);
}
NODE

if /usr/bin/grep -vE '^(#.*|$|[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+)$' deploy/platform-v1/requirements-service.lock | /usr/bin/grep -q .; then
	printf 'Service dependency lock contains an unpinned requirement.\n' >&2
	exit 1
fi

for package in fastapi httpx mcp pydantic starlette uvicorn; do
	if ! /usr/bin/grep -qiE "^${package}==" deploy/platform-v1/requirements-service.lock; then
		printf 'Missing direct service dependency pin: %s\n' "$package" >&2
		exit 1
	fi
	done

/usr/bin/grep -q -- '--host 127.0.0.1 --port 8765' deploy/platform-v1/systemd/slurm-api.service
/usr/bin/grep -q -- '--host 192.168.51.48 --port 8766' deploy/platform-v1/systemd/slurm-mcp.service
/usr/bin/grep -q -- '--host 192.168.51.48 --port 8765' deploy/platform-v1/systemd/slurm-api-vpn-bind.conf
/usr/bin/grep -q -- 'SLURM_API_URL=http://192.168.51.48:8765' deploy/platform-v1/systemd/slurm-mcp-vpn-backend.conf

if /usr/bin/grep -Eq -- '--host (0\.0\.0\.0|::)' deploy/platform-v1/systemd/*.service; then
	printf 'Service unit contains an uncontrolled listener.\n' >&2
	exit 1
fi

if /usr/bin/grep -Eq 'listen[[:space:]]+(0\.0\.0\.0:|\[::\]:|80;|443;)' deploy/platform-v1/nginx/gpu-platform.conf; then
	printf 'Reverse proxy example contains an uncontrolled listener.\n' >&2
	exit 1
fi
/usr/bin/grep -q 'listen 127.0.0.1:8443 ssl;' deploy/platform-v1/nginx/gpu-platform.conf

bash -n deploy/platform-v1/smoke-mcp.sh

systemd-analyze verify deploy/platform-v1/systemd/slurm-api.service deploy/platform-v1/systemd/slurm-mcp.service >/dev/null

artifact_output="$(mktemp -d)"
trap 'rm -rf "$artifact_output"' EXIT
ARTIFACT_OUTPUT_DIR="$artifact_output" bash scripts/build-platform-v1-artifact.sh >/dev/null
artifact="$(find "$artifact_output" -maxdepth 1 -type f -name 'gpu-platform-v*.tar.gz' -print -quit)"
[[ -n "$artifact" ]]
sha256sum --check "$artifact.sha256" >/dev/null

printf 'Deployment configuration is valid.\n'