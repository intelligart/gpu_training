# Slurm GPU Cluster MCP Server — 使用說明

## 什麼是 MCP Server？

MCP (Model Context Protocol) Server 讓 Claude Code 能直接操作 Slurm 叢集。
連上後，你只需要用中文跟 Claude 說你想做什麼，Claude 會自動呼叫對應的工具。

---

## 連線設定

在你的 Claude Code 專案目錄底下建立 `.claude/.mcp.json`：

```json
{
  "mcpServers": {
    "slurm-gpu-cluster": {
      "command": "npx",
      "args": ["mcp-remote", "http://ia-ai-server-5:8766/mcp", "--allow-http"]
    }
  }
}
```

> 需要先安裝 Node.js。`npx` 會自動下載 `mcp-remote`。

---

## 可用工具

| 工具 | 說明 | 例子 |
|------|------|------|
| `gpu_status` | 即時 GPU 使用率、VRAM、正在跑的 process | 「現在 GPU 狀況怎樣？」 |
| `cluster_info` | 各節點 online/offline 狀態、GPU 數量 | 「叢集有哪些節點？」 |
| `list_jobs` | 目前 queue 中的 job（running / pending） | 「現在有什麼 job 在跑？」 |
| `submit_job` | 提交訓練 job | 「幫我提交一個 job 跑 train.py」 |
| `cancel_job` | 取消某個 job | 「取消 job 458」 |
| `get_logs` | 讀取 job 的 output log | 「job 458 的 log 是什麼？」 |
| `job_history` | 最近的歷史 job 記錄 | 「最近有哪些 job？」 |
| `list_venvs` | 列出 NAS 上的共享 venv | 「有哪些 venv 可以用？」 |
| `create_venv` | 在 NAS 建立新的共享 venv | 「幫我建一個叫 myenv 的 venv」 |

---

## submit_job 參數說明

| 參數 | 必填 | 說明 |
|------|------|------|
| `command` | 是 | 要執行的指令，例如 `python train.py --lr 1e-4` |
| `username` | 是 | 你的名字，job 工作目錄在 `/storage/SSD2/slurmjob/<username>/` |
| `gpu` | 否 | 需要幾張 GPU（預設 1） |
| `job_name` | 否 | job 名稱（預設 "job"） |
| `nodelist` | 否 | 指定節點，例如 `AI-Server-6`（不填自動分派） |
| `venv` | 否 | venv 名稱，例如 `ltx2`（或完整路徑） |
| `repo_url` | 否 | GitHub repo URL，如果工作目錄不存在會自動 clone |
| `branch` | 否 | git branch（預設 main） |
| `mem` | 否 | 記憶體上限，例如 `32G` |

---

## 資料存放規則

- **訓練資料**：必須放在 `/storage/Internal_NAS/`
- **Job 工作目錄**：`/storage/SSD2/slurmjob/<username>/`
- **共享 venv**：`/storage/Internal_NAS/venvs/<name>/`

---

## 使用範例

跟 Claude 說：

```
幫我提交一個 job，用 ltx2 venv 跑 python train.py，需要 2 張 GPU，我的名字是 alice
```

Claude 會自動呼叫 `submit_job` 並回報 Job ID。

---

## 架構

```
Claude Code (IDE)
    ↓ MCP protocol (Streamable HTTP)
mcp-remote (npx)
    ↓ HTTP
ia-ai-server-5:8766  ← mcp_server.py  (systemd: slurm-mcp.service)
    ↓ REST API
ia-ai-server-5:8765  ← slurm_server.py (systemd: slurm-api.service)
    ↓ sbatch / squeue / scancel
Slurm Controller
```
