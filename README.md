# Slurm GPU Platform

**透過 MCP，讓你的 AI client 查詢 GPU 叢集、提交訓練、讀取 log，並由 Slurm 排程執行。**

你提供固定的 Git 程式版本、NAS dataset/config、核准的環境與資源；
AI 整理摘要、取得確認後呼叫 MCP，不在你的電腦上偷偷執行 training。

**[三分鐘快速開始](docs/mcp-quickstart.md)** ·
**[MCP 工具參考](docs/mcp-tool-reference.md)** ·
**[版本與操作指南](MCP_GUIDE.md)** ·
**[遷移既有 training](docs/training-user-pack/README.md)**

## 可以做什麼？

| 需求 | 使用方式 |
|---|---|
| 第一次使用 | `get_onboarding_guide` 取得必要資料、確認流程與限制 |
| 了解叢集與環境 | `cluster_info`、`gpu_status`、`list_venvs` |
| 執行自己的程式 | 明確提供 `username`、`venv`、command，確認後以 `submit_job` 提交 |
| 追蹤實驗 | 保存 submission/job ID，使用 `list_jobs`、`job_history`、`get_logs` |
| 停止自己的工作 | 先核對 job，再明確確認 `cancel_job` |

```text
Your MCP client
  --> Slurm MCP
    --> fixed Git source + approved venv + NAS data/config
      --> Slurm allocation
        --> exact log + experiment output
```

## 第一次連線：先只讀，不自動跑 demo

1. 向 Operator 取得 MCP endpoint、VPN access、已確認的 username/venv 與資源政策。
2. 依 [quick start](docs/mcp-quickstart.md) 設定 VS Code/Copilot 或核准的 MCP client。
3. 請 AI 讀指南、查 cluster／venvs／GPU，**不要提交或取消 job**。
4. 若要 training，再填 [遷移資料卡](docs/training-user-pack/migration-card.md)，
   核對 worker／GPU occupancy、獨立 output、成功／停止條件，另行確認一次提交。

使用者只連線 client，不需要安裝 Slurm 或自己的 MCP server。
完整 endpoint 與 credentials 保留 machine-local，repository 只使用占位符。
MCP 不可用時停止；AI 不得改成本機、notebook training 或 raw API fallback。

## 目前能力與證據

文件更新：2026-10-22；以下是已保存的部署／執行證據，不是當下 GPU readiness：

- 平台為 **1.0.1 加 MCP GPU telemetry hotfix**；guide 內容版本為 **1.0.0**。
  SDK、協定與平台版本不同，見 [版本對照](MCP_GUIDE.md#版本與相容性)。
- Hank 的 LTX-2.5 job **545** 用固定 Git source 加 NAS YAML，直接呼叫官方 entrypoint，
  完成五步 LoRA training 並保存 checkpoint，沒有額外 NAS runner。
  這證明 smoke pipeline，不代表模型品質、所有 workers 或新帳號 onboarding 已驗收。
- Onboarding tool/resource/prompt 已部署並有測試紀錄；獨立 reviewer 驗收仍待完成，
  不把「已部署」當作「已 verified」。

[Training 成功案例與限制](docs/mcp-training-handoff-2026-10-20.md) ·
[Onboarding 驗證紀錄](docs/onboarding-implementation-evidence.md) ·
[1.0.1 部署歷史](docs/release-1.0.1-test-deployment.md)

## 使用前必讀

- 目前限受信任 VPN/private network，所有 submission 使用 shared service identity。
  `username` 是 audit label，不是認證或 per-user Unix execution。
- 尚未提供 sandbox、強制 dataset/venv 唯讀或跨使用者隔離。不要修改共享輸入；
  每次實驗使用新 output/cache，分目錄不是安全隔離保證。
- 沒有自動 worker preflight；venv 清單、空 queue、Slurm IDLE 都不能證明 GPU 可用。
- 沒有獨立 `job_status` tool；queue 消失不表示成功。提交 timeout／缺 ID 時先核對，
  不盲目 retry，以免建立重複 job。
- 這是含 Slurm、LTX-2、DCGM 整合工作的私有控制面，不是公開匿名 GPU 服務。

## 依角色找文件

| 角色 | 入口 |
|---|---|
| 新使用者 | [Quick start](docs/mcp-quickstart.md)、[MCP 指南](MCP_GUIDE.md) |
| 已有 training workflow | [Training 使用者包](docs/training-user-pack/README.md)、[工程師使用指南](docs/user-guide.md) |
| AI client／整合者 | [工具參考](docs/mcp-tool-reference.md)、[AI integration contract](docs/agent-training-integration.md) |
| Operator | [工程交付](docs/platform-v1-engineer-handoff.md)、[rollout/rollback](docs/platform-v1-rollout.md)、[artifact](deploy/platform-v1/README.md) |
| 維護與歷史查證 | [平台架構](docs/platform-architecture.md)、[v1 acceptance](docs/platform-v1-acceptance-2026-09-30.md) |

### GitHub 閱讀與文件網站

Push 後，有 repository 權限的人可以在對應 branch 直接閱讀本 README 與相連 Markdown；
若尚未合併到 default branch，請先切換 branch。這不需要重新部署 MCP server。
本次沒有建立 GitHub Pages 網站；獨立網站與公開範圍須另行核准。
Private repo 不保證 Pages 網站自然私有，不應直接發佈整個含維運證據的文件目錄。
