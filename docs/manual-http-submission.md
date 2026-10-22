# 手動 HTTP／curl 相容入口

## 狀態與邊界

1.0.1 已於 2026-10-15 部署，health／MCP onboarding／legacy schema 檢查通過；
Job 538 的 42 項回歸測試通過，exact log：
`/storage/Internal_NAS/logs/hank/e6fe15c70a31466298af2c31143d9a08/slurm_538.out`。
截至 2026-10-21，real curl submission 與 hank 矩陣 GPU demo 仍未執行。
MCP 已完成 server6 的 LTX-2.5 五步 training（jobs 544、545），其中 job 545
直接使用固定 Git source 加 NAS YAML；詳見 [training 交接紀錄](mcp-training-handoff-2026-10-20.md)。
該結果使用明確指定的新 venv，不驗證歷史 per-node default，也不取代 curl runtime acceptance。
新工作仍須先確認 node、venv 與 occupancy 並核准，不能把部署或單一短跑成功當作所有 worker 的保證。

這是受信任 VPN/private LAN 上**人類手動操作**的入口。AI agent 仍必須經
Slurm MCP `submit_job`，不能透過 curl 或其他 HTTP library 提交工作，也不能將
此入口作為 MCP 故障時的 fallback。來源 header 是 audit label，不是認證；服務
目前使用 shared hank 身分執行，username 不是登入身分或權限隔離。

## 原有 payload 不必偽裝為 MCP

- 不帶 `X-Submission-Source`：記為 `manual-http`。
- 舊 request 缺少 username：記為歷史預設 hank。建議新 request 明確提供 username。
- 明確指定 venv：使用該 shared 名稱或 absolute path，不改成節點預設。
- 省略 venv：worker 按實際 `SLURMD_NODENAME` 選 Operator 管理的預設環境。
- 原有精確 source path /storage/SSD2/hank/gpu_training 保留手動相容例外；其他
  `repo_dir` 仍必須位於使用者工作根目錄。這不是檔案 sandbox。
- `script_path` 仍不接受。MCP／Dashboard 的 username 和 venv 仍必填。
- UUID、Git 固定 commit、獨立 run/script/exact log、metadata recovery 不變。
  local repo 只提供已 commit 的 source，不會把未提交檔案自動帶進 job。

原有單 GPU payload 可在部署與本次 GPU 執行核准後原樣使用；以下 URL 由 Operator
提供於 machine-local 環境變數，不保存 endpoint/credential 到 Git：

```bash
curl --fail-with-body -sS -X POST "$GPU_PLATFORM_API/submit" \
  -H 'Content-Type: application/json' \
  -d '{"command":"python3 -u test_case1_single_gpu.py","gpu":1,"job_name":"test-1","repo_dir":"/storage/SSD2/hank/gpu_training"}'
```

不要為了「修好」入口直接送出原本的六個 jobs。先核對 worker環境、GPU occupancy
並核准一個短跑；Slurm IDLE 不代表沒有其他手動 GPU processes。

## hank demo 的 source／環境

[hank_demo.py](../hank_demo.py) 是五輪 GPU 矩陣運算、每輪等待 15 秒的 demo；不是
training model，也不是 job submission wrapper。提交前仍須核對所選 source commit 的
CUDA 檢查與退出行為，不能只靠 Slurm exit 0 判斷 demo 確實使用 GPU。
它在 hank/demo branch，不能假設預設 main branch 含有此程式。

手動提交 body 範例（**不代表以下 node/venv 已驗證可跑**）：

```json
{
  "command": "python3 -u hank_demo.py",
  "username": "hank",
  "gpu": 1,
  "job_name": "hank-demo",
  "repo_url": "git@github.com:intelligart/gpu_training.git",
  "branch": "hank/demo",
  "venv": "ltx2"
}
```

MCP 使用相同 command/username/gpu/job_name/repo_url/branch/venv 欄位，但**由既有
MCP tool 提交**。先確認 remote branch/commit、目標 node、venv Python/CUDA/torch
與 occupancy；已知 server5090 上 ltx2 的 Python3.10 target 缺失，不可直接使用。
未 push 的修正不會出現在 remote source checkout。

## Operator 的 per-node default policy

服務環境變數 `GPU_PLATFORM_NODE_VENVS` 是 JSON object，node name 對 absolute venv
path；提供時**完整取代**歷史 mapping。請在核准的 service deployment 設定，不原地
修改任何 venv，也不要自動改 Python symlink。worker 不依賴 controller 的 PATH。

```json
{
  "ia-ai-server-5": "/storage/Internal_NAS/venvs/approved-default-v001",
  "ia-ai-server-4": "/storage/Internal_NAS/venvs/approved-default-v001",
  "AI-Server-6": "/storage/Internal_NAS/venvs/approved-default-v001"
}
```

上面是**待 Operator 建立／驗證的示意環境**，不是現存可用環境。
未設定變數時保留歷史相容 mapping：server5 的 /storage/SSD2/hank/ComfyUI/venv，
server4 與 AI-Server-6 的 /storage/SSD2/hank/gpu_training/venv。這些歷史路徑
**尚未完成所有 worker 的 runtime 驗證**，不是健康環境保證。

Malformed/empty policy、或明確 nodelist 沒有 default：HTTP 提交前拒絕。
自動配置到未列出的 node：worker nonzero 停止。啟動前檢查 activate、python 和
python3 檔案及兩個 interpreter 的啟動；activation 或 interpreter 失敗時，不執行
使用者 command、不降級 system Python。缺少 shared libraries／CUDA／torch 仍可能
需要額外 worker qualification；`--version` 不等於 GPU compatibility acceptance。

成功回應與 request audit 記錄 `venv_policy`、`requested_venv`（response）與 default
mapping snapshot；exact log 寫入實際 node／selected venv／interpreter path。
實際 selected node/venv 不會從 queue 中推測，也尚未回寫為獨立 DB 欄位。