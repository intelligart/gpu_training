#!/usr/bin/env bash

set -euo pipefail

endpoint="${MCP_ENDPOINT:-http://192.168.51.48:8766/mcp}"
headers_file="$(mktemp)"
body_file="$(mktemp)"
session_id=""

cleanup() {
	if [[ -n "$session_id" ]]; then
		curl --silent --show-error --max-time 5 \
			--request DELETE "$endpoint" \
			--header "Mcp-Session-Id: $session_id" >/dev/null || true
	fi
	rm -f "$headers_file" "$body_file"
}
trap cleanup EXIT

curl --fail --silent --show-error --max-time 15 \
	--dump-header "$headers_file" \
	--output "$body_file" \
	--request POST "$endpoint" \
	--header 'Content-Type: application/json' \
	--header 'Accept: application/json, text/event-stream' \
	--data-binary '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"gpu-platform-rollout-smoke","version":"1.0"}}}'

session_id="$(awk 'BEGIN { IGNORECASE=1 } /^mcp-session-id:/ { gsub("\r", "", $2); print $2; exit }' "$headers_file")"
[[ -n "$session_id" ]] || { printf 'MCP initialize returned no session ID.\n' >&2; exit 1; }
/usr/bin/grep -q '"protocolVersion":"2025-06-18"' "$body_file"

curl --fail --silent --show-error --max-time 15 \
	--output /dev/null \
	--request POST "$endpoint" \
	--header 'Content-Type: application/json' \
	--header 'Accept: application/json, text/event-stream' \
	--header "Mcp-Session-Id: $session_id" \
	--data-binary '{"jsonrpc":"2.0","method":"notifications/initialized"}'

curl --fail --silent --show-error --max-time 15 \
	--output "$body_file" \
	--request POST "$endpoint" \
	--header 'Content-Type: application/json' \
	--header 'Accept: application/json, text/event-stream' \
	--header "Mcp-Session-Id: $session_id" \
	--data-binary '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
/usr/bin/grep -q '"name":"submit_job"' "$body_file"
/usr/bin/grep -q '"name":"cluster_info"' "$body_file"

curl --fail --silent --show-error --max-time 20 \
	--output "$body_file" \
	--request POST "$endpoint" \
	--header 'Content-Type: application/json' \
	--header 'Accept: application/json, text/event-stream' \
	--header "Mcp-Session-Id: $session_id" \
	--data-binary '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"cluster_info","arguments":{}}}'
/usr/bin/grep -q '"isError":false' "$body_file"

curl --fail --silent --show-error --max-time 20 \
	--output "$body_file" \
	--request POST "$endpoint" \
	--header 'Content-Type: application/json' \
	--header 'Accept: application/json, text/event-stream' \
	--header "Mcp-Session-Id: $session_id" \
	--data-binary '{"jsonrpc":"2.0","id":31,"method":"tools/call","params":{"name":"gpu_status","arguments":{}}}'
/usr/bin/grep -q '"isError":false' "$body_file"

curl --fail --silent --show-error --max-time 15 \
	--output "$body_file" --request POST "$endpoint" \
	--header 'Content-Type: application/json' \
	--header 'Accept: application/json, text/event-stream' \
	--header "Mcp-Session-Id: $session_id" \
	--data-binary '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_onboarding_guide","arguments":{}}}'
/usr/bin/grep -q '"isError":false' "$body_file"
/usr/bin/grep -q 'Guide version: 1.0.0' "$body_file"

curl --fail --silent --show-error --max-time 15 \
	--output "$body_file" --request POST "$endpoint" \
	--header 'Content-Type: application/json' \
	--header 'Accept: application/json, text/event-stream' \
	--header "Mcp-Session-Id: $session_id" \
	--data-binary '{"jsonrpc":"2.0","id":5,"method":"resources/list","params":{}}'
/usr/bin/grep -q 'slurm://guides/onboarding' "$body_file"

curl --fail --silent --show-error --max-time 15 \
	--output "$body_file" --request POST "$endpoint" \
	--header 'Content-Type: application/json' \
	--header 'Accept: application/json, text/event-stream' \
	--header "Mcp-Session-Id: $session_id" \
	--data-binary '{"jsonrpc":"2.0","id":51,"method":"resources/read","params":{"uri":"slurm://guides/onboarding"}}'
/usr/bin/grep -q '"contents":' "$body_file"
/usr/bin/grep -q 'Guide version: 1.0.0' "$body_file"

curl --fail --silent --show-error --max-time 15 \
	--output "$body_file" --request POST "$endpoint" \
	--header 'Content-Type: application/json' \
	--header 'Accept: application/json, text/event-stream' \
	--header "Mcp-Session-Id: $session_id" \
	--data-binary '{"jsonrpc":"2.0","id":6,"method":"prompts/list","params":{}}'
/usr/bin/grep -q 'slurm_onboarding' "$body_file"

curl --fail --silent --show-error --max-time 15 \
	--output "$body_file" --request POST "$endpoint" \
	--header 'Content-Type: application/json' \
	--header 'Accept: application/json, text/event-stream' \
	--header "Mcp-Session-Id: $session_id" \
	--data-binary '{"jsonrpc":"2.0","id":61,"method":"prompts/get","params":{"name":"slurm_onboarding"}}'
/usr/bin/grep -q '"messages":' "$body_file"
/usr/bin/grep -q 'Guide version: 1.0.0' "$body_file"

curl --fail --silent --show-error --max-time 5 \
	--output /dev/null \
	--request DELETE "$endpoint" \
	--header "Mcp-Session-Id: $session_id"
session_id=""

printf 'MCP initialize, discovery, cluster/GPU queries, onboarding tool/resource/prompt reads passed: %s\n' "$endpoint"