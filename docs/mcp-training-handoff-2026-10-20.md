# Slurm MCP training handoff - 2026-10-20

## Purpose and confirmed outcome

This is a curated record of the recovery and training conversation, not a
verbatim transcript. The next experiment is newcomer onboarding through a
separate MCP client/profile and an explicitly approved identity model.
No new account has been created by this work.

The principal acceptance result is **job 545**: MCP prepared a fixed Git
revision and directly launched the official LTX training entry point, without
calling a separately copied NAS runner or checking an input checksum manifest.
It completed five real LoRA training steps and saved a validated checkpoint.
This establishes a working smoke-training pipeline, not model quality or
convergence.

## Repository, installation, and runtime boundaries

- Slurm source checkout: `/home/hank/Code/slurm`. This conversation did not
  modify Slurm C source or build/install a new Slurm version.
- Platform source checkout: `/storage/SSD2/hank/gpu_training`. The GPU telemetry
  adapter fix belongs here, not in upstream Slurm.
- LTX source checkout: `/home/hank/Code/LTX-2`. Unrelated untracked files were
  preserved; no upstream LTX source patch was required for successful training.
- Installed Slurm runtime remains 21.08.5. Source checkout version, installed
  binaries, runtime daemons, and live configuration are separate facts.
- Platform runtime is release 1.0.1 plus an MCP adapter hotfix. Do not identify
  the modified installed adapter solely by the original release tarball hash.
- Existing onboarding, legacy HTTP, deployment, and other dirty worktree changes
  are separate from the narrow GPU telemetry commit.

## Server6 recovery

`AI-Server-6` was DOWN/NOT_RESPONDING. Investigation established:

1. The host has six GPUs, but live configuration declared seven and referenced
   nonexistent `/dev/nvidia6`.
2. Its installed daemon reads configuration under `/opt/slurm-21.08.5/etc/`;
   updating only `/etc/slurm` would not update that daemon's effective files.
3. Both `slurmd.service` and `slurmd-21.08.5.service` were enabled and competed
   over daemon resources.

The Owner separately approved the maintenance and ran privileged handoff
commands. The final repair aligned effective configuration and mirrors to six
GPUs, disabled the duplicate `slurmd.service`, and retained
`slurmd-21.08.5.service`. The controller restart required for this file-bound
GRES change was also separately approved.

The node was first restored with DRAIN retained; the Owner subsequently
approved UNDRAIN. Later training jobs demonstrate that it became schedulable.
The repair did not clear spool state, reset GPUs, or kill manual workloads.

Recovery backups:

- Controller: `/var/backups/slurm-server6-six-gpus-QMmo1gJm`
- Successful worker repair:
  `/var/backups/slurm-server6-single-worker-G1srk4HT`

Detailed operational evidence is in the Slurm checkout's `TEAM_LOG.md`.
These live changes are not Slurm source changes and are not automatically
captured by a Git commit in this platform repository.

## MCP GPU telemetry hotfix

The live backend returned nested node/device data, MB metrics
(`mem_used_mb`, `mem_total_mb`, `util_pct`), and process summaries as strings.
The adapter could omit devices, misreport metrics, or raise
`AttributeError: 'str' object has no attribute 'get'`.

The focused change:

- Supports nested node state/devices and legacy device lists.
- Handles MB metrics and legacy GB metrics without mixing units.
- Handles process-summary strings and legacy process-object lists.
- Reports malformed process telemetry explicitly.
- Adds five GPU regression tests and a real `gpu_status` call to the smoke test.
- Does not change the submission schema or add an identity-isolation mechanism.

CPU-only MCP regression job 541 passed all 12 focused submission tests,
with authoritative Slurm state COMPLETED and exit code `0:0`.
The Owner applied the MCP-only hotfix; live GPU queries then succeeded.

Installed adapter SHA-256 at deployment:

```text
450d9e9c79918bbf949ccba714cec357ce43cec89f8d3040c23dd40570ffaf7e
```

That digest identifies the complete installed candidate, which also includes
other release work; it is not the digest of a GPU-only Git patch.

## Training execution record

All model execution was submitted through MCP. There was no local training or
raw HTTP submission fallback.

