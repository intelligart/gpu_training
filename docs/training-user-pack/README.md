# Training 使用者包：從手動 GPU training 遷移到 MCP／Slurm

適用對象：已經會 training，只要把既有 workflow 改由 Slurm 排程的人。
第一位 pilot 使用者：**hank**。文件交付日：2026-10-13；狀態更新：2026-10-21。

## 從這裡開始

只想先接上 client：看 [三分鐘只讀 quick start](../mcp-quickstart.md)。
查參數、回應與副作用：看 [MCP 工具參考](../mcp-tool-reference.md)。
已有連線、要搬自己的 training workflow，再依以下順序進行。

1. 閱讀 [連線設定](client-setup.md)，確認自己的 client 能看見 Slurm tools。
2. 將 [遷移資料卡](migration-card.md) 複製到自己的 private notes，填入原本 command 與 venv。
3. 貼上 [P0 只讀檢查](prompts.md#p0-只讀連線與環境查詢)，不提交 job。
4. 貼上 [P1 遷移審查](prompts.md#p1-將既有-command-轉成提交摘要)，先取得短跑 command 和待確認清單。
5. Operator 核對 worker 路徑、環境及實際 GPU occupancy，記錄節點範圍、影響與停止方式。
6. 確認短跑摘要後，才使用 P2 授權一次提交；再用 P3 追蹤。
7. 以 [試用驗收表](pilot-checklist.md) 保存實際結果，通過短跑才安排正式 training。

不需要安裝 Slurm/MCP server、不需要重新學模型，也不要求先跑另一套通用 demo。
第一次用自己的既有程式，縮小資料量／steps，驗證遷移即可。

## 原本做法 → 現在做法

| 原本 | MCP／Slurm |
|---|---|
| SSH 到一台主機執行 | AI 呼叫 `submit_job`，Slurm 排程 |
| 手動挑實體 GPU index | 指定 GPU 數量，尊重 Slurm 的 device visibility；不要覆蓋 `CUDA_VISIBLE_DEVICES` |
| Activate 個人環境 | 指定已確認、worker 可使用的 `venv`；不能假定個人 conda 環境可以搬移 |
| 使用未提交 working tree | 建議已推送的 Git commit；由 backend 固定 source commit |
| 本機 dataset/checkpoint 路徑 | 改為 Operator 核對的 NAS 版本路徑 |
| 共用 output/cache | 每個 job 使用獨立目錄，必要時在 command 內使用 `$SLURM_JOB_ID` |
| 看 terminal／猜 log 名稱 | `get_logs(job_id)` 讀 exact log |
| 手動 kill GPU process | 先核對自己的 job，再明確確認 `cancel_job` |

## 這包現在能測什麼？

這是搭配 **live 1.0.1** 的文件版遷移包；`get_onboarding_guide`、
`slurm://guides/onboarding`、`slurm_onboarding` 已部署，guide 內容版本為 `1.0.0`。
Job 535 的 11 pass / 2 fail 是歷史失敗；修正後 jobs 537、538 已通過包含
真實 SDK walkthrough 與乾淨 artifact/double-build 的測試，詳見
[implementation evidence](../onboarding-implementation-evidence.md)。獨立 reviewer 驗收仍待完成。

Hank 的 job **545** 已用固定 Git source 加 NAS YAML、直接呼叫官方 entrypoint，
完成 LTX-2.5 五步 LoRA training 並保存 checkpoint，沒有額外 NAS runner。
完整參數與證據見 [training 交接紀錄](../mcp-training-handoff-2026-10-20.md)。
這是短跑 pipeline 證據，不是模型品質保證；矩陣 demo、新帳號 onboarding、取消/resume
及正式長跑仍未因此完成。資料卡與驗收表保留為新一次實驗的空白範本，不自動填成 PASS。
歷史 command 的 output 已存在，不能直接重送；每次另備獨立 output 並取得新核准。

## 必須知道的 pilot 限制

- `username=hank` 為本次 audit label；所有 jobs 實際仍使用 shared `hank` 身份。不是 per-user authorization。
- 沒有 sandbox、強制 dataset/venv 唯讀或跨使用者權限隔離。Output/cache 分目錄是使用規範。
- Dataset/output 目前放在 `command`，不是新提交 schema 欄位。
- 沒有自動 worker preflight。路徑、CUDA、系統依賴、GPU 型號與實際 occupancy 必須核對。
- Slurm queue 空或 node IDLE 不等於實體 GPU 空閒；`gpu_status` 缺 device rows 時停止 GPU 提交並找 Operator。
- 目前沒有獨立 `job_status`；history／queue 消失不能證明 training 成功或 Slurm terminal state。
- Training、evaluation、模型執行及 Python scripts 經 Slurm MCP；MCP 失敗不得降級到本機、notebook 或 raw API。
- 不原地修改共享 venv，不碰其他人的 process，不把 credentials 或個人 private config 提交至 Git。
  團隊核准的內部 MCP 為 `http://192.168.51.48:8766/mcp`，僅限 VPN／內網；
  其他 private endpoints 未經核准不提交，未來公開文件另做去識別。

P0 telemetry 不完整時可記「client 連線通過、GPU readiness BLOCKED」。
使用資料卡內 Operator 聯絡管道交接；收到新的 occupancy 核對與核准後才進入 P2。
可重跑只讀 P0，但不要自動定時輪詢、重送 job 或自行認定等待一段時間後就能使用 GPU。

## Operator 私下交付項目

確認上述內部 MCP URL 的 VPN access、核准 venv、允許的節點範圍與 GPU/RAM 政策、
NAS dataset/output 路徑、程式 repository 存取與聯絡窗口。
Client credentials 只在自己的 secret/config store 輸入，不貼到聊天或共享驗收記錄。

更多細節：[MCP 使用說明](../../MCP_GUIDE.md)、[工程師指南](../user-guide.md)。