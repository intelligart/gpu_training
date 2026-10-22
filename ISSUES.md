# GPU Platform Issues

本文件是尚未形成 OpenSpec change 的 bug 與小型修正之本地權威來源。跨 repo 功能、
架構變更、deployment 或 production rollout 應建立 OpenSpec change。

## 狀態

- `open`：已記錄但尚未認領
- `in-progress`：已由一位 contributor 認領
- `fixed`：實作與 focused validation 已通過
- `verified`：由 reporter/reviewer 重跑驗證

## Active

### #1 - MCP gpu_status 未格式化 nested device payload

- Status: open
- Reporter: GitHub Copilot，2026-09-30
- Target repo / files: `gpu_training`; `mcp_server.py`、focused MCP tests
- Reproduction: live `GET /gpu-status` 對每個 node 回傳 `{state, gpus}`，但 MCP `gpu_status` 只處理 top-level list 或 `{error}`；目前 tool output 只有 node 標題，沒有 model、VRAM、utilization 或 process rows
- Expected: MCP 逐 node 顯示 state 與 backend `gpus` 中每張 device 的 index、model、VRAM、utilization 及 process summary，並保留 error behavior
- Acceptance command: 透過 Slurm MCP 執行 focused mocked formatter test，再執行 protocol-aware MCP `gpu_status` read-only smoke；A6000 node 必須出現 device rows

### #2 - Slurm idle 狀態與實際 GPU process occupancy 不一致

- Status: open
- Reporter: GitHub Copilot，2026-09-30
- Target repo / files: cluster operations；後續 OpenSpec security/resource-accounting change
- Reproduction: `squeue` 無 jobs 且 `scontrol show node ia-ai-server-{4,5}` 為 `IDLE`/無 `AllocTRES`，但 live GPU telemetry 顯示 server-5 兩張 A6000 約 42 GiB、100% utilization，server-4 也有非零 Python process/VRAM
- Expected: 可被 Slurm allocation 的 GPU 不存在未歸屬 process；若合法外部 workload 必須由 policy 排除、reserve 或 drain，scheduler availability 不得誤導 submission
- Acceptance command: Owner 核准 node/impact/rollback 後，比對 `squeue`、`scontrol show node`、read-only GPU telemetry 與 process-to-job mapping；不得以未核准 kill/restart 作為修正，最後以低風險 MCP canary 驗證無 collision

## 條目格式

```markdown
### #N - 標題

- Status: open
- Reporter:
- Target repo / files:
- Reproduction:
- Expected:
- Acceptance command:
```