| Job | Purpose | Result |
| --- | --- | --- |
| 541 | CPU-only GPU adapter regression | COMPLETED, exit 0; 12 tests |
| 542 | Isolated Python 3.12 LTX environment setup | COMPLETED, exit 0; 00:06:29 |
| 543 | First five-step training attempt | FAILED, exit 1; 0/5 steps |
| 544 | Rebuild text conditions, then train | COMPLETED, exit 0; 00:03:37; 5/5 steps |
| 545 | Direct Git entry point plus NAS YAML; no external runner | COMPLETED, exit 0; 00:00:47; 5/5 steps |

### Source, environment, and data

- Repository: `git@github.com:Lightricks/LTX-2.git`
- Fixed commit: `a95ab856bf29407b6b066ede0abe1846050db56c`
- Environment:
  `/storage/Internal_NAS/hank/venvs/server6-ltx25-smoke-py312`
- Python 3.12.3, Torch 2.11.0+cu128, LTX core/trainer 1.3.0.
- The user's actual configuration is LTX-2.5 22B, not LTX-2 19B.
- Transformer:
  `/storage/Internal_NAS/Checkpoints/LTX-2_Release/v2.5/checkpoints/ltx-2.5-22b-dev-transformer-bf16.safetensors`
- Text encoder:
  `/storage/Internal_NAS/Checkpoints/LTX-2_Release/v2.5/text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors`
- Video/audio VAEs are under the same release's `vae/` directory.
- Original dataset:
  `/storage/Internal_NAS/hank/Disney-VideoGeneration-Dataset`

Job 543 showed that the old cached conditions were not compatible with the
current LTX-2.5 path: legacy `prompt_embeds` had width 4096 and were duplicated
for both modalities, while the audio connector required width 2048.
No successful training step or checkpoint was produced by that job.

After separate approval, job 544 used the official `process_captions.py` and
the existing Gemma4 encoder to regenerate 69 conditions in an independent
directory. It validated video width 4096, audio width 2048, finite features,
attention masks, and one-to-one latent filenames. Original latents were
referenced without modification. Do not truncate embeddings or substitute
synthetic features to bypass the mismatch.

Reusable prepared data:

```text
/storage/Internal_NAS/hank/ltx25-smoke-1420cdde/job-544/prepared
```

### Direct command accepted by job 545

The Owner explicitly selected **Git program plus NAS YAML**, rather than
requiring the YAML itself to be committed in the upstream Git repository.

MCP `submit_job` arguments:

```json
{
  "username": "hank",
  "repo_url": "git@github.com:Lightricks/LTX-2.git",
  "branch": "a95ab856bf29407b6b066ede0abe1846050db56c",
  "venv": "/storage/Internal_NAS/hank/venvs/server6-ltx25-smoke-py312",
  "gpu": 1,
  "mem": "128G",
  "nodelist": "AI-Server-6",
  "job_name": "hank-ltx25-direct-1420cdde",
  "command": "timeout --signal=TERM --kill-after=30 1800 python -u packages/ltx-trainer/scripts/train.py /storage/Internal_NAS/hank/ltx25-direct-1420cdde/configs/smoke-20261020-0040.yaml"
}
```

This is a historical successful invocation, **not a safe resubmission template**:
its output directory already exists. Prepare a new YAML with a fresh output
directory and obtain approval before another submission.

The platform-generated Slurm batch script activates the venv, changes to the
per-submission Git source, and executes that command. A generated batch script
is still required by Slurm; the user does not need a separate copied runner.

Job 545 details:

- Submission: `e093b6b4715941eb89b72221d6c863cf`
- Source:
  `/storage/Internal_NAS/slurm-runs/hank/e093b6b4715941eb89b72221d6c863cf`
- Exact log:
  `/storage/Internal_NAS/logs/hank/e093b6b4715941eb89b72221d6c863cf/slurm_545.out`
- YAML:
  `/storage/Internal_NAS/hank/ltx25-direct-1420cdde/configs/smoke-20261020-0040.yaml`
- Output:
  `/storage/Internal_NAS/hank/ltx25-direct-1420cdde/run-20261020-0040`
- Settings: rank16 LoRA, batch1, five steps, bf16/int8-quanto, gradient
  checkpointing, adamw8bit, no resume, no validation-video generation.
