# Slurm MCP：版本與操作指南

透過核准的 remote MCP，查詢 GPU/環境、提交自己的 training 並讀取 exact log。
本文件描述目前能力與限制，不保證當下節點或 GPU 可用。

**[第一次使用](docs/mcp-quickstart.md)** · **[完整工具參考](docs/mcp-tool-reference.md)** ·
**[Training 遷移包](docs/training-user-pack/README.md)** · **[回首頁](README.md)**

## 版本與相容性

文件更新：2026-10-22。下面各版本有不同意義，不要互相比較或當成即時版本查詢：

| 項目 | 已記錄版本／行為 | 權威來源與限制 |
|---|---|---|
| 平台 artifact | `1.0.1`，後續有 MCP GPU hotfix | [manifest](deploy/platform-v1/artifact.json) 與 [部署紀錄](docs/release-1.0.1-test-deployment.md)；原 tarball hash 不等於 hotfix 後完整 installed 身份 |
| Guide 內容 | `1.0.0` | [onboarding.py](onboarding.py)；不是平台版本 |
| MCP SDK | `2.2.0` | [service dependency lock](deploy/platform-v1/requirements-service.lock)；不是平台或協定版本 |
| MCP protocol | Initialize 時協商；現有 smoke 請求 `2025-06-18` | [smoke](deploy/platform-v1/smoke-mcp.sh)；不宣稱只支援或已測遍其他版本 |
| Remote transport | Streamable HTTP | [server source](mcp_server.py)；CLI 保留的 `--sse` 名稱不代表 legacy SSE transport |

Source checkout、Git HEAD、build artifact、installed 檔案與 running service 是不同事實。
目前沒有 `server_info`／版本查詢 tool；需要 runtime 版本或 checksum 時交由 Operator 核對，
不要把 MCP SDK 的初始化資訊當成平台 release 證明。本次文件更新不提升 runtime guide 或 artifact 版本。

### Client 能力

| Client | 連線方式 | 注意事項 |
|---|---|---|
| VS Code／GitHub Copilot | Operator 提供的 `<MCP_ENDPOINT>`，HTTP MCP 設定 | 詳見 [quick start](docs/mcp-quickstart.md)，設定只保留 machine-local |
| Claude Code | 核准的 remote bridge profile | Private HTTP profile 的 `--allow-http` 不套用至公開網路 |
| 其他 client | 須支援 remote MCP 並經 Operator 核准 | 不支援就停止，不提供 raw API fallback |
| 只支援 tools | 呼叫 `get_onboarding_guide` | 不依賴可選 resource/prompt |
| 支援 resources/prompts | 可讀 guide URI 或取得 prompt | 與 tool 同內容，不新增權限 |

Server source 亦有 stdio 模式，但一般使用者不需要另啟本機 server；
那不是 remote MCP 故障時的替代執行路徑。

## 能力一覽

| 類型 | 現有入口 | 能做什麼 |
|---|---|---|
| 首次使用 | `get_onboarding_guide` | 只讀 checklist、確認與追蹤範本 |
| 叢集／環境 | `cluster_info`、`gpu_status`、`list_venvs` | 查詢狀態，不預約 GPU、不自動驗證 worker |
| 提交 | `submit_job` | 依確認的 Git source、command、venv 與資源送 Slurm job |
| 追蹤 | `list_jobs`、`job_history`、`get_logs` | 查 queue／metadata／exact log |
| 取消 | `cancel_job` | 對指定 job 請求取消，須先核對並確認 |

完整參數、預設值、回傳形式及副作用以 [工具參考](docs/mcp-tool-reference.md) 為單一文件入口。
目前大多回傳文字；submit/cancel 的 JSON 是工具字串內的內容，不是所有 tools 共用的 structured schema。

### 同內容的三種指南入口

| MCP 能力 | 識別名稱 |
|---|---|
| Tool | `get_onboarding_guide` |
| Resource | `slurm://guides/onboarding` |
| Prompt | `slurm_onboarding`，無 arguments |

取得指南不連 backend、不寫 metadata、不提交或取消 job。
缺 guide 工具時核對 endpoint／版本與 client 設定，停止提交並找 Operator，
不自行重啟 server；文件不是連線失敗時的 training fallback。

## 從連線到一次 training

1. 依 [quick start](docs/mcp-quickstart.md) 完成只讀 discovery。
2. 使用者提供已確認的 `username`、`venv`、repo/ref/command、dataset/config、
   GPU/host RAM、獨立 output/checkpoint/cache 與成功／停止條件。
