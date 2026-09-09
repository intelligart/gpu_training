# Data Scientist 使用手冊 — GPU 叢集訓練平台

## 總覽

透過 Slurm Dashboard 提交 GPU 訓練任務，不需要 SSH、不需要懂 Slurm。

你只需要：
1. 程式碼放 GitHub
2. 資料放 Internal NAS
3. 到 Dashboard 網頁或用 curl 提交

**Dashboard 網址：http://ia-ai-server-5:8765**

---

## 平台架構

```
Internal NAS (read-only, 所有節點共用)
├── venvs/                ← 共用 Python 環境
│   ├── ltx2/
│   ├── comfyui/
│   └── ...
├── <你的資料夾>/          ← 訓練資料（路徑自由）
└── Checkpoints/           ← 共用模型權重

Local SSD (writable, 每台各自獨立)
└── slurmjob/<username>/   ← 自動 clone 你的 repo，訓練輸出也在這
```

**規則：**
- **讀取**：資料和 venv 都在 Internal NAS 上，所有節點都看得到
- **寫入**：輸出自動寫到該節點的 local SSD
- **程式碼**：從 GitHub 自動 clone 到 local SSD

---

## 方式一：跑你自己的訓練程式（通用）

適合有自己的 training script 的 data scientist。

### Step 1：準備

1. **程式碼**放 GitHub repo（任何 Python 訓練腳本）
2. **資料**放 Internal NAS（路徑自由，例如 `/storage/Internal_NAS/ryan/my_dataset/`）
3. **Venv**：用共用的或請 admin 在 `/storage/Internal_NAS/venvs/` 建一個

### Step 2：確認 GPU 可用

打開 Dashboard（http://ia-ai-server-5:8765），看 **GPU Status** 表格：

| Node | GPU | Model | VRAM Usage | Utilization | Processes |
|------|-----|-------|-----------|-------------|-----------|
| ia-ai-server-4 | GPU 0 | RTX A6000 | 0.7 / 48 GB | 0% | — |
| AI-Server-6 | GPU 0 | RTX 5090 | 0.0 / 32 GB | 0% | — |

找一台有空閒 VRAM 的 GPU。

### Step 3：提交

#### 透過 Dashboard 網頁

在 Submit Job 表單填：

| 欄位 | 填什麼 | 範例 |
|------|--------|------|
| **Command** | 你的訓練指令 | `python train.py --data /storage/Internal_NAS/ryan/my_dataset --lr 1e-4` |
| **Username** | 你的名字 | `ryan` |
| **Job Name** | 任意名稱 | `my-experiment` |
| **GPU Count** | 需要幾張 GPU | `1` |
| **Node** | 有空 GPU 的機器（可留空自動分配） | `ia-ai-server-4` |
| **Repo URL** | 你的 GitHub repo | `git@github.com:ryan/my-project.git` |
| **Venv** | 使用的 Python 環境 | `ltx2` |

按 **Submit Job**。

#### 透過 curl

```bash
curl -X POST http://ia-ai-server-5:8765/submit \
  -H "Content-Type: application/json" \
  -d '{
    "command": "python train.py --data /storage/Internal_NAS/ryan/my_dataset --lr 1e-4 --epochs 50",
    "username": "ryan",
    "gpu": 1,
    "job_name": "my-experiment",
    "repo_url": "git@github.com:ryan/my-project.git",
    "venv": "ltx2"
  }'
```

### Step 4：監控

- **Dashboard**：Job Queue 看狀態（RUNNING / PENDING），點 **log** 看即時輸出
- **curl**：`curl http://ia-ai-server-5:8765/logs/<JOB_ID>`
- **CLI**：`squeue`

### Step 5：取得結果

結果在執行該任務的節點上：

```
/storage/SSD2/slurmjob/<username>/
    你的 repo 內容
    以及你的程式產生的所有輸出
```

具體是哪台機器，看 Dashboard Job Queue 的 Node 欄位，或 log 裡的 hostname。

---

## 方式二：LTX-2 LoRA 訓練（現成範例）

不需要自己寫 training script，只需要準備影片資料集。

### Step 1：準備資料集

放到 NAS 上你的資料夾：

```
/storage/Internal_NAS/slurm_workspace/<你的名字>/datasets/<資料集名稱>/
    dataset.json
    videos/
        clip1.mp4
        clip2.mp4
        clip3.mp4
```

