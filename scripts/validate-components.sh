#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

registry="config/components.json"
[[ -f "$registry" ]] || { printf 'Missing %s\n' "$registry" >&2; exit 1; }

node -e '
const fs = require("fs");
const registry = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
if (registry.schema_version !== 1) throw new Error("unsupported schema_version");
for (const name of ["slurm", "ltx2", "dcgm"]) {
  const component = registry.components?.[name];
  if (!component) throw new Error(`missing component: ${name}`);
  for (const key of ["target_repo", "upstream", "commit", "checkout_version", "deployed_version", "candidate_version", "update_policy"]) {
    if (!(key in component)) throw new Error(`${name} is missing ${key}`);
  }
  if (!/^[0-9a-f]{40}$/.test(component.commit)) throw new Error(`${name} has an invalid commit`);
  for (const versionKey of ["deployed_version", "candidate_version"]) {
    const version = component[versionKey];
    if (!version || typeof version.status !== "string" || typeof version.note !== "string") {
      throw new Error(`${name}.${versionKey} lacks status or note`);
    }
  }
}
' "$registry"

while IFS='|' read -r name target_repo upstream branch expected_commit; do
	[[ -d "$target_repo/.git" ]] || { printf 'Missing checkout for %s: %s\n' "$name" "$target_repo" >&2; exit 1; }
	actual_upstream="$(git -C "$target_repo" remote get-url origin)"
	actual_branch="$(git -C "$target_repo" branch --show-current)"
	actual_commit="$(git -C "$target_repo" rev-parse HEAD)"
	[[ "$actual_upstream" == "$upstream" ]] || { printf '%s origin drifted\n' "$name" >&2; exit 1; }
	[[ "$actual_branch" == "$branch" ]] || { printf '%s branch drifted\n' "$name" >&2; exit 1; }
	[[ "$actual_commit" == "$expected_commit" ]] || { printf '%s commit drifted\n' "$name" >&2; exit 1; }
	printf 'PASS  %s checkout matches registry\n' "$name"
done < <(node -e '
const fs = require("fs");
const registry = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
for (const [name, component] of Object.entries(registry.components)) {
  console.log([name, component.target_repo, component.upstream, component.branch ?? "", component.commit].join("|"));
}
' "$registry")

printf 'Component registry is valid.\n'