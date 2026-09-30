# Slurm GPU Cluster MCP 使用說明

MCP Server 讓 Claude、GitHub Copilot、ChatGPT 與後續 AI client 透過同一條受控路徑使用 Slurm：

```text
AI client -> trusted private-LAN MCP endpoint -> internal adapter -> Slurm
```

## 上線狀態

GPU Platform v1.0.0 已在 `ia-ai-server-5` 上線。MCP endpoint 是 `http://192.168.51.48:8766/mcp`；Owner 核准的完整 Dashboard/API 綁定 controller private interface 的 port `8765`，限 trusted VPN 使用並保留 submit/cancel。Read-only MCP smoke 與 1-GPU CUDA canary job `534` 已通過，實作者標示 fixed；非實作者 reviewer verification pending。

## 使用政策

- Training、模型執行與 Python training script 一律呼叫 MCP `submit_job`。
- MCP 無法連線或 submission 失敗時必須停止，不得在 client 主機本機執行或改呼叫 raw backend。
- `username`、`venv`、`command` 在 MCP tool schema 中都是必填；agent 不得猜測。
- 成功回應必須包含 `submission_id`、Slurm `job_id` 與初始 `status`。
- Endpoint、token 與憑證只放 machine-local secret/config，不提交到 repository。
- v1 只允許 trusted internal network/VPN/gateway，不得公開到 Internet。

日常 code、dataset、venv 與不同 GPU task flow 見 [工程師使用指南](docs/user-guide.md)。完整部署流程見 [工程師交付與部署指南](docs/platform-v1-engineer-handoff.md)。Claude、Copilot 與 ChatGPT 的共同設定契約見 [AI training integration contract](docs/agent-training-integration.md)。

## Client 設定

目前 direct-LAN pilot 的 Claude Code 設定使用 local-scope stdio bridge，避免 unauthenticated remote endpoint 被 Claude 誤判為 OAuth connector：

```json
{
  "mcpServers": {
    "slurm-gpu-cluster": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://192.168.51.48:8766/mcp", "--allow-http"]
    }
  }
}
```

需要 Node.js 與 `npx`。此明文 HTTP profile 只核准用於受信任的 VPN/private network；不得從 Internet 暴露。未來啟用 HTTPS gateway 後移除 `--allow-http`。

VS Code Copilot 的 machine-local workspace 設定：

```json
{
  "servers": {
    "slurmGpuCluster": {
      "type": "http",
      "url": "http://192.168.51.48:8766/mcp"
    }
  }
}
```

儲存後重新載入 client，確認 tool picker 可看到 `cluster_info`、`list_venvs` 與 `submit_job`。VS Code Copilot、ChatGPT 與其他 client 都只註冊管理員提供的 MCP endpoint。Client 不支援 private HTTP remote MCP 時，該 client 暫不支援 training，不建立 raw API fallback。這些設定只放使用者本機，不提交至公開或共用的 source repository。

## 新增使用者 onboarding

Operator 先提供並確認：

1. VPN/private-LAN access，以及 `192.168.51.48:8766` 的 network route。
2. 使用者的固定 `username` audit label。
3. 核准的 shared `venv` 名稱。
4. 可讀取的 Git repository、dataset 與 checkpoint path。
5. 可使用的 GPU 數量、memory 與 node policy。

目前沒有 per-user authentication 或 Slurm ownership isolation；所有 submission 由 service identity `hank` 執行，`username` 只用於 audit metadata。只能加入受信任的 VPN 成員，不得把 endpoint 公開到 Internet。

使用者完成 client 設定後，先貼上 read-only 驗證範本：

```text
我的 username 是 <username>，核准的 venv 是 <venv>。
只使用 slurm-gpu-cluster MCP，不要執行本機 training，也不要使用 raw API fallback。
請呼叫 cluster_info、gpu_status、list_venvs，整理目前 cluster、GPU 與 venv 狀態。
這次不要提交或取消任何 job。
```

若工具清單或 read-only 結果不完整，停止 onboarding 並通知 Operator，不要嘗試 raw HTTP fallback。

## 對話範本

1-GPU smoke：

```text
我的 username 是 <username>，venv 是 <venv>。
只使用 slurm-gpu-cluster MCP，從 <repo-url> 的 commit <full-commit-sha>，
使用 1 張 GPU、<memory> memory 執行：
<smoke-command>
job name 是 <username>-smoke。
提交成功後回報 submission_id、job_id、status 與固定的 source commit。
```

