## 1. Wave 控制面遷移

- [x] 1.1 在 target repo `gpu_training`（建議 branch `platform/wave-control-plane`）建立 `.claude/CLAUDE.md`、`SUB_AGENT_CHEATSHEET.md`、`ROADMAP.md`、`ISSUES.md`、`TEAM_LOG.md` 與必要的 `.github` Copilot instructions；限制寫入 workflow 文件，不搬移 Slurm active changes，並以檔案存在檢查及關鍵安全規則搜尋驗證
- [x] 1.2 在 `gpu_training` 移植 Wave issue skills/prompts 與 `scripts/setup-wave-workspace.sh`、`scripts/validate-wave-workflow.sh`；所有 `gh` mutation MUST 要求 `WAVE_GH_REPO`、拒絕 `SchedMD/slurm` 並先預覽，驗證方式為 shell syntax check、無 target 時的拒絕測試及 workflow validator
- [x] 1.3 記錄 Slurm、LTX-2、DCGM 的 target repo、upstream、checked-out commit、candidate/deployed version 與更新政策，並以 schema/config parser 和三個 checkout 的實際 Git 資訊交叉驗證
- [x] 1.4 驗證 `gpu_training` 可獨立執行 `openspec list`、`openspec validate launch-platform-v1 --strict` 與 Wave validator，且 Slurm repo 的既有 active changes 仍原地可讀

## 2. MCP-only training submission

- [x] 2.1 在 target repo `gpu_training`（建議 branch `platform/mcp-only-training`）將 MCP submission contract 改為強制非空白 `username` 與 `venv`，回傳 submission ID 與 Slurm job ID，並以 mocked API unit tests 驗證成功、缺參數及 backend failure
- [x] 2.2 將 Claude、GitHub Copilot 與 ChatGPT integration 文件限制為只註冊 MCP endpoint，明列 MCP 不可用時禁止本機或 raw HTTP fallback，並以設定檔／文件 lint 搜尋 raw submission action 與 local Python execution 反例
- [x] 2.3 在 internal API 加入可辨識 MCP/internal UI caller 的 v1 boundary、結構化 validation 與 audit metadata；保留可信任內網相容性但不新增公開入口，並以 FastAPI client tests 驗證 agent 路徑無法使用 legacy `script_path` 或未驗證欄位

## 3. 同使用者併發隔離

- [x] 3.1 在 target repo `gpu_training`（建議 branch `platform/concurrent-submissions`）加入 additive SQLite migration 與 submission repository，保存唯一 submission ID、job ID、source identity、run/script/log path、request payload 與狀態；以 temporary SQLite migration tests 驗證 legacy rows 保留及唯一 constraint
- [x] 3.2 將 script generation 改為 submission 專屬目錄與原子寫入，`job_name` 只作顯示用途；以多執行緒測試同一 user、同名 job 產生不同且內容完整的 script/log/metadata path
- [x] 3.3 實作 per-repository source cache lock 與 submission 專屬 immutable run directory，在 `sbatch` 前解析並固定 commit；以 temporary Git remote concurrency tests 驗證 branch 更新或另一個 submission 不會改變既有 run source
- [x] 3.4 將 log lookup 改由 job metadata 解析精確 path，並處理 `sbatch` 成功但 metadata finalize 失敗的 recovery record；以 mocked subprocess tests 驗證同名 job log 不混用且 partial failure 保留真實 job ID
- [x] 3.5 建立 retention/cleanup 的 list 與 dry-run 行為，查詢 Slurm 狀態後跳過 pending/running submission；以 fixture tests 驗證 active artifact 不被刪除

## 4. v1 部署與驗收

- [x] 4.1 在 target repo `gpu_training`（建議 branch `platform/v1-rollout`）補齊鎖定的 Python runtime/dependencies、versioned service artifact 與 systemd/reverse-proxy 範例；只做離線 parser/config check，不修改 live `/etc` 或 service
- [x] 4.2 建立 `scripts/preflight-v1.sh`，依序執行 Python syntax、unit/concurrency tests、OpenSpec strict validation、Wave validator 與 deployment config check，並在任一 gate 失敗時以非零狀態停止
- [x] 4.3 撰寫 rollout/rollback runbook，要求記錄目標 node、目前 artifact/config 備份、影響、read-only health check 與恢復上一版步驟；以文件 validator 確認禁止刪除 SQLite、run directories、logs 或 Slurm spool
- [x] 4.4 在 Owner 明確核准節點、影響與 rollback 後才切換 live service，執行 read-only health checks 並保存輸出；未取得核准時此 task 保持未完成
- [x] 4.5 在 Owner 另行核准 username、venv、GPU 數與 fixture 後，僅透過 MCP 提交 canary training，驗證 submission/job ID、固定 commit、唯一 artifact 與精確 log；由非實作者 reviewer 重跑 acceptance 後才標記 verified