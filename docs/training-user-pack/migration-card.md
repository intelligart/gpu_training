# hank 的第一個 training 遷移資料卡

這是**填寫範本，不是可直接執行的 job**。只預填已確認的 `username=hank`。
每一次新實驗的 training venv、模型、dataset、command 均須確認；不沿用之前平台測試的 service venv。
在 private notes 填寫，下列占位符未填完時不能提交。分享至 Git 的版本必須移除 secrets 和 private endpoints。
Hank 已完成的 LTX-2.5 job 545 另見 [training 交接紀錄](../mcp-training-handoff-2026-10-20.md)；
本範本不覆寫成歷史結果，也不授權重用該 job 的 output 或自動提交下一次。

## 1. 既有 workflow（你填）

| 項目 | 本次資料 |
|---|---|
| username | hank |
| 專案／實驗名稱 | `<project>/<experiment>` |
| 原本完整 training command | `<包含 launcher、config、dataset、output 參數；不含 credentials>` |
| 原本環境 | `<venv/conda 名稱、Python/CUDA 版本、dependency lock>` |
| 程式來源 | `<repo_url>` |
| 已推送完整 commit SHA | `<full-commit-sha>` |
| Dataset 版本路徑 | `<NAS-version-path 或明確不需要>` |
| Base／resume checkpoint | `<NAS-version-path 或明確不需要>` |
| 原本 output／cache | `<原路徑與程式是否支援設定>` |
| GPU／RAM 需求 | `<GPU count>/<RAM>`；RAM 不是 GPU VRAM |
| Launcher | `<單 GPU/DDP/其他>`；是否手動設 CUDA_VISIBLE_DEVICES |
| 特殊依賴 | `<CUDA extension/系統套件/下載/外部服務/none>` |

## 2. 短跑版本（AI 協助，Operator 核對）

| 項目 | 提交前確認 |
|---|---|
| 核准 training venv | `<venv-name-or-path>`；使用者明確確認 |
| 短跑 command | `<沿用原程式，少量 steps/資料；不可捏造不存在的 CLI flags>` |
| 上限／停止條件 | `<程式支援的 steps/epochs 上限、預期時間、逾時處理>` |
| job_name | hank-onboard-smoke |
| gpu | `<程式支援且核准的數量；先 1 GPU 或說明原因>` |
| mem | `<核准 RAM，例如 8G；只是格式示例不是配置結論>` |
| nodelist | 預設留空，只有核准特定節點時指定 |
| Output／checkpoint | `<每個 job 獨立的 NAS 目錄；可用 $SLURM_JOB_ID>` |
| Cache／tmp | `<程式支援且不覆寫共享輸入的路徑>` |
| 成功指標 | `<資料讀取、一次 forward/backward、finite loss/metric、checkpoint、必要品質門檻及對應證據>` |

GPU allocation 是 Slurm 管理；不在 command 覆蓋 `CUDA_VISIBLE_DEVICES` 或硬指定 host GPU index。
框架的 logical device 0 可能正是 allocation 內的第一張 GPU，不能只靠 `--device 0` 字樣判定違規；
需核對程式的 device 語意、launcher 及 visibility，不任意刪除參數。
DDP 要按 visible devices 配置 rank；`gpu=2` 不會自動啟用 DDP，也不代表 multi-node。
不要修改共享 dataset/checkpoint/venv；NAS output 分目錄不是 sandbox 保證。

## 3. Operator／Owner 提交核准（必填）

| 核對點 | 結果／證據 |
|---|---|
| Target node 或允許節點範圍 | `<核准範圍；空 nodelist 不表示所有節點都已驗證>` |
| Program/dataset/venv worker 可達性 | `<檢查時間、節點、結果；不是 MCP 自動 preflight>` |
| Scheduler allocation ＋實際 GPU occupancy | `<檢查時間與證據；缺 telemetry 就停止>` |
| 系統／CUDA 相容性與共享輸入風險 | `<結果、限制與接受風險的人>` |
| 預期影響 | `<GPU/RAM/CPU/時間/NAS 讀寫；是否有其他 workload>` |
| 驗證方式 | `<exact log、checkpoint、metric、Slurm status 來源>` |
| 停止／回復方式 | 僅確認後取消本 job；不 kill 其他 process、不修改 live service；保留 log，不自動刪結果 |
| 聯絡窗口／核准人 | `<Operator/Owner>` |
| BLOCKED 恢復方式 | `<實際聯絡管道、Operator 回覆核對證據；不自行猜等待時間或 GPU 空閒>` |
| 使用者明確確認 | `<確認時間與本次摘要；未確認不能提交>` |

## 4. 本次結果（執行後填）

- submission_id：`<returned-id>`
- job_id：`<returned-id>`
- source_commit：`<returned-full-sha；和卡片比較>`
- 初始 status：`<submitted 等；不等於 training 成功>`
- Exact log 證據：`<get_logs 回應；分享前遮掉敏感內容>`
- Slurm terminal state／來源：`<Operator 核對結果，無法確認則 unknown>`
- Output/checkpoint/metrics：`<實際位置及結果>`
- 短跑結果：`<PASS/FAIL/BLOCKED/UNKNOWN>`
- 正式 training 是否另行核准：`<未核准/已核准及範圍>`

此卡為使用者 test record，不取代平台 OpenSpec tasks，也不代表平台 onboarding 已由獨立 reviewer verified。

Venv 的「存在／可讀」不是「程式相容」。第一次短跑本來就是相容性驗證；
Operator 若需要額外 import/CUDA probe，應另外列明測試、資源與核准，同樣經 Slurm MCP，
不能叫 AI 在本機先跑 Python，或把未執行的檢查標成通過。