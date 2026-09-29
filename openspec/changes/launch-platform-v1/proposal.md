## Why

目前 GPU training 已有可操作 Slurm 的 MCP、HTTP API 與 Dashboard，但跨 repo 的 Wave/OpenSpec 控制面仍留在 Slurm checkout，AI training 提交只靠提示詞約束，同一使用者的併發 job 也會共用生成 script 與 mutable repo 工作樹。第一版上線前需要建立單一私有規劃中心，並消除會造成錯誤程式碼或錯誤參數被執行的併發風險。

## What Changes

- 將 `gpu_training` 設為新的內部 Wave/OpenSpec 權威位置，供 Slurm、LTX-2、DCGM 與 training 的後續跨 repo 開發使用。
- 保留 Slurm repo 目前的 active changes 至完成與 archive，不在進行中搬移，也不再於該 repo 建立新的內部跨 repo change。
- 規定 Claude、ChatGPT 及其他 AI agent 的 training 請求 MUST 經由 Slurm MCP 的 training tools 提交，不得由 agent 在本機直接執行 Python 或繞過 MCP 呼叫 submission API。
- 將每次 job submission 建立為不可互相覆寫的獨立執行單位；同一使用者同時提交多個 job 時，生成 script、source snapshot、log 與 metadata MUST 可獨立識別。
- 建立可重跑的 v1 離線測試、部署前檢查、內網 rollout 與 rollback 程序；未通過 gate 時不得重啟或切換 live service。
- v1 不新增任意 Slurm 管理 shell、daemon restart 或公開網際網路入口；完整 SSO/RBAC 與 Admin MCP 留給後續 change。

## Capabilities

### New Capabilities

- `wave-control-plane`: 定義 `gpu_training` 如何集中管理跨 repo OpenSpec changes、task lanes、GitHub issues 與驗證證據。
- `agent-training-submission`: 定義 AI agent 只能透過 Slurm MCP 提交 training，以及提交所需參數與禁止的旁路行為。
- `concurrent-job-isolation`: 定義同一使用者或同名 job 的併發提交如何隔離 script、source、log 與實驗 metadata。
- `platform-v1-rollout`: 定義第一版內網部署的 preflight、健康檢查、驗收與 rollback gate。

### Modified Capabilities

無；`gpu_training` 尚未有已生效的 OpenSpec capability。

## Impact

- 主要 repo：`gpu_training`；新增 Wave/OpenSpec 工作流、測試與部署文件，並修改 MCP/API submission 路徑。
- 整合 repo：Slurm、LTX-2、DCGM 保持獨立 checkout；未來 lane 以明確 target repo、branch、file scope 與 component commit 連結。
- 執行環境：Slurm controller 上的 MCP/API services、`/storage/SSD2/slurmjob/<username>/` 工作目錄與 `/storage/Internal_NAS/logs/`。
- 相容性：保留現有 MCP tool 的主要使用流程；可能收緊不安全的 legacy submission 欄位與 agent 直連 API 行為。
- 營運：本 change 只規劃 deployment gate；任何 service restart、live config 或 firewall 變更都需另行列出節點、影響與 rollback 並取得明確核准。