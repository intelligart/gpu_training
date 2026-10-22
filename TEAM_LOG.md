# GPU Platform Team Log

最新紀錄放在最上方。每個 lane 完成或 blocked 時留下可重跑證據；實作者不得自行
將工作標記為 verified。

## 2026-09-30T16:48Z · GitHub Copilot · trusted-VPN Dashboard/API bind

- Change / task: Owner-approved v1 network profile follow-up；GitHub issue 尚未發布
- Result: implementation fixed；完整 Dashboard/API 已綁 `192.168.51.48:8765` 並保留 submit/cancel，MCP 維持 `192.168.51.48:8766`；非實作者 reviewer verification pending
- Target repo / files: `gpu_training`; `deploy/platform-v1/artifact.json`、`deploy/platform-v1/systemd/*vpn*.conf`、`scripts/validate-deployment-config.sh` 與 v1 使用/交付文件
- Rollout: 在 `ia-ai-server-5` 安裝兩個 systemd drop-ins，MCP backend 同步改為 private-IP API；只重啟 `slurm-api.service`、`slurm-mcp.service`
- Validation: `bash deploy/platform-v1/smoke-mcp.sh && curl --fail http://192.168.51.48:8765/ && ss -ltn '( sport = :8765 or sport = :8766 )' && scontrol ping` -> MCP initialize/discovery/read-only cluster query 通過，Dashboard HTTP 200，兩個 listener 精確綁 private IP，controller UP
- Validation: `./scripts/validate-deployment-config.sh && ./scripts/validate-wave-workflow.sh && git diff --check` -> deployment artifact valid，Wave 0 errors/0 warnings，whitespace check 通過
- Notes: backup `/opt/gpu-platform/backups/20261001T003959CST-vpn-api-bind`；rollback 為移除兩個 drop-ins、daemon-reload 並只重啟 API/MCP。`slurmctld` 未重啟，`NRestarts=0`；完整 API 目前沒有 SSO/RBAC 或 per-user ownership enforcement，不得公開到 Internet。實作者未標記 verified

## 2026-09-29T18:16Z · GitHub Copilot · v1 live rollout 與 MCP CUDA canary

- Change / task: `launch-platform-v1`, tasks 4.4、4.5；GitHub issue 尚未發布
- Result: implementation fixed；OpenSpec progress `17/17`；非實作者 reviewer verification pending
- Target repo / files: `gpu_training`; `docs/platform-v1-acceptance-2026-09-30.md`、`docs/platform-v1-rollout.md`、`openspec/changes/launch-platform-v1/tasks.md`
- Rollout: `ia-ai-server-5` 僅切換 `slurm-api/slurm-mcp` 至 `/opt/gpu-platform/releases/1.0.0`；API `127.0.0.1:8765`、MCP `192.168.51.48:8766`，artifact SHA-256 `0a01d671cef4267fa86206f37d338d7994d29183ddb64b0b189df7f130a377e1`
- Validation: `curl http://127.0.0.1:8765/health && bash /opt/gpu-platform/current/deploy/platform-v1/smoke-mcp.sh && systemctl is-active slurm-api.service slurm-mcp.service slurmctld.service && scontrol ping` -> API v1.0.0、MCP initialize/discovery/cluster query 通過，三個 services active，controller UP
- Canary: 僅透過 v1 MCP 使用 `hank`、`yujong`、1 GPU、`ia-ai-server-5` 提交 CUDA smoke；submission `69f58c3caf8748a295c57f8e8dc22a23`、job `534`、commit `6046d6869749ac07491100aa60cec0018ac0184b`
- Validation: `scontrol show job -dd 534` 與 MCP `get_logs(job_id="534")` -> `COMPLETED`、`ExitCode=0:0`、RTX A6000、CUDA result `2048.0`，exact metadata/run/script/log paths 一致
- Notes: rollback backup `/opt/gpu-platform/backups/20260930T015008-CST` 與 immutable previous release `/opt/gpu-platform/releases/legacy-6046d686` 保留；未重啟 Slurm daemon、未刪除 history/run/log/spool，實作者未標記 verified

## 2026-09-28T05:14Z · GitHub Copilot · MCP submission、併發隔離與 v1 離線 rollout

- Change / task: `launch-platform-v1`, tasks 2.1、2.3、3.1-3.5、4.1-4.3；GitHub issue 尚未發布
- Result: offline implementation fixed；reviewer verification pending；OpenSpec progress `15/17`
- Target repo / files: `gpu_training`; `mcp_server.py`、`slurm_server.py`、`tests/**`、`deploy/platform-v1/**`、`scripts/**`、`docs/platform-v1-rollout.md`
- Validation: 透過 Slurm MCP 使用 `username=hank`、`venv=yujong`、`nodelist=ia-ai-server-5` 執行 `cd /storage/SSD2/hank/gpu_training && PYTHON_BIN=python ./scripts/preflight-v1.sh`（job `528`）-> 20 tests passed，OpenSpec strict valid，Wave 0 errors/0 warnings，deployment/runbook/whitespace gates passed
- Validation: 透過 Slurm MCP 在 disposable venv 安裝 `deploy/platform-v1/requirements-service.lock`（job `531`）-> `pip check`、service imports 與 normalized `pip freeze` exact diff passed，temporary directory removed
- Validation: `openspec validate launch-platform-v1 --strict && ./scripts/validate-wave-workflow.sh && ./scripts/validate-deployment-config.sh && ./scripts/validate-rollout-runbook.sh && git diff --check` -> valid
- Notes: 未修改 live `/etc`、service、firewall 或 Slurm spool；tasks 4.4/4.5 仍等待 Owner 另行核准 target node、impact、validation、rollback，以及 canary 的 username/venv/GPU/fixture。實作者未標記 verified。

## 2026-09-24T22:57Z · GitHub Copilot · Wave control plane migration

- Change / task: `launch-platform-v1`, lane 1, GitHub issue not yet published
- Result: completed locally; reviewer verification pending
- Target repo / files: `gpu_training`; `.claude/**`, `.github/**`, `openspec/**`, `scripts/**`, trackers, `config/components.json`
- Validation: `openspec validate launch-platform-v1 --strict && ./scripts/validate-wave-workflow.sh` -> valid, 0 errors and 0 warnings
- Validation: validate both active changes from `/home/hank/Code/slurm` with `--strict` -> `dashboard-gpu-status` and `slurm-upgrade-26` valid in place
- Notes: GitHub publication is blocked until `gh` is authenticated and `WAVE_GH_REPO` names an internal repository; no GitHub or live cluster mutation was performed.

## Entry Format

```markdown
## YYYY-MM-DDTHH:MMZ · <agent> · <mission>

- Change / task: <change>, <task/lane>, <owner/repo>#<issue>
- Result: <completed, blocked, or inconclusive>
- Target repo / files: <paths>
- Validation: `<rerunnable command>` -> <key result>
- Notes: <risk, rollback, or follow-up>
```