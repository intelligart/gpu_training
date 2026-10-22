## Context

目前 `mcp_server.py` 將 AI tools 轉送至 `slurm_server.py` 的 FastAPI endpoint；後者以 `/tmp/slurm-generated/<job_name>.sh` 產生 script，並在 job 啟動時於共用 repo checkout 執行 fetch、checkout 與 pull。這使相同 job name 可覆寫 script，也讓多個 job 在 lock 釋放後繼續共用 mutable source tree。SQLite history 只記錄 job 層級欄位，log lookup 則使用 wildcard 的第一個結果。

OpenSpec 已在 `gpu_training` 以 spec-driven schema 初始化，Claude 與 GitHub Copilot 的官方入口也已生成。Slurm planning home 仍有進行中的 change，因此需要一段不複製 active checklist 的過渡期。完整行為契約見本 change 的四份 delta specs。

## Goals / Non-Goals

**Goals:**

- 讓 `gpu_training` 成為後續跨 repo Wave 的權威 planning home。
- 讓 AI training submission 只有一條受支援路徑：AI client → MCP → internal API → Slurm。
- 讓每個 submission 在 script、source、log 與 metadata 層級都可獨立識別與重現。
- 在不影響 live cluster 的情況下完成測試與部署準備，再以明確核准的 canary 上線。

**Non-Goals:**

- 本 change 不搬移 Slurm 目前的 active changes，也不修改三個 upstream repo 的歷史。
- 本 change 不提供通用 Slurm admin shell、daemon restart tool 或自動 production 升級。
- v1 不完成企業 SSO、完整 RBAC、多租戶計費或公開雲端服務；這些需要後續 security change。
- v1 不把 Training domain 從 `gpu_training` 拆成獨立 repo，但維持可抽離的 contract 邊界。

## Decisions

### 1. `gpu_training` 是新 change 的 planning home

官方 OpenSpec generated skills/prompts 留在 `gpu_training`，Wave 手冊、issue workflows、trackers 與 validator 也在此 repo 維護。Slurm 的 active changes 原地完成；archive 後只作歷史，不再接收新的內部跨 repo change。

替代方案是立即搬移 active change，但會產生兩份 task 狀態、破壞 issue 連結並模糊驗證責任，因此不採用。

### 2. 一個主要 task lane 對應一張 GitHub issue

OpenSpec `tasks.md` 是 checklist 權威來源；GitHub issue 用於認領、討論與驗證證據。Issue 建立必須延後至 design 核准後，要求明確的 `WAVE_GH_REPO`，並在 mutation 前顯示目標和動作。四個 v1 lane 預計各一張 issue，但若 tasks 最終合併 lane，issue 數量也隨之調整。

替代方案是每個 checkbox 一張 issue，會增加同步成本且容易讓 issue 與 OpenSpec 狀態分歧，因此不採用。

### 3. MCP 是 AI client contract，HTTP API 是內部 adapter boundary

Claude、ChatGPT 與後續 agent 只註冊 MCP endpoint。MCP tool validation 要求 `username` 與 `venv`，失敗時禁止降級至 local execution。Raw API 保留給 MCP service 與受信任內部 UI；v1 不把它宣告為 agent action，也不把它直接發布至網際網路。

僅依賴 prompt 無法形成後端安全邊界，但 v1 又不包含完整 SSO/RBAC。因此 v1 同時使用 client tool allowlist、內部 network boundary、backend input validation 與 audit metadata；每使用者授權和 job ownership enforcement 留給緊接的 security change，且在完成前服務只限可信任內部使用者。

### 4. Submission ID 在 `sbatch` 前產生

每次 request 先建立 UUID submission ID，再由它衍生唯一 script path、run directory、log path 與 metadata row；Slurm job ID 在 `sbatch` 成功後回填。`job_name` 維持人類可讀標籤，不參與唯一性判斷。

替代方案是只使用 Slurm job ID，但 job ID 在 script 與 source 準備完成後才可取得，無法避免提交前的路徑碰撞。

### 5. Source cache 與 immutable run directory 分離

