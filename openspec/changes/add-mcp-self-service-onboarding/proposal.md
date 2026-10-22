## Why

本 proposal 保留初始決策背景；截至 2026-10-21 已實作並部署 1.0.1。
目前進度與限制以 [tasks](tasks.md) 及
[驗證證據](../../../docs/onboarding-implementation-evidence.md) 為準，不代表獨立 reviewer 已驗收。

新使用者連上 MCP 後仍須從外部文件猜測需要提供的程式、dataset、環境與提交步驟。Owner 決定先做 onboarding 第一版，維持目前 shared-hank pilot，將 sandbox 與強制寫入隔離延後。

## What Changes

- 提供不會提交 job 的 onboarding 指南工具，並以 MCP resource/prompt 提供同一份內容；不依賴 client 一定支援 resources/prompts。
- 引導使用者確認 username、程式來源/ref/command、dataset 路徑、venv、GPU/memory 及 output 約定，先做 read-only discovery 再確認提交。
- 保留現有 submit_job schema；dataset/output 目前仍由 command 指定，不宣稱已新增結構化欄位或執行時保護。
- 提供連線、提交、logs、取消與常見失敗的範本；只走 MCP，不提供 raw/local fallback。
- 記錄後續階段：結構化提交、submission 專屬 output/cache/tmp、Bubblewrap 強制輸入唯讀及相容性驗證。這些不在本版實作。

## Capabilities

### New Capabilities

- `mcp-self-service-onboarding`: 可發現、只讀的首次使用指南與提交/追蹤範本。

### Modified Capabilities

無；不修改現有 submission、identity 或 sandbox 契約。

## Impact

Target repo 為 gpu_training；未來涉及 mcp_server.py、新的共用 onboarding 內容模組、tests、MCP_GUIDE.md/docs/user-guide.md，以及部署 artifact 的封裝與驗證。slurm_server.py、Slurm source、live services、帳號與 NAS ACL 不在本版實作範圍。部署與 canary 另需 Owner 核准；本次僅保存設計，保留既有未提交工作。
