本 change 實作六份 Markdown 文件與已另獲核准的 Wave validator 相容修正，
不修改 server、runtime guide、tests、dependencies、部署或網站設定。
Specs 已依文件／tooling 範圍明確跳過。Target repo：`gpu_training`；apply 進行中。

## 1. 建立新使用者入口與工具參考

File lane：新增 `docs/mcp-tool-reference.md`、`docs/mcp-quickstart.md`。
先完成工具契約，再由 quick start 與後續摘要文件引用；單一主要寫入者。

- [x] 1.1 新增九個既有 tools 及 onboarding resource/prompt 的參考，逐一列出參數型別、必填／預設、文字或 JSON 字串回傳、副作用與限制；驗證：用 Node／source inspection 對照 `mcp_server.py` 的 decorated tools、signature 與回傳分支，確認九個工具集合一致，submit 仍只有既有九個參數，沒有虛構 version/preflight/job_status/dry_run 能力。
- [x] 1.2 新增三分鐘只讀 quick start，包含 Operator 前置交付、VS Code HTTP／Claude Code bridge JSON、copyable setup prompt、預期發現項目與停止條件；驗證：JSON 全部可解析，步驟不提交／取消 job、不安裝 server 或執行 Python/model，endpoint 為占位符，清楚說明三分鐘不含 VPN／training 環境準備。

## 2. 整合六份文件與版本語意

File lane：`README.md`、`MCP_GUIDE.md`、`docs/user-guide.md`、
`docs/training-user-pack/README.md`。依賴 Lane 1 參考路徑與契約，不重寫 runtime 內容。

- [x] 2.1 更新 README 的用途、能力分類、使用者／Operator 分流及新文件入口，移除首頁內嵌 private endpoint、舊版本與舊 artifact 名稱；驗證：從首頁能找到 quick start、工具參考與維運／歷史資料，靜態狀態對齊既有部署證據，不將 implementation fixed、verified 或 hotfix hash 混為一談。
- [x] 2.2 整理 MCP_GUIDE 的能力／版本表、日常流程與 troubleshooting，將完整參數參考集中至新文件；驗證：artifact 1.0.1 加 hotfix、guide 1.0.0、協定協商與 smoke 2025-06-18、SDK lock 2.2.0 分列且標明來源，不宣稱新增 runtime version query；timeout／不完整回應／metadata failure 先核對、不盲目重試，submitted 與 terminal state／training 成功分開。
- [x] 2.3 在工程師指南與 training 使用者包加入通用入口，保留已核准 pilot 限制與既有內容；驗證：hank job 545 仍只是歷史五步成功案例，不複製既有 output 寫入 command 作 quick start，不自動標記新帳號、取消/resume 或所有 workers 通過，shared UID／未 sandbox／無 worker preflight 與 AI MCP-only 規則仍清楚可見。

## 3. 文件整體驗證與交付

File lane：`scripts/validate-wave-workflow.sh` 的相容修正；驗證六份文件與本 change artifacts。
驗證期間不修改既有 staging；完成後依 Owner 指示分組準備 commit。

- [x] 3.0 移除 validator 無條件的 nested-spec 檢查，委由既有 OpenSpec strict 判定 delta／skip_specs；驗證：合法 skip 的隔離 fixture 通過，未宣告 skip 且缺 delta 的 fixture 仍被整體 validator 拒絕，CLI 不可用仍失敗，其他 gates 不變。
- [x] 3.1 驗證相對 links/anchors、fenced JSON、工具集合／預設值與版本表；驗證：用非 Python 的 Node／shell 檢查六份文件的 link targets/anchors 與 JSON，對照 source signature、manifest、lock、onboarding constants 及 smoke protocol；新文字不含 private-IP endpoint、credentials，明確區分 GitHub Markdown 顯示與尚未建置的 Pages 網站。
- [x] 3.2 跑 `git diff --check`、`bash scripts/lint-agent-integrations.sh`、`bash scripts/validate-wave-workflow.sh`、`openspec validate document-mcp-user-experience --strict`，並確認變更範圍與 index 未變；驗證：所有 gates 通過，14 個既有 staged 檔案及 cached binary patch SHA-256 與 apply 前相同，未改 Python／設定／其他既有變更，回報可重跑命令與剩餘限制，不執行 live job／deploy／restart／push；commit 留待另行確認。