`dataset.json` 格式 — 每個影片配一句英文描述：

```json
[
    {"caption": "A cat playing with a ball of yarn", "media_path": "videos/clip1.mp4"},
    {"caption": "A cat sleeping on a sofa", "media_path": "videos/cat_sleeping.mp4"},
    {"caption": "A cat eating from a bowl", "media_path": "videos/cat_eating.mp4"}
]
```

**注意：**
- 影片建議 3-10 秒
- `caption` 用英文效果最好
- 建議至少 20 個以上的影片
- LTX-2 需要約 40GB VRAM，只有 RTX A6000 (48GB) 能跑

### Step 2：提交

#### Dashboard

| 欄位 | 填什麼 |
|------|--------|
| **Command** | `python train_lora.py alice cats` |
| **Username** | `alice` |
| **Job Name** | `cats-lora` |
| **GPU** | `1` |
| **Node** | 有空 A6000 的機器 |
| **Repo URL** | `git@github.com:hank-intelligarts/ltx2-training-demo.git` |
| **Venv** | `ltx2` |

#### curl

```bash
curl -X POST http://ia-ai-server-5:8765/submit \
  -H "Content-Type: application/json" \
  -d '{
    "command": "python train_lora.py alice cats --steps 1000",
    "username": "alice",
    "gpu": 1,
    "job_name": "cats-lora",
    "repo_url": "git@github.com:hank-intelligarts/ltx2-training-demo.git",
    "branch": "master",
    "venv": "ltx2"
  }'
```

### 進階參數

```
python train_lora.py <username> <dataset> [options]
```

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `--steps` | 1000 | 訓練步數（1000 步約 30 分鐘） |
| `--rank` | 16 | LoRA rank，越高表達力越強 |
| `--resolution` | 512x320x25 | 寬x高x幀數，影響 VRAM 用量 |

### 結果

log 最後會印出路徑：

```
============================================================
  DONE!
  Node:         ia-ai-server-4
  LoRA weights: /storage/SSD2/training_scratch/alice/cats/runs/20260907_150000/checkpoints/
  Validation:   /storage/SSD2/training_scratch/alice/cats/runs/20260907_150000/samples/
============================================================
```

把 `checkpoints/` 裡的 `.safetensors` 檔案載入 ComfyUI 或推論腳本即可。

---

## 常見問題

### Q: 我的任務一直 PENDING？
Dashboard 的 GPU Status 看看是不是所有 GPU 都被佔了。等其他人完成或換一台。

### Q: 出現 OOM (Out of Memory)？
你的模型太大或解析度太高。換一張 VRAM 更大的 GPU，或降低 batch size / 解析度。

### Q: 第一次跑很慢？
第一次需要 git clone repo 和安裝套件。之後同一台再跑就會很快（已快取）。

### Q: 結果在哪台機器上？
看 Dashboard Job Queue 的 Node 欄位，或 log 輸出。結果在那台機器的 `/storage/SSD2/slurmjob/<username>/` 下。

### Q: 需要特殊 Python 套件怎麼辦？
請 admin 在 `/storage/Internal_NAS/venvs/` 建一個新的 venv，或者在你的 training script 開頭加 `pip install`。

### Q: 我的資料一定要放 Internal NAS 嗎？
是的。Internal NAS 是所有節點都能讀取的共用儲存空間。你不知道 Slurm 會把任務分到哪台，所以資料必須放在每台都看得到的地方。

---

## 可用的共用 Venvs

| 名稱 | 路徑 | 用途 |
|------|------|------|
| `ltx2` | `/storage/Internal_NAS/venvs/ltx2/` | LTX-2 影片模型訓練 |
| `comfyui` | `/storage/Internal_NAS/venvs/comfyui/` | ComfyUI 相關 |

在 Dashboard 的 Venv 下拉選單可以直接選。

## 可用的計算資源

| 機器 | GPU | VRAM | 適合的任務 |
|------|-----|------|-----------|
| ia-ai-server-4 | 2x RTX A6000 | 48GB each | 大模型訓練 ✅ |
| ia-ai-server-5 | 2x RTX A6000 | 48GB each | 大模型訓練 ✅ |
| AI-Server-6 | 4x RTX 5090 | 32GB each | 中小模型訓練 |
