## Context

動機與六份文件範圍見 [proposal](proposal.md)。本設計用於釐清多份文件的職責、工具輸出與版本的權威來源，避免將改善說明擴大為新功能。

已觀察到：

- README 仍稱平台 1.0.0，包含 machine-local endpoint 與舊 artifact 名稱；MCP_GUIDE 已記錄 1.0.1 加 GPU hotfix，兩個入口不一致。
- `mcp_server.py` 提供九個 tools，以及同內容的 onboarding resource/prompt。多數工具回傳格式化文字；submit/cancel 回傳 JSON 序列化字串，不能描述為所有 tools 都有一致的 structured output。
- `submit_job` 的三個必填參數是 command、username、venv；dataset/output 仍在 command/config，不存在 dry-run、preflight 或獨立 job_status 入口。
- Server CLI 的 `--sse` 分支實際執行 Streamable HTTP，不能把旗標名稱當成 legacy SSE transport 的證據。使用者連遠端 endpoint，不需要在本機安裝另一個 Slurm server。
- Job 545 證明固定 Git source 加 NAS YAML 的五步 LTX-2.5 pipeline；既有 handoff 含歷史參數及已存在的 output，不能當成可直接重送的新手範例。
- 現有 staged onboarding／封裝共 14 個檔案。本 change 只新增未 stage 的 planning artifacts，實作時亦不得改動這些 staged blobs。
- Wave validator 另有無條件檢查 nested spec 的舊邏輯，與 OpenSpec 合法的 `skip_specs` 不相容；Owner 已核准將此相容修正納入。

## Goals / Non-Goals

**Goals:**

- 讀者由單一入口辨識用途、連線前置條件、第一個安全動作、工具契約及不能保證的事情。
- 同時服務一般使用者與 AI client，不讓使用者指南變成 Operator 安裝或維運手冊。
- Markdown 在 GitHub repository 可閱讀，並保持未來轉成文件網站的可攜性。

**Non-Goals:**

- 不建立網站、選擇前端框架或靜態網站生成器，不修改 Pages 設定、Actions、DNS 或 repository visibility。
- 不新增版本查詢、worker validation、dry-run、job 狀態持久化、tool annotations 或身份隔離。
- 不修改 runtime guide／Python docstrings，不為文件更新提升 guide 或 artifact 版本；文件版本日期不是新 release。

## Decisions

### 1. 採分層 Markdown，而非先搭網站

| 文件 | 職責 |
|---|---|
| `README.md` | 一句話用途、能力分類、quick start 入口、現況摘要、使用者／Operator 分流 |
| `docs/mcp-quickstart.md` | 可複製的 client 設定、只讀 setup prompt、預期發現項目與停止條件 |
| `docs/mcp-tool-reference.md` | 九個 tools 的完整輸入／預設值／輸出形式／副作用；resource/prompt 與錯誤語意 |
| `MCP_GUIDE.md` | 能力與版本對照、日常 MCP 流程、限制、troubleshooting；連到完整參考，不保留競爭的參數表 |
| `docs/user-guide.md` | 保留程式、dataset、venv、資源與 output 遷移細節，新增入口連結，避免大幅重寫 |
| `docs/training-user-pack/README.md` | 保留 hank pilot 與遷移範本，導向通用 quick start／參考，區分新實驗與歷史結果 |

參考 Flint 的「用途 → 快速開始 → 能力 → 設定 → 參考」資訊架構，不複製文案或承諾相同的互動 UI。
替代方案「只修改 README」無法容納完整工具契約；「立即做 Pages」會引入未核准的公開邊界與部署工具。

### 2. 第一個動作永遠只讀，提交另行確認

Quick start 的三分鐘是完成 client 連線及 discovery 的目標，不包含 VPN 開通、環境安裝或 training。
使用者向 Operator 取得核准 username/venv 與資源政策，確認 VPN／內網 access。
依 Owner 2026-10-22 修正，內部設定範例使用 `http://192.168.51.48:8766/mcp`；
8766 是 MCP，8765 是 API，不得互換。個人設定仍留本機，credentials／tokens 不提交。
範本先讀 `get_onboarding_guide`，再查 cluster、venvs、GPU；不提交、取消、安裝或執行 Python/model。
缺工具、連線失敗、telemetry 不完整或 occupancy 不明時停止並交接。

本機 stdio 只作「server 支援、Operator 使用」的區分，不鼓勵一般新使用者啟動本機替代 server。
VS Code HTTP 與 Claude Code bridge 設定沿用已存在的 client 契約；不承諾所有 clients 的能力相同。

### 3. 工具參考以 source 為準，回應範例不當作新實測