每個 user/repository 可有一個受 per-repository lock 保護的 Git object cache。Submission 在 lock 內 fetch 並解析 branch/ref 至 commit，接著在 submission 專屬 run directory materialize 該 commit；job 執行期間不再 checkout 或 pull 共用工作樹。Metadata 記錄 remote、requested ref 與 resolved commit。

優先採用 Git worktree 或 shared clone 以避免完整複製 objects；選用方式必須讓 active run directory 不受後續 fetch/checkout 影響。替代方案是在整個 job runtime 持有共用 repo lock，雖可避免檔案變動，但會把同 repo 的 training 全部序列化，因此不採用。

### 6. SQLite 保存 submission 關聯，檔案查詢不再猜測

History schema 增加唯一 `submission_id`、`job_id`、source identity、artifact paths、request payload 與狀態欄位。Migration 採 additive schema change 與 transaction；既有 row 保留，必要欄位可標記為 legacy unknown。Log endpoint 先由 job ID 查 metadata 中的精確 path，不再以 recursive wildcard 第一筆作權威結果。

若 `sbatch` 成功但 metadata finalize 失敗，adapter 回傳明確 partial failure 並把 job ID 寫入 fallback recovery record/log，讓 operator 可查找或取消；不得靜默回報完整成功。

### 7. 測試不接觸 live Slurm，rollout 分成 preflight 與 canary

單元與 concurrency tests 以 temporary directories、temporary SQLite database 及 mocked subprocess 驗證唯一性、commit pinning、精確 log lookup 與失敗補償。Preflight 只執行 syntax、tests、OpenSpec 與 deployment config check。

Live rollout 是獨立核准步驟：先備份目前 service artifact/config，列出 node、影響與 rollback，再切換服務並執行 read-only health checks。只有 owner 明確批准後，才透過 MCP 送低風險 canary job；不以 service restart 或 job submission充當離線測試。

## Risks / Trade-offs

- [每個 submission 的 run directory 增加儲存使用量] → 使用 shared Git objects、明確 retention policy，且 cleanup 跳過 pending/running job。
- [SQLite migration 與併發寫入可能產生 lock contention] → 使用短 transaction、busy timeout、唯一 constraint 與 concurrency regression test；v1 規模超出 SQLite 能力時再改用外部資料庫。
- [MCP-only 在沒有完整 identity provider 時仍依賴內網信任] → v1 限制於受信任內網並保留 audit；SSO/RBAC/job ownership 作為上線後最高優先 security change。
- [Legacy `repo_dir` 或 `script_path` 無法提供相同可重現性] → v1 對 AI MCP 路徑停用 legacy bypass；受信任 operator 的相容入口必須明確標記且不宣告給 agent。
- [Git worktree cleanup 失敗可能留下磁碟資料] → cleanup 採 idempotent 操作並提供 dry-run/list command，不在 submission critical path 強制刪除。

## Migration Plan

1. 在 `gpu_training` 完成 Wave 手冊、trackers、GitHub safety workflows 與 validator；確認 Slurm active changes 仍留在原處。
2. 先以 additive migration 擴充 submission metadata，再加入唯一 artifact/source preparation；以 mocked tests 驗證同 user 併發，不呼叫 live `sbatch`。
3. 收緊 MCP validation 與 agent instructions，更新 Claude、Copilot 與 ChatGPT 的設定文件，只註冊 MCP endpoint。
4. 建立 versioned deployment artifact、preflight script、health check 與 rollback runbook；在未核准前只執行離線 preflight。
5. Owner 核准 node、影響與 rollback 後，備份目前 service artifact/config，部署 v1 並執行 read-only health checks。
6. Owner 另行核准 canary 後，經 MCP 提交 fixture，保存完整 acceptance evidence。

Rollback 時恢復上一版 service artifact/config 並重跑 read-only health check；不刪除 SQLite、run directories、logs、Slurm spool，也不取消既有 job。若新 schema 已寫入資料，舊版必須忽略新增欄位而非執行 destructive downgrade。