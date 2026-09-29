# Slurm GPU Cluster MCP 使用說明

MCP Server 讓 Claude、GitHub Copilot、ChatGPT 與後續 AI client 透過同一條受控路徑使用 Slurm：

```text
AI client -> trusted private-LAN MCP endpoint -> internal adapter -> Slurm
```

## 上線狀態

`ia-ai-server-5` 已有 legacy MCP/API endpoint 正在服務。v1 release candidate 已通過離線 preflight，但尚未切換 live services，也尚未執行 v1 canary；既有 endpoint 在 rollout 前只能視為 legacy service，不能宣稱已具備本文件列出的 v1 isolation 與 release guarantees。

## 使用政策

- Training、模型執行與 Python training script 一律呼叫 MCP `submit_job`。
- MCP 無法連線或 submission 失敗時必須停止，不得在 client 主機本機執行或改呼叫 raw backend。
- `username`、`venv`、`command` 在 MCP tool schema 中都是必填；agent 不得猜測。
- 成功回應必須包含 `submission_id`、Slurm `job_id` 與初始 `status`。
- Endpoint、token 與憑證只放 machine-local secret/config，不提交到 repository。
- v1 只允許 trusted internal network/VPN/gateway，不得公開到 Internet。

完整工程師交付流程見 [工程師交付與部署指南](docs/platform-v1-engineer-handoff.md)。Claude、Copilot 與 ChatGPT 的共同設定契約見 [AI training integration contract](docs/agent-training-integration.md)。

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

需要 Node.js 與 `npx`。此明文 HTTP profile 只核准用於受信任的 `192.168.51.0/24` 私有網路；不得從 Internet 暴露。未來啟用 HTTPS gateway 後移除 `--allow-http`。

VS Code Copilot 與 ChatGPT 也只註冊管理員提供的 MCP endpoint。Client 不支援 remote MCP 時，該 client 暫不支援 training，不建立 raw API fallback。

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
    -> slurm_server.py internal adapter (loopback 127.0.0.1:8765)
    -> sbatch / squeue / scancel
    -> Slurm cluster
```

一般工程師只取得 MCP URL。Loopback adapter 與 Dashboard 是 implementation boundary，不是 agent action。

## 常見錯誤

- `username and venv are required`：補齊已確認值後重送。
- `incomplete success response`：視為失敗，不得假設 job 已建立；請 operator 檢查 adapter。
- `Source preparation failed`：檢查 repo URL、branch、Git 權限與 NAS 權限。
- `metadata_finalize_failed`：保留真實 job ID 並通知 operator 查 recovery record。