2-GPU training：

```text
我的 username 是 <username>，venv 是 <venv>。
只使用 slurm-gpu-cluster MCP，從 <repo-url> 的 commit <full-commit-sha>，
使用 2 張 GPU、<memory> memory 執行：
<distributed-training-command>
job name 是 <username>-<experiment>。
除非 Operator 已指定，請不要自行設定 nodelist。
提交成功後回報 submission_id、job_id、status 與固定的 source commit。
```

查詢狀態與 log：

```text
只使用 Slurm MCP 查詢 job <job-id>；先回報 queue/status，再用 get_logs 讀取 exact log。
不要從目錄或 wildcard 猜測 log，也不要提交或取消其他 job。
```

取消採兩步確認。第一步只檢查：

```text
只使用 Slurm MCP 查詢 job <job-id> 的狀態與 job name，先回報結果，不要取消。
```

確認 job ID 後再下第二個明確指令：

```text
我確認要取消 job <job-id>。只呼叫 Slurm MCP cancel_job，完成後回報結果。
```

## 可用工具

| 工具 | 說明 | 例子 |
|---|---|---|
| `gpu_status` | 即時 GPU 使用率、VRAM、正在跑的 process | 「現在 GPU 狀況怎樣？」 |
| `cluster_info` | 各節點 online/offline 狀態、GPU 數量 | 「叢集有哪些節點？」 |
| `list_jobs` | 目前 queue 中的 pending/running jobs | 「現在有什麼 job 在跑？」 |
| `submit_job` | 提交 training job | 「用 ltx2 與 2 GPU 跑 train.py」 |
| `cancel_job` | 取消 job | 「取消 job 458」 |
| `get_logs` | 依 job ID 讀 exact output log | 「job 458 的 log 是什麼？」 |
| `job_history` | 最近的 submission history，包含 submission ID 與短版 source commit | 「最近有哪些 job？」 |
| `list_venvs` | NAS 上的 shared venv 清單 | 「有哪些 venv 可以用？」 |

## submit_job 參數

| 參數 | 必填 | 說明 |
|---|---|---|
| `command` | 是 | 例如 `python train.py --lr 1e-4` |
| `username` | 是 | 已由使用者/管理員確認的 audit identity |
| `venv` | 是 | Shared venv 名稱，例如 `ltx2`，或核准完整路徑 |
| `gpu` | 否 | GPU 數量，預設 1 |
| `job_name` | 否 | 顯示名稱；不作唯一識別 |
| `nodelist` | 否 | 核准時才指定 node |
| `repo_url` | 否 | Git repository URL |
| `branch` | 否 | Requested ref，預設 `main`；接受時固定 commit |
| `mem` | 否 | 例如 `32G` |

## 使用範例

```text
我的 username 是 alice，venv 是 ltx2。
請從 git@github.com:org/model.git 的 main branch，
用 2 張 GPU 與 32G memory 執行 python train.py --config configs/base.yaml，
job name 是 alice-baseline。
```

成功時 agent 回報 `submission_id`、`job_id` 與 `status`。後續用 `list_jobs`、`get_logs` 與 `job_history` 追蹤；不要從檔名猜測 log。

## 儲存位置

- Training data：`/storage/Internal_NAS/`
- Shared venv：`/storage/Internal_NAS/venvs/<name>/`
- Immutable run：`/storage/Internal_NAS/slurm-runs/<username>/<submission_id>/`
- Log：`/storage/Internal_NAS/logs/<username>/<submission_id>/`
- Recovery：`/storage/Internal_NAS/slurm-recovery/`

## 架構

```text
Engineer / AI client
  -> trusted private LAN
  -> mcp_server.py (192.168.51.48:8766)
    -> slurm_server.py Dashboard/API (192.168.51.48:8765)
    -> sbatch / squeue / scancel
    -> Slurm cluster
```

一般 AI client 只註冊 MCP URL，不把 raw API 設成 agent action。Dashboard/API 目前可由受信任 VPN 使用者直接存取；它沒有完整 SSO/RBAC 或 per-user Slurm ownership enforcement，不得公開到 Internet。

## 常見錯誤

- `username and venv are required`：補齊已確認值後重送。
- `incomplete success response`：視為失敗，不得假設 job 已建立；請 operator 檢查 adapter。
- `Source preparation failed`：檢查 repo URL、branch、Git 權限與 NAS 權限。
- `metadata_finalize_failed`：保留真實 job ID 並通知 operator 查 recovery record。