工具分類：

- 指南：get_onboarding_guide；另列 resource/prompt，同內容、零提交副作用。
- 查詢：cluster_info、gpu_status、list_venvs、list_jobs、job_history、get_logs。
- 變更：submit_job、cancel_job，明列資源／metadata／取消影響。

逐項記載參數 type、必填與預設值；submit 的九個參數對齊 source，不添加 dataset/output、
timeout 或 dry_run 欄位。`mem` 是 host RAM 而非 GPU VRAM；GPU 數量不自動啟動 DDP。
Username 是 audit label，queue username filter 不是權限檢查；history 的 status 不是保證已同步的 Slurm terminal state。

回應範例標為示意，區分工具回傳的文字／JSON 字串與 MCP transport envelope；不把回傳文字
`Error:` 誤認為一致的 MCP `isError` 行為。結構化成功回應中的 submitted 不等於 training 成功。
範例只使用 Owner 核准的內部 MCP endpoint，不含 credentials 或可直接重送的既有寫入目錄。

### 4. 版本與結果分開查證

版本表分列：

- 平台 artifact：目前記錄為 1.0.1，另有 MCP hotfix；原 tarball hash 不等於 hotfix 後完整安裝身份。
- Guide 內容：1.0.0，依 `onboarding.py`；本次不更新該模組。
- MCP protocol：連線協商版本；既有 smoke 使用 2025-06-18，不宣稱唯一或所有版本均相容。
- MCP SDK：service lock 的 2.2.0，是相依套件版本，不是平台版本。
- Source commit、installed files 與 running service 是不同證據；未實作 server version tool 不可偽造一個查詢入口。

錯誤說明分三類：可確定未提交的前置拒絕、已知存在 job 的 metadata failure、
timeout／不完整回應的結果不確定。後兩者先核對 ID/history/exact log，不能盲目 retry。
Job 545 只作可追溯的成功案例，連到既有 handoff；不複製其完整歷史寫入 command。

### 5. GitHub 顯示與 GitHub Pages 是兩件事

六份 Markdown 可在 repository 直接閱讀，並使用相對 links；本次不會產生獨立網站網址。
未來 project Pages 可提供文件網站，但公開說明網站不等於公開 Slurm API/MCP。
Private repo 不應被當作網站天然私有的保證；私有 Pages 的權限與方案須另查證。
公開發佈前另做允許文件清單與敏感資訊審查，不直接把含運維證據的整個 docs 目錄發佈。

## Risks / Trade-offs

- [首頁與工具參考再次漂移] → README 只保留摘要；參數表集中到工具參考，驗證 source signature 與文件工具集合。
- [靜態版本表被誤認為即時查詢] → 標明紀錄日期與各自來源；不把 SDK、協定或內容版本當平台 release。
- [文件範本觸發重複 job／覆寫輸出] → quick start 只讀；提交範例需新確認與獨立 output，timeout／缺 ID 不自動 retry。
- [公開文件洩漏內網或身份資訊] → 本 change 僅在內部文件使用核准的 MCP URL、
  不含 credentials、不開 Pages；未來公開發佈另做去識別並決定 audience、allowlist 與存取控制。
- [新增文件混入待確認 commit] → 保留 index patch SHA-256 與 14 檔案集合，實作及驗證後比對，再依 Owner 指示分組 stage，另確認 commit 訊息。

### Wave validator 相容性

移除重複且無條件的 nested-spec 檔案檢查，保留既有 `openspec validate --strict`
作為 delta／`skip_specs` 的權威判定，不自行用 grep 解析 YAML。一般缺 delta 的
change、非法 metadata 或宣告 skip 卻含 spec 的 change 仍由 CLI 拒絕；
CLI 不可用仍維持 fail closed。以隔離 fixture 驗證合法 skip 可通過、未宣告 skip
且缺 delta 仍失敗，不新增 dependency 或放寬其他 gates。

## Migration Plan

先檢查現有 staged patch 與六份文件的工作樹狀態，再依 tasks 更新 Markdown、驗證 links/anchors、
JSON 範例及工具／版本契約，另修正 validator 並驗證正反向 fixture，最後回報範圍與限制。不需要 package install、
Python/model 執行、新 Slurm job 或 service restart。
回復僅限本 change 的文件與 validator edits，保留使用者既有內容；不操作 live state 或重設 index。

Owner 的內部 endpoint 修正另外涵蓋 training pack 的 client setup 與 migration card；
與 README、MCP_GUIDE、quick start 同步端點及分享界線。這是文件修正，
不修改 server bind、runtime guide、權限或已保存的歷史驗證紀錄。
