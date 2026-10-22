# GPU Platform Collaboration Instructions

Before changing this repository, read the Wave manual at
`../.claude/CLAUDE.md` and `../SUB_AGENT_CHEATSHEET.md`. For OpenSpec work, read
every context file returned by the OpenSpec workflow before implementation.

Use this repository as the planning home for new internal Slurm, LTX-2, DCGM,
and training changes. Do not copy the active Slurm OpenSpec changes here; they
remain in the Slurm planning home until archived.

Keep each implementation inside its assigned target repository and file lane.
Preserve unrelated worktree changes and attach a rerunnable validation command
to every completion claim. An implementer may mark work fixed, but only a
reporter or reviewer may mark it verified.

Require an explicit `WAVE_GH_REPO` for every GitHub mutation, pass
`--repo "$WAVE_GH_REPO"`, preview the mutation, and refuse internal Wave changes
against `SchedMD/slurm`, `Lightricks/LTX-2`, or `NVIDIA/DCGM`.

Training, model execution, and Python training scripts requested through an AI
agent must use the Slurm MCP submission tool. Never fall back to local execution
or direct raw submission API calls when MCP is unavailable.

Do not restart services, change live `/etc/slurm`, modify firewall or spool
state, switch endpoints, or submit canary jobs without explicit Owner approval
and a stated node, impact, validation, and rollback plan.