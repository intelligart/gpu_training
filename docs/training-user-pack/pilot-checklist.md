# hank pilot 試用驗收表

**這是下一次實驗待填的使用者驗收範本，不是歷史 job 的成績單。**
請複製至 private notes 保存結果，不把 secrets 或 machine-local config 提交到 repository。
以實際 log/IDs/Operator 證據判定，不只看 AI 說「完成」。
Hank 已完成的 LTX-2.5 job 545 見 [training 交接紀錄](../mcp-training-handoff-2026-10-20.md)；
新帳號尚未試用，以下未測欄位不由舊 job 自動填成通過。

## 測試順序

| ID | 動作 | 通過標準 | 初始狀態 |
|---|---|---|---|
| U0 | Client 設定＋P0 | guide 與 read-only tools 可用，沒有提交/取消 job；telemetry 缺失如實標註 | 未測 |
| U1 | 遷移卡＋P1 | hank/venv/ref/command/dataset/output 清楚；未填項會詢問，不自動執行 | 未測 |
| U2 | Operator 核對＋P2 | target/impact/validation/rollback 核准；只建立一個短跑 job，必要 IDs 完整 | 未測 |
| U3 | P3 追蹤 | exact log 對應本 job；短跑程式成功標準達成，Slurm terminal state 來源記錄 | 未測 |
| U4 | Output 檢查 | checkpoint/metrics 實際存在且合理、目錄獨立；無覆寫舊結果的跡象 | 未測 |
| U5 | P4 取消 | 先核對再確認，只操作自己的 active job；確認最終狀態而非只收到 accepted | 未測／可 N/A |
| U6 | P5 失敗回報 | 能整理 ID/log/環境/階段，不自動重送、不 local/raw fallback | 未測 |
| U7 | P6 resume | 若程式支援，另行核准 resume，從指定 checkpoint 繼續並寫到新 output | 未測／可 N/A |
| U8 | 正式 training 準備 | 固定版本、成功標準、停止方式與資源核准；只驗收 readiness，不自動送長 job | 未測 |

U6 可用對話情境 dry-run，不需要故意破壞資料、關 endpoint 或提交失敗 job。
U5/U7 不適用時記 N/A 和理由；不因此宣稱具備未實測的取消/resume 能力。
已部署的 resource/prompt 入口驗收屬於平台 onboarding，和此使用者 pilot 分開。

## 每個實際 job 保存的證據

- 測試日期／client／使用者：`<填寫>`
- 資料卡版本／核准 target/impact/validation/rollback：`<填寫>`
- submission_id／job_id／requested commit／resolved source_commit：`<填寫>`
- command／venv／gpu／mem：`<填寫；敏感資訊遮罩>`
- `get_logs(job_id)` 關鍵片段：`<填寫>`
- Queue/Slurm terminal state、exit status、時間與證據來源：`<填寫或 UNKNOWN>`
- Checkpoint、metrics、output/cache 路徑及驗證結果：`<填寫>`
- 異常與處理／是否重試：`<填寫；重試需新核准，確認非 duplicate>`
- 整體判定：`<PASS / FAIL / BLOCKED / UNKNOWN>`
- 使用者 hank 回饋／reviewer：`<填寫>`

目前 accounting disabled 的既有紀錄意味 `sacct` 可能不可用；Operator 應在 job 仍可查時保存
authoritative controller 狀態，之後查不到就標 UNKNOWN，不從 queue 消失推斷 exit code。
Log 證明程式結果與 Slurm terminal state 是不同證據，分欄記錄。

## 停止條件

- MCP 不可用、資料卡未填齊、Operator 未核准：不提交。
- GPU telemetry 缺失/手動 workloads 未釐清：不送 GPU job。
- ID 回應不完整或 submit timeout：先核對是否已建立 job，不直接 retry。
- Output 可能覆寫/shared venv 需要更新：停止，找 Operator；不自行改 ACL 或共享套件。
- 別人的 job/process、live service/config、NAS 資料刪除：不在使用者 onboarding 範圍。

## 使用者包可接受，不等於平台已驗收

你能獨立整理需求、核准一次短跑、讀 exact log、判讀結果、交付可追溯的實驗記錄，
即可完成基本遷移；取消/resume 另標能力是否實測。平台 tasks、onboarding 測試與獨立 reviewer
狀態仍以 [implementation evidence](../onboarding-implementation-evidence.md) 為準。