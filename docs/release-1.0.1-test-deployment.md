# 1.0.1 可測試版：curl／MCP／onboarding

## 目前狀態與歷史範圍

本文保留 2026-10-15 rollout 及其後 MCP GPU hotfix 的證據，不是重新部署的授權。
截至 2026-10-21，API/MCP 為 active；三個 Python source 與 installed 版本的
checksum 各自一致，不需要為了整理或 commit 再 restart。
Hank 後續已完成 server6 LTX-2.5 五步 training；詳見
[training 交接紀錄](mcp-training-handoff-2026-10-20.md)。
下文「未執行 GPU demo」指當時的矩陣 demo／curl 驗收，不表示後續 MCP training 未執行。
Onboarding 獨立 reviewer、新帳號實驗與 real curl submission 仍待完成。

## 核准與範圍

- Owner 於 2026-10-15 對話要求直接部署可測試版，不另建 proposal。
- Target：ia-ai-server-5；窗口：本次 session。僅 API／MCP 短暫中斷。
- Previous release：/opt/gpu-platform/releases/1.0.0。
- New release：/opt/gpu-platform/releases/1.0.1；沿用 service venv 1.0.0。
- VPN bind／MCP endpoint 不變。不 install package、不改 training venv，不重啟
  Slurm／Munge、不動 live Slurm config／firewall／spool、不取消既有 jobs。
- 當時使用 `deploy/platform-v1/rollout-approved.sh`，備份 live
  units/drop-ins/current/artifact，失敗自動恢復 previous units 與 current symlink，
  只重啟 API／MCP。history、run/source/cache/log/recovery 保留。
  該腳本是一次性的 1.0.0 → 1.0.1 遷移，拒絕覆寫既有 release；目前已是 1.0.1，
  不可當作一般 redeploy 指令重跑。腳本的 site-specific 設定另待整理，不屬本次提交分組。

## 實作與測試證據

- Headerless curl 記為 manual-http；歷史 username-less request 明確預設 hank。
  exact legacy source path 例外保留。MCP／Dashboard username 和 venv 仍必填。
- omitted venv 使用 Operator node mapping；explicit venv 優先。activate／python／
  python3／interpreter startup 失敗就停止，不落回 system Python。
- source commit、submission UUID、獨立 artifact、exact log 和 metadata recovery 保留。
- onboarding tool/resource/prompt 可經真實 SDK 存取，無 backend submission side effect。
- MCP GPU formatter 修正 nested state/gpus payload，不再只顯示 node 標題。
- 當時另準備 [hank demo](../hank_demo.py) 的 CUDA fail-fast 修改；
  該修改尚未納入本次提交，不宣稱 repository 已有此行為，也沒有執行 GPU demo。

三次**核准的 CPU-only Slurm MCP**測試均為 hank、service venv 1.0.0、server5、
1 GPU allocation／4G，不做 CUDA、torch import 或 real nested job submission：

| Job | 結果 | exact log（NAS） |
|---|---|---|
| 536 | focused 19 + legacy 10 passed | /storage/Internal_NAS/logs/hank/aeffe49554ce4e20a4b331d4d0d21c05/slurm_536.out |
| 537 | full 40 passed | /storage/Internal_NAS/logs/hank/6b8a39694e2942b0bb70364236a63231/slurm_537.out |
| 538 | final full 42 passed | /storage/Internal_NAS/logs/hank/e6fe15c70a31466298af2c31143d9a08/slurm_538.out |

可重跑的 command（必須經 MCP、另核准 resource plan；不是本機執行指令）：

```text
cd /storage/SSD2/hank/gpu_training && PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 timeout 180 python -m unittest discover -s tests -v
```

測試刻意 cd mutable working tree，以檢查 source candidate；回應中的 source_commit
30874a09f5f4e355cbbc22b080debef477f7dd1d 不是未提交 candidate 的身份。
部署身份以 artifact checksum 為準，不將 checkout commit 當作 release checksum。

Final artifact：/tmp/gpu-platform-artifacts/gpu-platform-v1.0.1.tar.gz。
SHA-256：10f1f01764d78cbb1f9ed1a52f4c8da37d2c3d8b035ac204b5575e188feddbf7。

`git diff --check`、`./scripts/validate-wave-workflow.sh`、
`./scripts/lint-agent-integrations.sh`、`./scripts/validate-deployment-config.sh`、
兩個 rollout/smoke scripts 的 `bash -n` 和 artifact checksum 通過。
Wave 0 errors／0 warnings。systemd parser 有 host 上既存的 snapd／netplan 警告，
沒有因此改動其他 services。

## Worker 與 acceptance 邊界

read-only SSH 驗證歷史 default 的 activate 可讀、python/python3 executable target：
server4 的 local training venv -> Python3.10；server5 ComfyUI venv -> Python3.10；
Server-6 local training venv -> Python3.12。這不是 CUDA／torch compatibility test。
Server-6 的 NAS shared venv Python targets 缺失；不能用 listing 推斷可用。
server5090 的 ltx2 Python3.10 target 同樣缺失，不在 default mapping 中。

GPU canary／舊六 jobs loop 未核准、未執行。確認 node、venv／torch／CUDA、occupancy
後，先只測一個 job；當時 server5 兩 GPU 有其他 active workloads；這是歷史觀察，不可作為目前 occupancy。

## 部署執行紀錄