3. Operator 核對 worker 路徑、環境、GPU occupancy 與資源政策。
4. AI 顯示摘要，取得本次明確確認，再呼叫 `submit_job` 一次。
5. 保存 submission/job ID、初始 status 與完整 source commit，追蹤 exact log 和產物。

Dataset/output 仍在 command/config，不是獨立 tool 欄位。
建議固定已 push 的完整 Git commit；NAS YAML 也可用，但須另記其版本／內容與新 output，
不假裝 YAML 已包含在 Git source。平台會產生 Slurm batch script，不要求使用者另外複製 runner。
`gpu=2` 不會自動變成 DDP；`mem` 是 host RAM，不是 GPU VRAM。

先準備、尚不提交的對話範本：

```text
只使用 Operator 核准的 Slurm MCP。
username=<已確認值>，venv=<核准環境>，repo_url=<repo>，branch=<已 push 的完整 commit>。
command=<已確認 entrypoint 與 config>，dataset=<版本路徑或不需要>。
gpu=<核准數量>，mem=<host RAM>，output=<新的獨立路徑>。
先整理工作摘要、待核對項目、影響與成功／停止條件；現在不要提交。
等我明確確認且 Operator 完成 worker/occupancy 核對後，才提交一次。
```

這是 client guidance，不是 backend approval/authorization gate。
實際操作 prompt、兩步取消與 resume 模板見 [training prompts](docs/training-user-pack/prompts.md)。

## 如何判斷結果？

- `submitted` 表示提交回應，不代表程式啟動、training 完成或模型品質合格。
- `list_jobs` 查 queue；`job_history` 是 submission metadata，不保證已同步 terminal state。
- `get_logs` 讀 exact log，不從 wildcard 猜檔名；training log、checkpoint/metric 與
  Slurm terminal state 分別保存。
- 目前沒有獨立 `job_status` tool。資訊不足交由 Operator 向 Slurm 核對；
  accounting 關閉或歷史已清除時如實標 unknown，不從 queue 消失推斷成功。
- 取消先核對自己的 job ID/name/submission，再明確確認 `cancel_job`；
  request accepted 不等於已確認取消完成。

## 常見問題與停止條件

| 情況 | 處理 |
|---|---|
| MCP 無法連線／工具缺失 | 核對 VPN、Operator endpoint 與 client 設定，停止並回報；不改 server/firewall |
| `username and venv are required` | 補齊使用者已確認值；不要從路徑或登入名稱猜測 |
| Venv 有列出但 job 啟動失敗 | Listing 不驗證 worker interpreter/CUDA；保存 exact log，交 Operator |
| GPU 沒 device rows／有其他 processes | 不猜可用容量；Slurm IDLE 不代表無手動 workload |
| Source preparation failed | 核對 repo/ref、Git access、NAS 路徑與 source commit；修正後另確認 |
| Submit timeout／服務錯誤／incomplete success response | **結果可能不確定**，先查 history／已知 ID／exact log，找 Operator，不盲目重送 |
| metadata_finalize_failed 且帶 job ID | Job 已建立；保存真實 ID/recovery path，交 Operator，不再送一個 |
| Output 已存在／需改共享 venv | 停止並確認新 output／核准環境，不覆寫或自行 pip install |

錯誤可能在工具文字而非一致的 MCP `isError` 欄位，必須閱讀回應。
人類手動 curl 的 [HTTP 相容入口](docs/manual-http-submission.md) 不是 AI fallback；
AI training/model/Python training script 仍只經 MCP。

## 已證明與尚未保證的事

已保存的 job **545** 用固定 Git source 加 NAS YAML，直接執行官方 LTX-2.5 entrypoint，
完成五步 LoRA training 並保存 finite checkpoint，沒有外部 NAS runner。
詳見 [成功案例／交接紀錄](docs/mcp-training-handoff-2026-10-20.md)；
歷史 output 已存在，不可直接重送其中的 command。

這不驗證模型品質、所有 worker/default venv、real curl submission、新帳號 onboarding、
取消/resume 或 per-user execution。Onboarding 的獨立 reviewer acceptance 仍待完成，
見 [驗證證據](docs/onboarding-implementation-evidence.md)。

目前限受信任 VPN/private network；username 僅為 audit label，shared service identity
不等於跨節點 UID/GID 已一致。沒有 sandbox、強制 dataset/venv 唯讀、worker preflight、
SSO/RBAC 或跨使用者 ownership enforcement。獨立 output/cache 是使用規範，不是安全隔離。
Endpoint／tokens 只放本機設定；公開說明網站不代表可以公開 MCP/API。
