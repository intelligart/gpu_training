# 可複製的試用 prompts

按順序使用；保留上一步摘要再進入下一步。任何 `<...>` 未填妥不得提交。
這些 prompts 是操作指引，不是 backend enforced authorization。不能用它們證明 sandbox 或安全隔離。

## P0 只讀連線與環境查詢

```text
我是 <username>，這是本次把既有 training 遷移到 MCP／Slurm 的只讀檢查。
這次只做 read-only discovery，不提交、取消、安裝套件或執行任何 Python/model。
只使用核准的 Slurm MCP，先呼叫 get_onboarding_guide，再查 cluster_info、list_venvs、gpu_status、list_jobs。
回報工具是否可用、venv 清單及 GPU telemetry 是否完整。
列出的 venv 只是候選，不代表我已選定或它已相容我的程式。
不要由 queue 空或 Slurm IDLE 推斷 GPU 空閒；device rows 缺失就標 BLOCKED，交 Operator 核對。
1.0.1 已部署 get_onboarding_guide；若找不到，回報 Operator 核對 endpoint/版本/client 設定。
可先閱讀文件版使用者包，但工具發現不完整時不要提交，也不要自行重啟 server。
MCP 不可用就停止，不使用本機或 raw API fallback。
```

## P1 將既有 command 轉成提交摘要

填寫 [遷移資料卡](migration-card.md) 後，把卡片連同此段貼給 AI。

```text
請檢查我提供的 training 遷移資料卡，只做準備，不提交、不執行程式。
保留原本模型程式；提出使用同一 entrypoint 的最小短跑 command。
不要猜 venv/dataset/ref，不要新增未確認存在的 command flags。
區分 framework logical device index 和 host 實體 index，核對 launcher/device visibility 語意，
不要看到 --device 0 就自行刪除；用變更前後摘要讓我確認必要調整。
找出硬指定 host GPU index、CUDA_VISIBLE_DEVICES、相對路徑、共享 output/cache、
個人 conda 環境與無限 training 的遷移風險，不直接替我修改共享環境。
呈現已確認的 username、repo_url、完整 commit、command、dataset/checkpoint、venv、
gpu、mem、job_name、nodelist、output/cache、停止條件與成功標準。
Dataset/output 留在 command，別捏造 submit_job 新欄位。
區分已確認、假設、待我填寫、待 Operator worker/occupancy 核對的項目。
附 target node/允許範圍、impact、validation、rollback 摘要；取得核准前不能提交。
```

## P2 確認後只提交一次

只能在資料卡完整、Operator 核對完成、你真的接受影響後使用。此頁占位符不是授權。

```text
我確認上一份提交摘要 <摘要版本或日期> 的 command、venv、資源及 NAS 路徑。
Target node/允許範圍=<核准範圍>；impact=<GPU/RAM/時間/NAS影響>。
Validation=<短跑成功標準>；rollback=只停止本 job，保留 log/output，不改 live services。
核准人=<Owner/Operator>，實際 GPU occupancy 核對時間=<時間>。
Output/checkpoint/cache=<核准的獨立路徑或 job-id 路徑規則>，不得重用舊 job 的寫入目錄。
如果無法確認路徑獨立，先停止，不假裝 backend 會強制隔離。
現在只透過 Slurm MCP submit_job 提交這一次短跑；未完成欄位就停止問我。
不自動送正式 training，不自動重試，不在本機/notebook 執行，也不使用 raw API。
回報 submission_id、job_id、初始 status、source_commit，核對與指定 commit 一致。
若 timeout 或 ID 回應不完整，先視為結果不確定，查 history/交 Operator 確認是否已建立 job，
不要重送造成 duplicate jobs。未得到明確結果就停止。
```

## P3 查 queue／history／exact log

```text
只用 Slurm MCP 查我的 job <job-id>：list_jobs、job_history、get_logs。
確認是我的本次 submission，不用 wildcard 猜檔名、不提交或取消工作。
將結果分成提交狀態、queue 狀態、程式 log、checkpoint/metrics 證據。
逐項比較資料卡的成功指標和實際證據；loss/metric 是否 finite、checkpoint 是否符合預期。
沒有讀到實際產物就標待核對，不把 Training started 或 exit 0 當成模型品質驗證。
Queue 消失或 history 顯示 submitted 都不能當成成功。
若 terminal state 或 output 證據不足，標 UNKNOWN，請 Operator 核對 Slurm 與 NAS 結果。
不要為了檢查而執行本機 Python/model，不把過往 job 的成功當成本次證據。
```

## P4 兩步取消

先貼第一段：

```text
請只查 job <job-id> 的 submission_id、job_name、username 與可取得的 queue/status。
我要核對的是實驗=<experiment>、提交日期=<date>、原 submission_id=<id>。
核對是不是我這次的 job，先回報，不取消。身份或狀態不明時請 Operator 確認。
```

看過結果，確認 job 正確後才貼第二段：

```text
我確認取消上一步核對的 job <job-id>，只呼叫 Slurm MCP cancel_job。
回報 cancellation request 結果，再查 queue/log；不要把 request accepted 當成已 terminal。
不要刪 checkpoint/log，不 kill host process，不取消其他 job。
```

只對你自己仍 active、已核准的 job 操作。不為完成 checklist 額外送空耗 GPU 的 job；
若短跑已結束，取消測試記 N/A 或留待下一次核准的 active job。

## P5 失敗交接

```text
這次 training 出現問題，請停止自動提交／重試。
整理 submission_id、job_id、source_commit、venv、command、資源、錯誤發生階段、
exact log 關鍵片段、已知與未知事項，以及下一個最小檢查建議。
分辨 client/MCP、submission、pending allocation、環境/路徑、模型程式或結果品質問題。
不要修改共享 venv/dataset，不換 endpoint，不重啟服務，不做 local/raw fallback。
分享前移除 credentials 和敏感資料；交我／Operator 決定下一步。
```

## P6 Resume／正式 training（另外確認）

```text
先不要提交。請用已驗證的短跑資料卡提出 <resume/正式 training> 摘要。
確認 checkpoint 與原程式的 resume flags 相容，固定 code/dataset/venv，
列出來源 checkpoint=<舊 job 的完整 checkpoint 路徑>、來源 job_id=<id>，
以及新 output=<新的 job-id 路徑或獨立目錄>，確認不是舊 job 寫入目錄。
用新的 output 目錄避免覆寫舊結果，說明新增資源／時間／NAS 影響。
不要捏造 resume flags；原程式不支援就停止說明。
取得新一次 Operator/Owner 資源核准及我的提交確認後，才進入 P2。
Evaluation、模型執行或 Python script 一樣只經 Slurm MCP。
2 GPU/DDP 只有程式支援且另行核准時才測，不是完成單 GPU onboarding 的必要條件。
```