## Validation Evidence

2026-10-22，實作者完成以上八項；這不是獨立 reviewer 的 verified，
也不完成另一個 onboarding change 尚未執行的驗收。

- 六份文件的 Node 靜態檢查：75 個 local links/anchors、10 個 JSON examples、
  九個工具集合與參數／預設值、四類版本來源均通過。
- 隔離的 HEAD+index checkout 加本次 validator／文件變更：合法 `skip_specs` 的
  整體 Wave validator 為 0 errors；新增無 skip、缺 delta 的普通 change 後，
  只有該 change 被拒絕（1 error）；保留 Node 20、移除 OpenSpec CLI 後亦
  fail closed（1 error）。Fixture 已刪除，未修改現有 changes 作負向測試。
- 既有 14-file staging binary patch SHA-256 仍為
  `96ca7db262778ffc230afdab916596e7fa1f50d0014e725ab5f5d5913588b1af`。
- VS Code diagnostics tool 未註冊 implementation，不能宣稱 IDE diagnostics 通過；
  下列 repository gates 與 shell syntax check 實際通過。未執行 Python tests、
  cluster job、live smoke、deploy、restart、Pages 發佈或 push。
- Owner 後續核准兩組提交：原有 14 檔案已成為 `2bf58ee`；文件組擴至
  23 檔案，納入既有 AI integration、training pack、部署／驗證紀錄及
  onboarding planning，以免 GitHub 連結指向未提交檔案。此為提交範圍確認，
  不新增 server 行為，亦不變更 onboarding reviewer task 的未完成狀態。
- 23-file index-only checkout 的最終驗證：20 份 staged Markdown，
  27-file link closure／102 個 links/anchors、12 個 JSON examples、
  九工具／13 個參數型別與預設值；Wave 0 errors／0 warnings，兩個相關
  changes 的 strict validation 通過。不依賴未提交的 demo、identity planning、
  TEAM_LOG／acceptance 歷史修改或一次性 rollout script。

可重跑的 repository gates（在 repository root）：

```bash
export PATH="$HOME/.nvm/versions/node/v20.17.0/bin:$HOME/.local/bin:$PATH"
git diff --check
bash -n scripts/validate-wave-workflow.sh
bash scripts/lint-agent-integrations.sh
bash scripts/validate-wave-workflow.sh
openspec validate document-mcp-user-experience --strict
```

## 4. Owner 核准的內部 endpoint 修正

2026-10-22，Owner 改以實際內部 endpoint 取代連線範例占位符。
以上八項為原提交的歷史驗證，當中的占位符／不含 private-IP 要求不再作為本項門檻。
File lane：README、MCP_GUIDE、quick start，以及 training pack README、
client setup、migration card；不改 runtime guide、live service 或權限。

- [x] 4.1 將內部 MCP 設定統一為 `http://192.168.51.48:8766/mcp`，清楚區分 8766 MCP 與 8765 API；保留 VPN／內網限制及 credentials／個人設定不提交規則，修正不一致的 endpoint 分享說明。驗證：六份文件 JSON／links 與 endpoint 一致，無 credentials；重跑 policy、Wave、OpenSpec strict 與 whitespace gates。

驗證結果：六份文件 endpoint 一致，四個 JSON examples 可解析且使用正確 MCP URL，
57 個 local links 存在，無 API URL 或常見 credential patterns；policy、Wave
（0 errors／0 warnings）、strict 與 whitespace gates 通過。此為文件靜態驗證，
不是新的 live connectivity 或 GPU readiness 證明。

交付：另建確認過訊息的 commit，再依已核准目標 push；不部署、不公開網站、
不直接修改 main。這些 Git 操作不作為文件實作 checkbox 的驗證替代。
