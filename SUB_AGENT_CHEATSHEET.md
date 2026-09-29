# GPU Platform Contributor Cheatsheet

## 開工順序

1. 讀 `.claude/CLAUDE.md`。
2. 讀 OpenSpec apply instructions 列出的全部 context files。
3. 確認 GitHub issue assignee、target repo、branch 與 file lane。
4. 在每個受影響 repo 執行 `git status --short`，不得覆蓋既有工作。
5. 寫下最便宜、可推翻目前假設的 focused validation，再開始修改。

## 預設 File Lanes

| Lane | 可修改 | 不可自行擴張 |
|---|---|---|
| Wave control plane | `.claude/**`, `.github/**`, `openspec/**`, `scripts/**`, trackers | Training/API implementation |
| MCP submission | `mcp_server.py`, integration docs 與指定 tests | Live service、Slurm source |
| Concurrent submissions | `slurm_server.py`, storage/source adapters 與指定 tests | Wave workflow、live database |
| Deployment | `deploy/**`, preflight、runbook | Live `/etc`, service restart, firewall |
| Component source | Task 指定的 Slurm/LTX-2/DCGM paths | 其他 repo 或未指派共享檔案 |

共享 API contract、database schema、deployment config 與 top-level dependency files 是高
碰撞面；跨 lane 修改前由 coordinator 重切 tasks 或指定單一整合者。

## GitHub 認領

- 本地 issue ID、OpenSpec task ID 與 GitHub issue number 是不同命名空間。
- 所有 `gh` 操作要求明確的 `WAVE_GH_REPO` 並帶 `--repo`。
- 完整標題已存在時重用；已有其他 assignee 時停止並回報 coordinator。
- 一個主要 lane 一張 issue，不為每個 checkbox 重複開 issue。

## 完成標準

- `open` → `in-progress`：Contributor 成功認領後。
- `in-progress` → `fixed`：實作完成且 focused validation 通過。
- `fixed` → `verified`：由 reporter/reviewer 重跑 acceptance 後。
- 回報需包含 change/task、target repo、主要檔案、實際命令、關鍵結果與剩餘風險。

## 紅線

- 不執行未核准的 job submission、service restart、live config、firewall 或資料刪除。
- 不提供 agent 通用 SSH、`systemctl` 或 shell 管理工具。
- 不使用 `git reset --hard`、destructive checkout 或 force push。
- 不把 secret、private endpoint、runtime database 或短期狀態提交到 repo。