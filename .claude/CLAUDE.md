# GPU Platform Wave 工作手冊

本 repository 是 Slurm、LTX-2、DCGM 與 training 整合工作的私有控制面。三個開源
專案維持獨立 checkout；本 repo 保存跨 repo 規格、派工、版本 pin、部署 gate 與驗證
證據，不複製它們的原始碼。

## 開工前

1. 讀 `SUB_AGENT_CHEATSHEET.md`。
2. 若工作屬於 OpenSpec change，依 CLI 回傳的 `contextFiles` 讀 proposal、design、
   tasks 與所有 delta specs。
3. 查看所有受影響 repo 的 `git status --short`，保留既有變更。
4. 確認 task lane 的 target repo、branch、檔案範圍與 focused validation。
5. GitHub mutation 前確認 `WAVE_GH_REPO`、登入狀態、目標與操作清單。

## 權威來源

| 資訊 | 權威位置 |
|---|---|
| 尚未規格化的方向 | `ROADMAP.md` |
| 跨 repo change 與 task | `openspec/changes/` |
| 已生效 capability | `openspec/specs/` |
| 小型 bug 與本地 issue ID | `ISSUES.md` |
| Wave 執行與驗證證據 | `TEAM_LOG.md` |
| 平台架構 | `docs/platform-architecture.md` |
| Component checkout 與版本政策 | `config/components.json` |

既有 Slurm planning home 的 active changes 原地完成並 archive。不得在本 repo 建立
平行 checklist，也不得再於 Slurm repo 建立新的內部跨 repo change。

## 角色

- **Owner**：核准設計、風險、live rollout、canary 與最終驗收。
- **Coordinator**：維護 OpenSpec、拆 lane、建立 GitHub issue 並執行整體驗收。
- **Contributor**：只修改獲派 lane，留下可重跑驗證證據。
- **Reviewer/reporter**：重跑 acceptance；實作者不能自行標記 `verified`。

## Wave 流程

1. `/opsx-propose` 建立 proposal、design、delta specs 與 tasks。
2. Owner 核准 design 後，每個 `tasks.md` 二級標題視為一個主要 lane。
3. `/wave-issues` 為每個未完成 lane 建立或重用一張 GitHub issue。
4. Contributor 用 `/start-issue` 認領 lane，再進行 implementation。
5. 每完成一項 checkbox 就執行其 focused validation 並立即更新 tasks。
6. Lane 通過後記錄 `TEAM_LOG.md` 並標示 fixed；由非實作者驗證。
7. 全部 tasks 與整體驗收通過後才 archive change。

## GitHub 安全規則

- 所有 `gh issue` 與 `gh pr` 命令 MUST 帶 `--repo "$WAVE_GH_REPO"`。
- 不得由任一 checkout 的 `origin` 推定內部 issue 目的地。
- 未設定 `WAVE_GH_REPO` 時拒絕 mutation。
- 內部 Wave 拒絕官方 upstream：`SchedMD/slurm`、`Lightricks/LTX-2`、
  `NVIDIA/DCGM`。
- 建立、關閉、指派或留言前，先顯示目標 repo 與完整操作清單並取得確認。

## 執行邊界

- AI training、模型執行或 Python training script MUST 經 Slurm MCP submission tool；
  MCP 失敗時不得降級成本機執行或 raw HTTP submission。
- 未經 Owner 明確授權與 node/impact/rollback 計畫，不得 restart service、修改 live
  `/etc/slurm`、清除 spool、改 firewall、切換 endpoint 或提交 canary job。
- Source checkout、build artifact、installed version 與 running version 是不同事實，
  必須分別採證。
- 不得提交 token、SSH key、Munge key、`.env`、本機 MCP endpoint 或 runtime database。

## 最低驗證

每個 lane 至少執行：

```bash
git diff --check
./scripts/validate-wave-workflow.sh
```

OpenSpec 變更另跑 `openspec validate <change> --strict`。Implementation 依 tasks 加上
focused test；live acceptance 只能在相應 task 已列出目標、影響與 rollback 後執行。