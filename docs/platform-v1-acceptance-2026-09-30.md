# GPU Platform v1 rollout 與 canary acceptance record

狀態：implementation fixed；非實作者 reviewer verification pending。

## 核准與範圍

| 欄位 | 紀錄 |
|---|---|
| Target node | `ia-ai-server-5` |
| Maintenance window | 2026-09-30 01:50-02:15 CST |
| Owner approval | 本次 VS Code Copilot session；2026-09-30 01:30 CST 前確認現在開始切換，並核准下列 canary 參數 |
| Expected impact | `slurm-api` 與 `slurm-mcp` 切換期間 submission 暫停 1-3 分鐘；既有 Slurm jobs 不受影響 |
| Authorized services | 僅 `slurm-api.service`、`slurm-mcp.service`；不重啟 Slurm controller、worker 或 Munge |
| Canary | `username=hank`、`venv=yujong`、1 GPU、`ia-ai-server-5`、短版 Torch CUDA smoke、無 dataset |
| Validation owner | 待指定非實作者 reviewer |

## Release 與 rollback

| 欄位 | 紀錄 |
|---|---|
| Artifact | `/storage/SSD2/hank/gpu_training/dist/gpu-platform-v1.0.0.tar.gz` |
| Artifact SHA-256 | `0a01d671cef4267fa86206f37d338d7994d29183ddb64b0b189df7f130a377e1` |
| Manifest | `/opt/gpu-platform/releases/1.0.0/deploy/platform-v1/artifact.json` |
| Live release | `/opt/gpu-platform/releases/1.0.0` |
| Service venv | `/opt/gpu-platform/venvs/1.0.0` |
| Current symlink | `/opt/gpu-platform/current` -> `/opt/gpu-platform/releases/1.0.0` |
| Previous release | `/opt/gpu-platform/releases/legacy-6046d686` |
| Backup directory | `/opt/gpu-platform/backups/20260930T015008-CST` |

Artifact 重建與 checksum 驗證：

```bash
cd /storage/SSD2/hank/gpu_training
ARTIFACT_OUTPUT_DIR="$PWD/dist" ./scripts/build-platform-v1-artifact.sh
sha256sum --check dist/gpu-platform-v1.0.0.tar.gz.sha256
```

備份 checksum：

```text
17fa3b2115f45650fe9738bcbf8be0db1f53d9a4b717ca7569bc7757230b4100  slurm-api.service
e4e2af2a98c9c6bae09694c5a1ad89c50558988970d4c724e9cc929f64216cb1  slurm-mcp.service
14b5be7da2b0f92d44a58f5428b07e8683b252d2eebebe8ef517b95be304c34d  rollback/slurm-api.service
e26501bf06d293683599d00286f98aa2d9d1f9594aa1e15ec4aea66ea2724641  rollback/slurm-mcp.service
```

核准的 rollback command：

```bash
sudo ln -sfn /opt/gpu-platform/releases/legacy-6046d686 /opt/gpu-platform/current
sudo install -m 0644 /opt/gpu-platform/backups/20260930T015008-CST/rollback/slurm-api.service /etc/systemd/system/slurm-api.service
sudo install -m 0644 /opt/gpu-platform/backups/20260930T015008-CST/rollback/slurm-mcp.service /etc/systemd/system/slurm-mcp.service
sudo systemctl daemon-reload
sudo systemctl restart slurm-api.service slurm-mcp.service
```

Rollback MUST 保留 SQLite history、run directories、source cache、generated scripts、logs、recovery records、Slurm spool 與既有 jobs。

## Live rollout 結果

- v1 services 於 2026-09-30 02:03:57 CST 啟動，執行 identity 為 `hank:hank`。
- API 使用 `/opt/gpu-platform/venvs/1.0.0/bin/python` 與 release `1.0.0`，只綁 `127.0.0.1:8765`。
- MCP 使用相同 service venv 與 release，只綁 `192.168.51.48:8766`；未建立 `0.0.0.0:8765/8766` listener。
- `/health` 回傳 `{"status":"ok","service":"slurm-api","version":"1.0.0"}`。
- Protocol-aware smoke 完成 MCP initialize、`tools/list`、read-only `cluster_info` 與 session close。
- `slurm-api.service`、`slurm-mcp.service`、`slurmctld.service` 均為 `active`；`scontrol ping` 回報 primary controller `UP`。
- 2026-09-30 02:04:41 CST 檢查時 pending/running jobs 為 0；切換未中斷既有 job。
- Restart 瞬間舊 MCP session ID 的 404 為預期 reconnect 行為；新 session 隨後完成完整 smoke。