狀態：2026-10-15 05:41 CST（2026-10-14 21:41 UTC）部署成功；implementation fixed，
不是非實作者 verified。Owner 先執行 sudo authentication，再核准繼續。

- Backup：/opt/gpu-platform/backups/20261014T214104Z-release101。
- Artifact checksum 通過；current 指向 /opt/gpu-platform/releases/1.0.1。
- Health：status=ok、service=slurm-api、version=1.0.1；Dashboard HTTP 200。
- MCP smoke：initialize、discovery、cluster query、onboarding tool/resource/prompt 全通過。
- Live OpenAPI：SubmitRequest only required command；username/venv 可省略，submit/cancel
  routes 保留。這是 read-only schema check，沒有 raw HTTP real submission。
- Listener 仍精確綁 private-IP 的 8765／8766，沒有變更 endpoint 或 firewall。
- API PID 1735366、MCP PID 1735367；Slurmctld PID 4038348、slurmd PID 1938
  與部署前一致，四個 services active、NRestarts=0，controller ping UP。
- 初次 health 在 service startup 時 connection refused，既定 retry 隨後成功；
  沒有進入 rollback。沒有 package install、training venv 修改或 GPU demo execution。

可重跑的 read-only checks：

```bash
: "${GPU_PLATFORM_API:?Operator must supply the approved API base URL}"
curl --fail --silent --show-error "$GPU_PLATFORM_API/health"
bash /opt/gpu-platform/current/deploy/platform-v1/smoke-mcp.sh
systemctl show slurm-api slurm-mcp slurmctld slurmd -p MainPID -p NRestarts -p ActiveState --no-pager
scontrol ping
```

回滾使用 backup 的 slurm-api.service／slurm-mcp.service／10-vpn-bind.conf 恢復
原來三個 unit/config；current 切回 1.0.0，daemon-reload 後只 restart API/MCP，
再核對 health version=1.0.0。不要使用新版 onboarding smoke 當作旧版 acceptance。
GPU demo、real curl/MCP job acceptance 和非實作者 verification 仍獨立處理。

## MCP GPU telemetry hotfix：source 與 live read-only gate 通過

後續 live `gpu_status` 重現 `AttributeError: 'str' object has no attribute 'get'`：
backend 的 `processes` 是文字，但 adapter 假定為物件清單；顯存與使用率亦使用了
不相符的欄位。修復支援實際的 `mem_used_mb`／`mem_total_mb`／`util_pct` 與
process 文字，同時保留 legacy GB／process-list 格式；未知 process 格式明確報錯。
Read-only smoke 加入真正的 `gpu_status` tool call，避免僅 cluster query 通過就放行。

- Owner 已核准 source 修復、測試與 controller `ia-ai-server-5` 的 MCP-only hotfix。
- 核准的 CPU-only MCP job **541** 使用 hank、service venv
  `/opt/gpu-platform/venvs/1.0.0`、server5、1 GPU allocation／4G；沒有 CUDA 或 training。
- 12 個 focused tests 全通過；`scontrol show job 541 -o` 為
  `JobState=COMPLETED`、`ExitCode=0:0`。
- Exact log：
  `/storage/Internal_NAS/logs/hank/aa9d18031f4d40e3ac4254c12aa0e37b/slurm_541.out`。
- 測試明確切回 mutable checkout，驗證的是 source candidate，不把 submission 的
  Git commit 誤稱為未提交修復的身份。
- Candidate adapter SHA-256：
  `450d9e9c79918bbf949ccba714cec357ce43cec89f8d3040c23dd40570ffaf7e`。
- 工具端 `sudo -n true` 顯示需要密碼，因此由 Owner 在終端機執行核准的
  MCP-only hotfix；備份為 `/opt/gpu-platform/backups/mcp-gpu-status-cHPwKmWE`。
- 部署後 installed adapter checksum 與上述 candidate 一致；實際 MCP `gpu_status`
  及 cluster/GPU/onboarding smoke 通過。MCP PID 由 1735367 變為 4168421；
  API PID 1735366、Slurmctld PID 4038348、slurmd PID 1938 未變。
  這是 1.0.1 的 adapter hotfix，不將原始 release tarball checksum 當作已修改檔案的身份。
- 提交前再次查 MCP，server4 GPU 0 已轉為 100% utilization、48262/49140 MB，
  另有手動 workload；因此中止 demo submission，沒有產生新的 demo job ID。
  GPU 1 的較低占用不代表可安全提交，因現有 submission 不保證選到該實體裝置。
  不取消或修改他人的程序，待 Operator 重新確認 occupancy 與授權條件。
- MCP-only 部署須先備份 adapter 與 checksum，只重啟 `slurm-mcp`；
  cluster/GPU/onboarding smoke 失敗時還原 adapter 並只重啟 MCP。
  不重啟 API、Slurm 或 Munge，不改 live Slurm config，不碰他人程序。

可重跑 focused command（仍須核准資源，經 MCP 執行，不在本機執行）：

```text
cd /storage/SSD2/hank/gpu_training && PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 timeout 180 python -m unittest discover -s tests -p test_mcp_submission.py -v
```

部署後的 read-only gate：

```bash
bash deploy/platform-v1/smoke-mcp.sh
systemctl show slurm-mcp slurm-api slurmctld slurmd -p Id -p MainPID -p ActiveState --no-pager
```