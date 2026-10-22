## Why

現有 Slurm MCP 說明已包含 onboarding 與成功短跑，但資訊分散，repository 首頁仍停在舊版本，讀者難以快速了解能做什麼、如何連線，以及回應能證明什麼。參考 Flint MCP 頁面的資訊分層，改善使用者入口與工具參考，而非新增 server 能力或模仿其安裝與互動功能。

## What Changes

- 將 README 整理為簡短的能力入口，分離使用者連線、工具參考、Operator 維運與歷史驗證紀錄。
- 新增三分鐘只讀 quick start：取得 Operator 設定、設定 client、讀指南與 discovery、辨識停止條件；不自動提交示範 job。
- 新增九個既有 MCP tools 的參考：參數、預設值、必要輸入、回傳形式、副作用與已知限制；另列既有 resource/prompt。
- 在 MCP 指南區分平台 artifact、guide 內容、MCP 協定與 SDK 版本，標記成功案例、歷史證據與未驗收能力。
- 補齊 submission timeout／回應不完整／metadata finalize failure 的「結果不確定、先核對、不可盲目重試」說明。
- 保留 shared execution、username audit label、未 sandbox、無 worker preflight／獨立 job_status 的現有限制；不將文件寫成新權限機制。
- 使用相對 Markdown links 與 endpoint 占位符，便於日後另外建立文件網站。GitHub Pages、網站外觀、公開發佈與自動部署不在本次範圍。
- 修正 Wave validator 對純文件 `skip_specs` 的相容性；由既有 OpenSpec strict validation 判定是否需要 delta，一般缺 spec 的 change 仍拒絕。

## Capabilities

### New Capabilities

無。本次僅改善既有功能的說明，未新增可觀察的 server 行為。

### Modified Capabilities

無。既有 submission、onboarding、identity 及部署契約不變。
`.openspec.yaml` 設定 `skip_specs: true`；不為純文件變更建立虛構的 capability delta。

## Impact

Target repo：`gpu_training`。實作限以下六份文件與已另獲核准的 validator 修正：

- `README.md`
- `MCP_GUIDE.md`
- `docs/user-guide.md`
- `docs/training-user-pack/README.md`
- 新增 `docs/mcp-quickstart.md`
- 新增 `docs/mcp-tool-reference.md`
- `scripts/validate-wave-workflow.sh`，僅修正 delta/spec-skip 判定

不修改 Python source、tool schema、共用 runtime guide、tests、dependencies、部署設定或 GitHub workflows；不重新部署、不提交 job、不變更帳號或 NAS 權限。
實作與驗證期間保留目前已 stage 的 14 個 onboarding／封裝檔案；完成後依 Owner 新指示分組準備 commit，另確認訊息後才提交，不 push。