可重跑的 read-only health checks：

```bash
curl --fail --silent --show-error http://127.0.0.1:8765/health
bash /opt/gpu-platform/current/deploy/platform-v1/smoke-mcp.sh
systemctl is-active slurm-api.service slurm-mcp.service slurmctld.service
scontrol ping
ss -ltn | grep -E '127\.0\.0\.1:8765|192\.168\.51\.48:8766'
```

## MCP canary request

Canary 僅經 v1 MCP `submit_job` 提交，參數如下：

| 欄位 | 值 |
|---|---|
| `username` | `hank` |
| `venv` | `yujong` |
| `gpu` | `1` |
| `nodelist` | `ia-ai-server-5` |
| `mem` | `8G` |
| `job_name` | `platform-v1-canary` |
| `repo_url` | `/storage/SSD2/hank/gpu_training` |
| `branch` | `6046d6869749ac07491100aa60cec0018ac0184b` |

Command：

```bash
python -c 'import json, torch; assert torch.cuda.is_available(), "CUDA unavailable"; assert torch.cuda.device_count() >= 1, "No allocated CUDA device"; device = torch.device("cuda:0"); left = torch.ones((1024, 1024), device=device); right = torch.full((1024, 1024), 2.0, device=device); result = left @ right; torch.cuda.synchronize(); assert result[0, 0].item() == 2048.0; print(json.dumps({"cuda": True, "device_count": torch.cuda.device_count(), "device_name": torch.cuda.get_device_name(0), "result": result[0, 0].item()}))'
```

## MCP canary 結果

| 欄位 | 結果 |
|---|---|
| Submission ID | `69f58c3caf8748a295c57f8e8dc22a23` |
| Slurm job ID | `534` |
| Initial status | `submitted` |
| Source commit | `6046d6869749ac07491100aa60cec0018ac0184b` |
| Run path | `/storage/Internal_NAS/slurm-runs/hank/69f58c3caf8748a295c57f8e8dc22a23` |
| Script path | `/tmp/slurm-generated/69f58c3caf8748a295c57f8e8dc22a23/job.sh` |
| Log path | `/storage/Internal_NAS/logs/hank/69f58c3caf8748a295c57f8e8dc22a23/slurm_534.out` |
| Slurm terminal state | `COMPLETED`, `ExitCode=0:0`, `DerivedExitCode=0:0` |
| Runtime | 2026-09-30 02:14:08-02:14:28 CST；20 秒 |
| Allocation | `ia-ai-server-5`、`gres:gpu:1`、4 CPU、8 GiB memory |

MCP `get_logs(job_id="534")` 由 metadata 解析上述 exact log path，回傳：

```json
{"cuda": true, "device_count": 1, "device_name": "NVIDIA RTX A6000", "result": 2048.0}
```

其他證據：

- Live `/history` 保存完整 MCP request、submission/job ID、固定 commit 與三個 artifact paths。
- Run directory 的 `HEAD` 為 `6046d6869749ac07491100aa60cec0018ac0184b`，worktree clean 且沒有 Git remote，後續 fetch 無法改動此 accepted source。
- `slurm-api.service` 使用 `PrivateTmp=yes`；script 在 service namespace 中存在、mode `755`、SHA-256 為 `7ada3ae1b12812d8306c03c151bb0d672a1bc36ec4bee3301a96f60ddb263001`。
- Script 的 job name、GPU、node、memory、venv、run directory 與 exact log template 均符合 request；script、run 與 log path 都由 submission ID 隔離。
- Exact log 為 mode `640`、87 bytes；MCP lookup 與 `scontrol` 的 stdout/stderr path 相同。

可重跑的 acceptance checks：

```bash
scontrol show job -dd 534
curl --fail --silent --show-error 'http://127.0.0.1:8765/history?limit=20' \
  | jq '.jobs[] | select(.submission_id == "69f58c3caf8748a295c57f8e8dc22a23")'
git -C /storage/Internal_NAS/slurm-runs/hank/69f58c3caf8748a295c57f8e8dc22a23 rev-parse HEAD
cat /storage/Internal_NAS/logs/hank/69f58c3caf8748a295c57f8e8dc22a23/slurm_534.out
```

非實作者 reviewer 仍 MUST 重跑 acceptance 並留下 identity/result，之後才可將本 change 標為 verified 或 archive。