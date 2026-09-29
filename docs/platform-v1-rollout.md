# GPU Platform v1 rollout 與 rollback runbook

狀態：操作範本；v1 已於 2026-09-30 完成 live rollout 與 canary，實作者標示 fixed，非實作者 reviewer verification pending。證據見 [`platform-v1-acceptance-2026-09-30.md`](platform-v1-acceptance-2026-09-30.md)。

本文件只定義操作順序。任何 service restart、endpoint 切換或 canary submission 前，Owner MUST 明確核准下列紀錄。未填完核准紀錄時，operator MUST 停止；不得把 preflight 成功視為 rollout 授權。

## 變更紀錄

每次 rollout 建立獨立紀錄並填入：

| 欄位 | 必填值 |
|---|---|
| Target node | `<hostname>` |
| Maintenance window | `<start/end/timezone>` |
| Owner approval | `<approver + timestamp + reference>` |
| Expected impact | MCP/API submission 在切換期間短暫不可用；既有 Slurm jobs 不受影響 |
| Artifact | `<gpu-platform-v1.0.0.tar.gz absolute path>` |
| Artifact SHA-256 | `<sha256>` |
| Previous release | `<resolved /opt/gpu-platform/current target, or immutable legacy snapshot for first rollout>` |
| Backup directory | `<absolute backup path outside the new release>` |
| Validation owner | `<reviewer other than implementer>` |
| Rollback command | `<approved command sequence from this runbook>` |

## 前置條件

1. 在 source checkout 執行 `PYTHON_BIN=<approved-python> ./scripts/preflight-v1.sh`，保存完整輸出。
2. 以 `sha256sum --check <artifact>.sha256` 驗證 artifact，保存結果。
3. 執行 read-only `squeue` 並記錄目前 pending/running jobs；此紀錄只供影響評估，不得取消 job。
4. 確認 application services 的目前狀態、`/opt/gpu-platform/current` 實際 target（若存在），以及目前 unit/proxy config checksum。
5. 將上一版 artifact、service units 與 gateway config 複製到「變更紀錄」指定的 backup directory，並驗證備份非空。
6. 顯示 target node、expected impact、validation、rollback command 與 backup directory，取得 Owner approval 後才可繼續。

### 第一次從 legacy checkout 升級

若 live units 直接執行 mutable source checkout，且 `/opt/gpu-platform/current` 尚不存在，rollout 前 MUST 額外完成：

1. 記錄 running process、unit、listener、health behavior 與 source commit evidence；確認可重建 legacy behavior 的 commit。
2. 從該 commit 建立 immutable legacy release directory。不得將目前已修改的 working tree 當成 previous release。
3. 複製 live units，將 rollback copies 的 source path 改為 immutable legacy release，並執行 parser check。
4. 將 immutable legacy release 與 rollback units 記為 `Previous release`，保存 checksum。
5. 確認 rollback command 會恢復 rollback units，而不是重新啟動指向 mutable checkout 的原 units。

2026-09-29 採證時，`ia-ai-server-5` 沒有 `/opt/gpu-platform`，live services 直接使用 `/storage/SSD2/hank/gpu_training`；commit `6046d6869749ac07491100aa60cec0018ac0184b` 是 legacy snapshot candidate，仍須由 operator 在 rollout record 中確認。

## Rollout

以下命令是核准後由 operator 在「Target node」執行的範本；路徑與版本 MUST 與 artifact manifest 一致。

1. 將已驗證的 artifact 解壓至新的 `/opt/gpu-platform/releases/1.0.0`，不得覆寫 previous release。
2. 使用 `deploy/platform-v1/requirements-service.lock` 建立獨立 `/opt/gpu-platform/venvs/1.0.0`；不得修改 training venv。
3. 將已 review 的 units/proxy config 安裝到核准位置，先執行 parser/config check。
4. 原子切換 `/opt/gpu-platform/current` symlink 至新 release。
5. 僅重啟 `slurm-api.service` 與 `slurm-mcp.service`，不得重啟 Slurm daemon、Munge 或其他 cluster service。
6. 執行下列 read-only health checks。任一失敗即停止並進入 rollback：

```bash
curl --fail --silent --show-error http://127.0.0.1:8765/health
bash /opt/gpu-platform/current/deploy/platform-v1/smoke-mcp.sh
systemctl is-active slurm-api.service slurm-mcp.service
```

`/health` response MUST 包含 `"status":"ok"`、`"service":"slurm-api"` 與 `"version":"1.0.0"`。MCP smoke 完成 initialize、tool discovery 與 read-only cluster query，不提交 job。

## Rollback

Health check、MCP discovery 或 submission adapter check 任一失敗時：

1. 停止新 endpoint 的流量，保留所有 failure output。
2. 將 `/opt/gpu-platform/current` symlink 原子切回「Previous release」。
3. 從「Backup directory」恢復上一版 service units 與 gateway config，先執行 parser/config check。
4. 僅重啟 `slurm-api.service` 與 `slurm-mcp.service`。
5. 重跑上一節的 read-only health checks，確認回復 previous version。
6. 記錄 rollback 時間、operator、原因、health output 與後續 issue。

Rollback MUST 保留 SQLite submission history、run directories、source cache、generated scripts、logs、recovery records、Slurm spool 與既有 jobs。Rollback MUST NOT 執行 destructive schema downgrade、清理 artifact 或取消 job。

## 驗收與證據

保存以下資料至核准的 change record：

- preflight 完整輸出與 exit code
- artifact path、SHA-256 與 manifest
- target node、maintenance window、Owner approval 與 expected impact
- previous release、backup directory 與 config checksum
- rollout 或 rollback command transcript
- read-only health check output
- reviewer identity 與結果；實作者只可標示 fixed，不得自行標示 verified

Canary training 屬於獨立 task。未另行取得 username、venv、GPU、fixture、node、impact 與 rollback 核准前，不得提交 canary。