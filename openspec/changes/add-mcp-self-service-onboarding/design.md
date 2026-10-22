## Context

以下保留初始 planning 的決策背景，並非目前部署狀態。
截至 2026-10-21 的實作、測試與剩餘 review 見 [tasks](tasks.md) 及
[驗證證據](../../../docs/onboarding-implementation-evidence.md)；不變更本 design 的能力範圍。

Owner 最新決策：先記錄，第一版專注 onboarding，執行隔離之後再調整。本次是 planning only，不開始實作。現有 MCP 提供 instructions、submit_job 及 read-only tools，MCP_GUIDE.md 已有連線與對話範本，但 server 沒有 onboarding resource/prompt/tool；username 仍只是 audit label，實際執行帳號為 hank。

## Goals / Non-Goals

**Goals:**
- 使用者接上 MCP 後可取得首次使用指南，知道怎麼準備程式、dataset、venv、提交及追蹤。
- 對只支援 tools 的 clients 也可用，不強迫 users 先看 resources/prompts。
- 指南與範本不產生 job、不觸發取消，也不假裝驗證 worker 上的路徑或 GPU 相容性。

**Non-Goals:**
- 不改 submit_job schema、backend submission 或 output 路徑；dataset/output 暫時仍寫在 command 中。
- 不導入 Bubblewrap、強制唯讀、環境 builder、per-user identity 或自動安裝 client credentials。
- 不修改 live units、NAS permissions、Slurm config、不提交 canary。

## Decisions

### 1. 三種讀取方式共用內容

新增 get_onboarding_guide 只讀工具作通用入口；onboarding resource 與 prompt 為可選呈現方式，使用同一內容模組，避免三份規範漂移。Server instructions 指引首次使用先取 guide。替代方案「只給 Markdown URL」無法讓新接上的 LLM 自動發現；「只有 prompts」則會排除部分 clients。

Content 使用 zh-TW，包含 guide version、現有能力、限制、必要資料清單及範本。不在內容中內嵌個人 credentials 或 machine-local endpoint；client 連線使用 operator 提供的設定占位符。

### 2. 從 onboarding 到既有提交，不新增狀態服務

順序：取得 guide → 確認 username/venv → 透過 cluster_info/list_venvs 做只讀 discovery → 收集 repo/ref/command、dataset 路徑、GPU/memory 與 output 約定 → 顯示摘要並取得本次明確提交確認 → 呼叫現有 submit_job → 回報 submission_id/job_id/status/source_commit。

Dataset 若不需要須明確說明；未提供的資料不得猜。guide 描述這些為互動 checklist，不誤稱現有 backend 有 dataset 必填欄位、worker preflight 或不可繞過的 approval gate。確認流程是 client guidance，不是新 authorization。

guide 提供 logs/history/queue 與兩步取消範本；history 或 queue 不足以判定 terminal state 時告知限制，不偽造 job_status 能力。gpu_status 目前有 nested-payload 已知問題，結果缺失或 device 有手動 workload 時交由 Operator 判斷。

### 3. 延後項目與採用方向

- 下一階段：結構化 program/dataset/environment 欄位、worker preflight、submission 專屬 output/cache/tmp。
- 已選擇的 sandbox 方向：優先評估 Bubblewrap，將 code/dataset/checkpoint/venv 唯讀掛載，只開放本次 job 的 writable paths；驗證 worker namespaces、GPU/CUDA/venv、signals/cancellation 與多人共讀。不支援時 fail closed，不默默無保護執行。
- 此方向不代表已安裝或已通過所有 workers；不以本 change 的完成宣稱強制保護。共用 hank 與 host 外部 processes 的風險仍存在。
- 未來 sandbox 的 network/process/credential 邊界和 legacy compatibility 須由另一個 change 定義；per-user identity 已另存 plan-multi-user-job-identity，不在本版擴張。

## Risks / Trade-offs

- [LLM 沒有自動讀 guide] → instructions/tool 描述入口加文件備援；client walkthrough 驗收，不承諾提示詞有 kernel enforcement。
- [資料與範本漂移] → 同一內容來源和一致性 tests；runtime cluster 資訊使用查詢工具，不寫死 GPU 型號數量。
- [users 誤認唯讀保護已完成] → 每種呈現明列 shared-hank、未 sandbox、output 隔離仍為使用規範。
- [onboarding 觸發提交] → guide tool/resource/prompt 只回傳內容；mock tests 確認不呼叫 submission/cancel/backend。

## Migration Plan

本次僅保存 artifacts，tasks 全部未開始。未來 Owner review 後 apply；新增 MCP 能力為 additive，既有 submit_job contract 和 historical metadata 不變。新增內容模組須納入 versioned artifact，部署前驗證完整封裝；live 切換另列 controller node、短暫 MCP 中斷、health/protocol checks、previous release rollback，不重啟 Slurm。正式 training canary 另行核准並只經 MCP。
