# GPU Platform v1 使用指南

本指南描述工程師如何把自己的測試、training code、dataset 與 Python environment 接到目前已上線的 GPU Platform v1。

第一次連線先看 [三分鐘只讀 quick start](mcp-quickstart.md)；
需要參數、輸出與副作用時看 [MCP 工具參考](mcp-tool-reference.md)。
平台／guide／協定／SDK 版本分別見 [MCP 指南](../MCP_GUIDE.md#版本與相容性)。

已會 training、只要遷移執行方式：從 [Training 使用者包](training-user-pack/README.md) 開始。
先填自己的原始 command/venv，完成一次經核准的短跑，不需要先學 Slurm 維運。

## 1. 標準 flow

```text
Git commit + approved venv + versioned dataset
  -> MCP submit_job
  -> submission ID + Slurm job ID
  -> immutable source commit
  -> Slurm GPU allocation
  -> exact log + NAS experiment output
```

四種資料各有固定位置：

| 內容 | 權威位置 | 原則 |
|---|---|---|
| Code、config、tests、dependency lock | Git repository | Job 前 commit/push；提交完整 commit SHA |
| Dataset、base checkpoint | `/storage/Internal_NAS/` | 不放 Git；使用 versioned path 與 checksum |
| Shared venv | `/storage/Internal_NAS/venvs/<name>/` | Operator 建立、版本化，核准後不原地修改 |
| Output、checkpoint | `/storage/Internal_NAS/experiments/` | 每個 Slurm job 使用獨立目錄 |

AI-assisted training 只使用內部 MCP `http://192.168.51.48:8766/mcp`，
須有核准 VPN／內網 access；`8766` 是 MCP，`8765` 是 API，不可混用。
完整 Dashboard/API 的 VPN URL 由 Operator 提供給受信任使用者；AI client 不得將 raw API 設成 fallback action。

人類手動 curl 不是 AI fallback。已部署的 1.0.1 恢復舊 HTTP payload 與
Operator per-node default venv；詳見 [手動 HTTP 相容入口](manual-http-submission.md)。
MCP 的 username／venv 必填規則不變。Hank 已在 server6 用固定 Git source 加 NAS YAML
完成 LTX-2.5 五步短跑，詳見 [training 交接紀錄](mcp-training-handoff-2026-10-20.md)。
這不驗證手動 curl submission、歷史 default venv、所有 workers 或新帳號隔離；這些仍需分別驗收。

## 2. 第一次 onboarding

管理員提供下列資訊：

- 已確認的 `username`
- 可用 shared `venv` 名稱
- 可讀取的 Git repository
- 可讀取的 dataset/checkpoint path
- 允許的 GPU 數量、memory 與 node policy

Claude Code 的 machine-local MCP 設定：

```json
{
  "mcpServers": {
    "slurm-gpu-cluster": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://192.168.51.48:8766/mcp", "--allow-http"]
    }
  }
}
```

以上使用團隊核准的內部 MCP URL；只連線 client，不需安裝 MCP server。
個人設定與 credentials 不提交到 Git，公開發佈文件前另做去識別。
明文 HTTP 與 `--allow-http` 僅適用核准 VPN/private LAN；HTTPS profile 移除該旗標。
已部署的 1.0.1 可先呼叫 `get_onboarding_guide`，或讀取
`slurm://guides/onboarding` resource / `slurm_onboarding` prompt；三者內容相同且不提交 job。
只支援 tools 的 client 不需要 resources/prompts。
此 endpoint 只允許受信任的 private LAN。設定完成後先執行 read-only 驗證：

```text
請用 Slurm MCP 列出 cluster 狀態、GPU 狀態與可用 venv，不要提交 job。
```

預期使用 `cluster_info`、`gpu_status`、`list_venvs`，不應呼叫 raw HTTP API。1.0.1 已修正 nested GPU payload 的 formatting；若仍沒有 device rows，請 Operator 比對 backend telemetry，在確認實際 device occupancy 前不要提交 GPU job。

## 3. Training repository

提交前提供 username/program repo/ref/command、dataset（或明確「不需要」）、venv、
GPU/memory、output/checkpoint/cache 摘要，取得本次明確確認後才呼叫既有 `submit_job`。
Dataset/output 暫為 command 約定；backend 沒有這兩個結構化欄位或 worker path/GPU preflight。
指南確認不是 backend authorization；實際 jobs 以 shared `hank` 執行，username 僅供稽核。
沒有強制 dataset/venv 唯讀、sandbox 或跨使用者權限隔離；獨立 output 是使用規範。
Slurm IDLE 不代表無手動 GPU processes。Bubblewrap、強制 writable paths 與 preflight 另案實作。
狀態使用 `list_jobs`/`job_history`；目前沒有 `job_status`，queue 消失不能證明 terminal state。

建議專案結構：

```text
my-training/
├── README.md
├── requirements.lock
├── configs/
│   ├── smoke.yaml
│   └── train.yaml
├── tests/
│   ├── smoke_gpu.py
│   └── smoke_distributed.py
├── train.py
└── evaluate.py
```

Code、config 和 dependency lock 放 Git；dataset、model weights 與 output 不放 Git。提交前：

```bash
git add -A
git commit -m "Add training experiment"
git push origin HEAD
git rev-parse HEAD
```

把最後一行的 40 字元 commit SHA 當成 MCP `branch` 參數。不要提交未 push 的 branch 或未 commit 的 working tree；job 只會看到 remote 可取得的 commit。

## 4. Dataset 與 output

建議 NAS layout：

```text
/storage/Internal_NAS/datasets/<project>/<dataset>/<version>/
/storage/Internal_NAS/checkpoints/<project>/<model>/<version>/
/storage/Internal_NAS/experiments/<username>/<project>/<slurm-job-id>/
```

每個 dataset version 建議包含：

```text
dataset-v001/
├── manifest.json
├── SHA256SUMS
├── train/
└── validation/
```

`manifest.json` 至少記錄 dataset 名稱、版本、建立日期、來源、license、sample count 與 preprocessing version。Job 開始前由 test code 檢查必要檔案可讀；training 不應修改 dataset 或 base checkpoint。

Output 不要寫進 immutable source run directory。使用 Slurm job ID 建立獨立 output：

```bash
output=/storage/Internal_NAS/experiments/hank/my-training/$SLURM_JOB_ID && \
mkdir -p "$output" && \
python -u train.py \
  --config configs/train.yaml \
  --data /storage/Internal_NAS/datasets/my-training/images/v001 \
  --output "$output"
```

Platform log 另存於 `/storage/Internal_NAS/logs/<username>/<submission-id>/`，使用 `get_logs(job_id)` 查詢，不用 wildcard 猜檔名。

## 5. 建立 shared venv

目前 v1 的 engineer MCP 只有 `list_venvs`，沒有 `create_venv`。建立或更新 shared venv 是 Operator workflow，不應讓每位 engineer 直接修改共同環境。

建議命名包含 project、Python/CUDA compatibility 與版本，例如：

```text
my-training-py310-cu128-v001
```

Live API 雖有 `/venvs/create` schema，但目前 hardened systemd unit 沒有授權 service 寫入 venv root，因此它不是已支援的建立入口。Operator 在 controller 的受控 shell 建立空環境：

```bash
umask 0027
python3 -m venv /storage/Internal_NAS/venvs/my-training-py310-cu128-v001
```

接著依 repository 中的 exact lock 安裝並驗證：

```bash
venv=/storage/Internal_NAS/venvs/my-training-py310-cu128-v001
"$venv/bin/python" -m pip install -r requirements.lock
"$venv/bin/python" -m pip check
"$venv/bin/python" -m pip freeze > environment.freeze.txt
```

若 dependency 會編譯 CUDA extension，Operator 必須在相容的 approved node/build workflow 建立，再於所有允許的 GPU node 跑 smoke test。環境核准後不原地 upgrade；dependency 改變時建立 `v002`。

Operator 完成後，Engineer 用 MCP `list_venvs` 確認新名稱，再以該名稱提交。不得把 `/venvs/create` 設成 AI client tool；下一版應以獨立、可稽核的 environment builder 取代手動步驟。

## 6. 測試階梯

### 6.1 CPU-only tests

Lint、format 與不需要模型/GPU 的 unit tests 應在 repository CI 執行。v1 `submit_job` 目前要求 1-7 GPU，不適合用來跑純 CPU checks。

### 6.2 1-GPU smoke

先在 repository 放最小 GPU test：

```python
import json

import torch


assert torch.cuda.is_available()
assert torch.cuda.device_count() == 1
value = (torch.ones((1024, 1024), device="cuda") @ torch.ones((1024, 1024), device="cuda"))[0, 0]
torch.cuda.synchronize()
print(json.dumps({"device": torch.cuda.get_device_name(0), "result": value.item()}))
```

提交 prompt：

```text
我的 username 是 hank，venv 是 my-training-py310-cu128-v001。
請只透過 Slurm MCP submit_job，從 git@github.com:org/my-training.git
的 commit <full-commit-sha>，用 1 GPU、8G memory 執行
python -u tests/smoke_gpu.py；job name 是 my-training-smoke-1g。
先不要指定 node，讓 Slurm 排程。
```

### 6.3 2-GPU distributed smoke

`gpu=2` 只負責保留兩張 GPU，不會自動把單 GPU Python 程式變成 distributed training。Code 必須支援 DDP，command 也要使用 launcher：

```text
我的 username 是 hank，venv 是 my-training-py310-cu128-v001。
請從同一個完整 commit，用 2 GPU、16G memory 執行
torchrun --standalone --nproc_per_node=2 tests/smoke_distributed.py；
job name 是 my-training-smoke-2g，讓 Slurm 自動選 node。
```

Test 應驗證 `WORLD_SIZE=2`、每個 rank 的 CUDA device 不同，並完成一次 collective operation。

### 6.4 Training

1 GPU command：

```bash
output=/storage/Internal_NAS/experiments/hank/my-training/$SLURM_JOB_ID && \
mkdir -p "$output" && \
python -u train.py --config configs/train.yaml \
  --data /storage/Internal_NAS/datasets/my-training/images/v001 \
  --output "$output"
```

2 GPU command：

```bash
output=/storage/Internal_NAS/experiments/hank/my-training/$SLURM_JOB_ID && \
mkdir -p "$output" && \
torchrun --standalone --nproc_per_node=2 train.py \
  --config configs/train.yaml \
  --data /storage/Internal_NAS/datasets/my-training/images/v001 \
  --output "$output"
```

先通過 1-GPU smoke，再跑 2-GPU smoke，最後才送長時間 training。不要用正式 dataset 與完整 epoch 當第一個驗證 job。

## 7. GPU 數量與型號

目前 MCP 接受 `gpu=1..7`，但實際可否排程取決於 `cluster_info` 的 live state。
GPU 型號、數量與 occupancy 以 `gpu_status` 或 Operator 核對的 read-only telemetry 為準，
不要用文件內的靜態 inventory 決定排程。只有 node healthy 且 typed GRES 可可靠區分時才選型號。
`nodelist` 選的是 node，不是特定 GPU index，也不能在 mixed node 保證 GPU model。

一般 job 留空 `nodelist`，讓 Slurm 排程。只有測試硬體 compatibility 且 Owner/Operator 核准時才指定 node。v1 MCP 尚未提供 typed GPU constraint、multi-node parameters 或特定 GPU index；不要把 `gpu=4` 解讀成可以自動跨兩台 2-GPU node。

提交前必須同時確認 scheduler allocation 與實際 device occupancy。`cluster_info` 顯示 `idle` 只代表 Slurm queue 沒有 allocation；若 `gpu_status` 或 Operator 的 read-only telemetry 仍看到其他 process/大量 VRAM，停止提交，由 Operator 判斷是合法外部 workload、遺留 process，或應先 drain node。不得由 engineer 自行 kill process。

## 8. 追蹤與判定結果

成功 submission 必須回傳：

```json
{
  "success": true,
  "submission_id": "<uuid>",
  "job_id": "<slurm-job-id>",
  "source_commit": "<40-char-sha>",
  "status": "submitted"
}
```

後續操作：

```text
請列出 hank 的 pending/running jobs。
請顯示 job <job-id> 的 exact log。
請顯示最近的 job history 與 source commit。
```

- `list_jobs`：判斷 job 是否 PENDING/RUNNING。
- `get_logs`：讀取 metadata 綁定的 exact log。
- `job_history`：確認 submission ID 與 source commit。
- `cancel_job`：取消錯誤或不再需要的 active job。

目前 MCP 沒有獨立 `job_status` tool，history status 也不是 authoritative terminal state。正式驗收 terminal state 仍需 Operator 查 Slurm；這是下一版優先補強項目。

## 9. 建議的 landing 順序

### v1 現在就採用

1. Code/config/lock 全部由 Git commit SHA 識別。
2. Dataset 與 checkpoint 使用 NAS versioned path + manifest/checksum。
3. Venv 由 Operator 建立 immutable version；engineer 只選用。
4. 每個專案先有 1-GPU 與 2-GPU smoke，再提交 training。
5. Output 以 `$SLURM_JOB_ID` 分目錄，log 由 platform metadata 查詢。

### 下一個 platform change

1. 修正 MCP `gpu_status` nested payload formatting，並建立 Slurm allocation 與 device process reconciliation gate。
2. 新增 MCP `job_status` 並同步 terminal state 到 metadata。
3. 新增受控 environment build/approve workflow，取代手動 shared venv 安裝。
4. 新增 dataset registry、ACL、manifest 與 checksum validation。
5. 新增 task profile：CPU-only、GPU type/count、time limit、memory 與 single/multi-node policy。
6. 將 `submission_id` 注入 job environment，讓 experiment output 可直接與 submission metadata 關聯。
7. Slurm 完成 typed GRES 後才開放 A6000/4090/5090 型號選擇。

在 SSO/RBAC 與 per-user Slurm identity 完成前，所有 job 實際仍以 service identity `hank` 執行；本平台只適合受信任的內部工程師。
