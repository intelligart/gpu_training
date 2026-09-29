# GPU Platform v1

這個 repository 是 Slurm、LTX-2、DCGM 與 training 的私有控制面。AI client 透過核准的 MCP endpoint 提交工作，internal adapter 再呼叫 Slurm；工程師不需要也不得把 raw submission API 設成 agent action。

## 目前狀態

- `ia-ai-server-5` 已有 legacy `slurm-api`、`slurm-mcp` 與 Slurm controller 正在服務；這次工作是原地升級，不是從零安裝叢集。
- OpenSpec `launch-platform-v1`：`15/17` tasks 完成。
- MCP contract、submission isolation、SQLite metadata、精確 log、cleanup、deployment artifact、preflight 與 rollback runbook 已完成。
- Slurm MCP job `528` 已通過 20 個 unit/concurrency tests 與全部 preflight gates。
- Slurm MCP job `531` 已驗證 clean venv install、`pip check`、service imports 與 exact dependency lock。
- 尚未把既有 application services 切換到 v1 artifact，也尚未執行 v1 canary；這兩項需要 Owner 另外核准。

## 文件入口

- [工程師交付與部署指南](docs/platform-v1-engineer-handoff.md)：成果、架構、部署、工程師 onboarding 與日常使用。
- [Rollout/rollback runbook](docs/platform-v1-rollout.md)：live 變更紀錄、核准、健康檢查與回滾。
- [MCP 使用說明](MCP_GUIDE.md)：AI client 設定、工具與 submission 範例。
- [AI integration contract](docs/agent-training-integration.md)：MCP-only、no-fallback 與必要參數。
- [平台架構](docs/platform-architecture.md)：repository、Training/Admin domain 與 Wave 邊界。
- [v1 deployment artifact](deploy/platform-v1/README.md)：manifest、dependency lock、service 與 gateway 範例。

## 離線驗證

Operator 在 deployment 前執行：

```bash
PYTHON_BIN=<approved-python> ./scripts/preflight-v1.sh
ARTIFACT_OUTPUT_DIR=/tmp/gpu-platform-artifacts ./scripts/build-platform-v1-artifact.sh
sha256sum --check /tmp/gpu-platform-artifacts/gpu-platform-v1.0.0.tar.gz.sha256
```

Preflight 只執行 syntax、unit/concurrency tests、OpenSpec、Wave、deployment config、runbook 與 whitespace checks；不提交 training、不修改 live `/etc`、不重啟 service。

## 使用原則

- AI training、模型執行與 Python training script 只透過 MCP `submit_job`。
- 每次提交必須提供已確認的 `username` 與 `venv`。
- Training data 放在 `/storage/Internal_NAS/`；共享 venv 放在 `/storage/Internal_NAS/venvs/`。
- MCP 不可用時停止並回報，不得在 client 主機、IDE terminal 或 raw API fallback。
- v1 pilot 只綁 `192.168.51.48` 私有位址並限受信任內網；完整 HTTPS/SSO/RBAC 與 per-user ownership enforcement 尚未完成。
