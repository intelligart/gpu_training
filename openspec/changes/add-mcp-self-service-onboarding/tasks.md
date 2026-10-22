狀態（2026-10-21）：1.0.1 已部署；後續 MCP tests 與封裝驗證通過，實作進度 8/9，
僅獨立 reviewer acceptance（3.3）待完成，非 verified／未 archive。
Tasks 僅在各自驗證通過後勾選。所有 lanes 的 target repo 是 gpu_training。
Bubblewrap、結構化提交、強制唯讀與 writable-path enforcement 只記在 design 後續階段，
不在本 checklist 冒充已完成。部署與 training 的歷史結果不授權新的 live 操作。

## 1. MCP onboarding 內容與入口

File lane：mcp_server.py、新增 onboarding 內容模組、tests/test_onboarding*.py。單一主要寫入者，不修改 slurm_server.py。

- [x] 1.1 建立共用 zh-TW guide，包含版本、username/program/dataset/venv/resources/output checklist、首次連線及 read-only discovery；驗證：內容 tests 確認所有必要項目、dataset 不需要的說明與 shared-hank/未 sandbox 限制。
- [x] 1.2 新增 get_onboarding_guide tool、resource 與 prompt，更新 server instructions 的發現入口；驗證：mock tests 確認三種入口內容一致且不呼叫 backend、submit/cancel 或寫 metadata。
- [x] 1.3 加入摘要確認、1/2 GPU、queue/history/exact logs、兩步取消及 failure 範本；驗證：tests 覆蓋 missing inputs、不猜 username/venv、no-local/no-raw fallback，既有 submit_job signature/contract tests 不變。

## 2. Client 使用指南與 walkthrough

File lane：MCP_GUIDE.md、docs/user-guide.md、docs/agent-training-integration.md。依賴 Lane 1 內容 contract，不和 Lane 1 同時修改相同檔案。

- [x] 2.1 同步 operator 提供 endpoint 的 client 設定占位符與 guide 呼叫示例，說明連線 client 而非安裝 server；驗證：./scripts/lint-agent-integrations.sh 通過，不提交個人 credentials/machine-local config。
- [x] 2.2 文件明列 dataset/output 暫為 command 約定、path/GPU 未經 worker preflight、shared UID 和手動 GPU workloads 限制；驗證：review checklist 確認不宣稱唯讀或跨使用者安全隔離已完成。
- [x] 2.3 分別完成 tools-only client 與支援 resource/prompt client 的只讀 walkthrough；驗證：可找到 guide、理解必要資料及確認流程，沒有真實 submit/cancel，mock transport 或只讀 session evidence 可重跑。

## 3. 封裝、測試與 review handoff

File lane：scripts/build-platform-v1-artifact.sh、scripts/validate-deployment-config.sh、deploy artifact metadata 與新增 packaging tests；依賴 Lane 1。不改 live units 或覆寫既有 release。

- [x] 3.1 將新增 onboarding 模組納入新版本 artifact；驗證：解壓至乾淨 fixture 後 imports/guide tests 通過，無 checkout 依賴，double-build checksum 一致。
- [x] 3.2 執行 focused Python/onboarding tests，Python 執行只經 Slurm MCP，先确认 username/venv，若需 canary/GPU/node 則另取核准，不本機 fallback；驗證：保存 job ID、exact log、tests 結果及 openspec validate add-mcp-self-service-onboarding --strict、Wave validator、git diff --check 結果。
- [ ] 3.3 交獨立 reviewer 重跑 onboarding acceptance；驗證：只讀 guide 不提交、不改 backend contract、三種入口一致，review evidence 留存，實作者不自行標 verified。Live deployment 另需 controller/impact/window/rollback 核准，不在此 task 自動執行。

驗證紀錄：[onboarding implementation evidence](../../../docs/onboarding-implementation-evidence.md)。
Job 535 的 11 pass／2 fail 保留為歷史失敗。後續核准的 CPU-only MCP jobs 536（19+10）、
537（40）、538（42）通過；537、538 的 exact logs 明列真實 SDK walkthrough 與
clean-artifact/double-build tests 通過，支援 2.3、3.1、3.2 的完成紀錄。
2026-10-21 文件限制 checklist、非 Python gates 及 live tool/resource/prompt 只讀 smoke
另見證據文件；本次未提交新 job，也沒有把先前本機 tests 當作 3.2 的 MCP 證據。
Guide version 為內容版本（1.0.0），已部署 artifact 為 1.0.1 加 MCP hotfix，
沿用鎖定 service venv 1.0.0。獨立 reviewer 尚未重跑，3.3 不勾選。