- Allocation: server6, one GPU, four CPUs, 128G host RAM.
- The 30-minute bound is a **command timeout**; the generated Slurm allocation
  still showed the backend's default eight-hour TimeLimit.
- Final displayed loss: 0.2777. Trainer-reported peak GPU memory: 28.62 GB.
- Checkpoint: `checkpoints/lora_weights_step_00005.safetensors`,
  214240000 bytes, 2304 adapter tensors, 106954752 parameters.
- Complete BF16 payload finite check passed; minimal step-5 training state was
  also saved. GPU0 returned to 0% utilization after the job.
- Checkpoint SHA-256:
  `b2e503ab615e1dd2d25e9970000c62bad03afc4391d3c6f9c8cb8a9a6acb2c2d`

Read-only verification commands:

```bash
scontrol show job 545 -o
scontrol write batch_script 545 -
grep -E 'Training 5/5|Peak GPU memory|Lora weights for step' \
  /storage/Internal_NAS/logs/hank/e093b6b4715941eb89b72221d6c863cf/slurm_545.out
sha256sum \
  /storage/Internal_NAS/hank/ltx25-direct-1420cdde/run-20261020-0040/checkpoints/lora_weights_step_00005.safetensors
```

Slurm may eventually purge historical job metadata. Exact logs and output
artifacts, rather than indefinite `scontrol` retention, provide durable evidence.

## Explaining MCP usage to the next user

1. Obtain the approved MCP endpoint and any required VPN access from the
   Operator. Keep endpoint/credential configuration machine-local.
2. Configure a compatible Streamable HTTP MCP client. Installing a Slurm client
   or another MCP server on the user's machine is not required.
3. Call `get_onboarding_guide`, `cluster_info`, `list_venvs`, and `gpu_status`
   for read-only discovery. Slurm IDLE does not detect manual GPU workloads.
4. Provide an approved audit label, Git repo/ref, command, compatible venv,
   prepared data/configuration, resource request, and fresh output path.
5. Show the complete plan and obtain approval, then call `submit_job` once.
   These are MCP tool arguments, not a raw HTTP `/submit` request body.
6. Record submission/job IDs and source commit; use `get_logs` for the exact
   job. Queue disappearance alone is not proof of success. There is currently
   no independent MCP `job_status` tool; ask the Operator for authoritative
   terminal state when needed.

The live tools-only onboarding entry point was checked during this conversation.
That does not mean a newcomer has completed onboarding or submitted a job yet.

## Identity decision required before the new-account experiment

The Owner accepted a trusted-team/shared-account pilot. Current `username`
values are audit labels, **not authentication or per-user Unix execution**.
There is no complete cross-user sandbox or forced dataset/venv isolation.

A concrete mismatch was observed:

- Controller: `hank` is UID/GID 1004.
- Server6: local `hank` is UID/GID 1003; numeric UID1004 maps to `ian.lin`.
- Slurm jobs ran with numeric UID1004 on server6.
- The Owner approved a writable NAS environment instead of changing UID/GID/ACL.

The next session must first distinguish:

- **New MCP client/profile and audit label:** demonstrates newcomer workflow
  while retaining the current shared execution model.
- **Real Unix user and per-user execution:** requires a separate approved
  design and rollout covering consistent UID/GID, authentication/authorization,
  Slurm execution identity, NAS permissions, and environment access. Changing
  only the `username` request field does not implement this.

Do not create accounts, change permissions, restart services, or submit
additional jobs solely because this handoff exists. Each live action still
requires its own node/impact/rollback approval.

## Remaining boundaries and follow-up

- The simple Hank matrix demo was not submitted in this conversation; earlier
  occupancy checks stopped it. Do not claim that separate acceptance is done.
- Newcomer onboarding and training are still pending.
- Previously completed five-step runs are not authorization for another run.
- The backend's inherited WorkDir is absent on workers, producing a warning
  before the script changes to its correct NAS Git source. This remains unfixed.
- Job 544 logged NFS multiprocessing temporary-file cleanup errors after caption
  processing; all rebuilt-data/training checks subsequently passed. Its actual
  staged runner was preserved. A session-only follow-up runner uses local
  `/tmp`, but that revision was not submitted as another job.
- Do not infer that source checkout state equals a release, or that every
  dirty/untracked file belongs to this conversation.
