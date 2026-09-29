# GPU Platform v1 deployment artifact

此目錄是離線 release 輸入，不是 live `/etc` 設定。`artifact.json` 固定 release、Python、service 與 network boundary；`requirements-service.lock` 僅供獨立 service venv 使用，不得套用至 training venv。

Internal API 綁定 `127.0.0.1:8765`；Owner 核准的 pilot MCP 綁定 controller 的私有位址 `192.168.51.48:8766`。Reverse proxy 範例仍為 loopback-only，留作未來 HTTPS/VPN/SSO gateway 使用。MCP listener 不得改成 `0.0.0.0` 或公開到 Internet。

建立 artifact：

```bash
ARTIFACT_OUTPUT_DIR=/tmp/gpu-platform-artifacts ./scripts/build-platform-v1-artifact.sh
```

此命令只建立 deterministic tar 與 SHA-256，不安裝套件、不寫入 `/etc`、不重啟 service。

部署後的 read-only MCP 驗收：

```bash
bash /opt/gpu-platform/current/deploy/platform-v1/smoke-mcp.sh
```

Live 操作只能依 `docs/platform-v1-rollout.md`，在完整填寫核准紀錄並取得 Owner approval 後執行。