# Slurm MCP：三分鐘只讀快速開始

讓 AI client 連上叢集、取得指南並查詢環境。**本頁不會提交 training job**；
三分鐘以你已取得 VPN／網路 access 與 Operator 設定為前提，不包含開通帳號或準備 training 環境。
要跑自己的 training，另看本頁的 [程式、venv 與資料位置](#4-training-程式venv-與資料要放哪裡)。

[回首頁](../README.md) · [MCP 指南](../MCP_GUIDE.md) · [完整工具參考](mcp-tool-reference.md)

## 1. 向 Operator 取得設定

- 確認可透過 VPN/private-LAN 存取 `http://192.168.51.48:8766/mcp`。
- 已確認的 `username` audit label、核准 `venv` 名稱或路徑。
- 資源政策、dataset/output 可用位置與 Operator 聯絡方式。

不從登入名稱或路徑猜 username/venv。Username 不是認證；目前是 shared execution pilot，
沒有跨使用者權限隔離。Tokens、credentials 與個人設定只保留在本機，不提交到 Git。
本文記錄團隊核准的內部 URL，不是公開服務；`8766` 是 MCP，`8765` 是 API，不可混用。
你只需要支援 MCP 的 client，**不需要安裝 Slurm 或另一個 MCP server**。

## 2. 設定自己的 client

選一種方式；以下已填入內部 MCP URL。已有其他 servers 時合併 entry，
不要覆蓋整份設定。只讀工具直接允許；`submit_job`／`cancel_job` 可用，但每次執行前由本人確認。

### VS Code／GitHub Copilot

放入使用者層級或核准且未追蹤的 machine-local MCP 設定：

```json
{
  "servers": {
    "slurmGpuCluster": {
      "type": "http",
      "url": "http://192.168.51.48:8766/mcp"
    }
  }
}
```

### Claude Code

Claude Code 原生支援 remote HTTP MCP，不需要 Node.js／npx。在工作目錄建立
`.mcp.json`（或用 `claude mcp add -s project --transport http slurm-gpu-cluster http://192.168.51.48:8766/mcp`）：

```json
{
  "mcpServers": {
    "slurm-gpu-cluster": {
      "type": "http",
      "url": "http://192.168.51.48:8766/mcp"
    }
  }
}
```

> ⚠️ `.mcp.json` 只放 `type` 與 `url`。不要加入 `"tools": ["cluster_info", ...]`
> 之類的其他 client 欄位：Claude Code 會**整個略過**這個 server，只在
> `claude mcp list` 的 diagnostics 顯示警告。工具限制改用下方的 permissions。

**設定工具權限。** Server 提供 9 個工具，其中 `submit_job`、`cancel_job` 會變更叢集狀態。
在同一目錄建立未追蹤的 `.claude/settings.local.json`，只讀與監控工具直接允許：

```json
{
  "enabledMcpjsonServers": ["slurm-gpu-cluster"],
  "permissions": {
    "allow": [
      "mcp__slurm-gpu-cluster__get_onboarding_guide",
      "mcp__slurm-gpu-cluster__cluster_info",
      "mcp__slurm-gpu-cluster__list_venvs",
      "mcp__slurm-gpu-cluster__gpu_status",
      "mcp__slurm-gpu-cluster__list_jobs",
      "mcp__slurm-gpu-cluster__get_logs",
      "mcp__slurm-gpu-cluster__job_history"
    ]
  }
}
```

`submit_job` 與 `cancel_job` **刻意不放進 `allow`，也不放進 `deny`**：預設就能送 job，
但每次呼叫時 Claude Code 會跳出確認，由你看過參數再按允許。不要把這兩個加進 `allow`，
否則 AI 會不經確認直接送出或取消 job。
工具名稱格式是 `mcp__<server 名稱>__<tool>`；若 `.mcp.json` 用了別的 server 名稱，這裡要一起改。

> ⚠️ **`username` 只是自填的稽核標籤，沒有驗證。** 所有 job 在 Slurm 與 OS 層實際都以
> 同一個共用帳號執行；`job_history` 的 `User` 欄與工作目錄
> `/storage/SSD2/slurmjob/<username>/` 是靠 `submit_job` 的 `username` 參數區分的。
> 一律填 Operator 確認過的**你自己的** username，不要沿用別人的或共用帳號名稱。
> `cancel_job` 只憑 `job_id`、不檢查擁有者：只取消自己的 job，取消前先用
> `list_jobs`／`job_history` 確認該 job 的 `User` 是你。

**第一次啟動要信任 workspace。** 在該目錄執行互動式 `claude`，接受 trust 對話框；
若詢問是否啟用 `.mcp.json` 的 server，選擇核准。未信任前 `settings.local.json`
的 allow 規則會被忽略，`claude mcp list` 會顯示 `⏸ Pending approval`。
完成後用 `claude mcp list` 確認 `slurm-gpu-cluster` 為 `✔ Connected`。
核准是每台機器各做一次的互動步驟；請執行 `claude` 走對話框，不要手改
`~/.claude.json` 等內部設定檔去繞過它（格式未保證，且會略過該有的信任確認）。

**替代：mcp-remote bridge。** 若團隊政策要求走 local bridge profile，可改用下列 entry
（需要 Node.js／npx，首次會下載 package，須符合公司政策；它不是在 client 安裝 Slurm server）：

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

`--allow-http` 只用於核准的 private HTTP profile；HTTPS profile 移除它。
其他 client 必須支援且獲准連線 remote MCP，不能直接套用不同 client 的 JSON。

## 3. 貼上第一個只讀請求

完成設定、啟動 client 的 MCP 連線後，填妥占位符並貼給 AI。
這四個只讀工具不需要 username／venv；Operator 尚未提供時，把該行改成
「username 與 venv 尚未由 Operator 確認，不要猜」即可先完成連線驗證。
之後送 job 時，`username` 必須是你自己的（見第 2 節的稽核說明）。

```text
請使用 Operator 核准的 Slurm MCP。
我的 username 是 <username>，核准的 venv 是 <venv>。
先呼叫 get_onboarding_guide，再呼叫 cluster_info、list_venvs、gpu_status。
回報工具是否可用、必要工作資料及 GPU telemetry 是否完整。
這次只做只讀查詢：不要提交、取消 job、安裝套件或執行 Python/model。
不要從 Slurm IDLE 或空 queue 推斷 GPU 空閒，不替我猜 username 或 venv。
缺工具、連線失敗、GPU 資訊不完整或有其他 workload 時停止並通知 Operator。
不得改用本機 training 或 raw HTTP fallback。
```

### 你應該看到什麼？

| 呼叫 | 預期結果 | 不代表什麼 |
|---|---|---|
| `get_onboarding_guide` | 指南版本與必要資料 checklist | 沒有建立 job，也不是認證流程 |
| `cluster_info` | 節點與 scheduler 狀態文字 | IDLE 不保證無手動 GPU workloads |
| `list_venvs` | Shared venv 名稱與路徑 | 不保證指定 worker 可用或 CUDA 相容 |
| `gpu_status` | Device rows、顯存、使用率及可取得的 processes | 不是資源預約或自動 preflight |

這是預期輸出類型，不是本次連線已通過的測試結果。
只支援 tools 的 client 不需要 resource/prompt；支援者可另讀
`slurm://guides/onboarding` 或取得 `slurm_onboarding`，內容與 guide 相同。

## 何時先停止？

- 工具不見：請 Operator 核對 endpoint／版本及 client 啟用的工具，不自行重啟 server。
- 連線失敗：核對 VPN/private route，提供已遮罩的錯誤，不改 firewall 或 endpoint。
- GPU 缺資料／有其他 processes：記錄「連線可用、GPU readiness 待確認」，不送 job。
- Venv 未列出：交 Operator 確認；清單不是所有個人環境的目錄，不自行安裝或猜路徑。

## 4. Training 程式、venv 與資料要放哪裡？

以下是連線之後的準備工作，**不包含在三分鐘連線目標內，也不會自動建立環境或提交 job**。

| 內容 | 放置位置 | 誰準備／注意事項 |
|---|---|---|
| 程式、一般 config、dependency lock | 叢集可讀取的 Git repository | 使用者先 commit／push，提供 `repo_url` 和已推送的完整 commit SHA |
| Training venv | `/storage/Internal_NAS/venvs/<環境名稱>/` | Operator 建立、版本化並核准；MCP 用 `list_venvs` 查詢 |
| Dataset | `/storage/Internal_NAS/datasets/<project>/<dataset>/<version>/` | 使用者與 Operator 確認 worker 可讀、版本與所需容量 |
| Base model weights／輸入 checkpoint | `/storage/Internal_NAS/checkpoints/<project>/<model>/<version>/` | 不放 Git，不在 job 中修改共享輸入 |
| Output、產生的 checkpoint／cache | `/storage/Internal_NAS/experiments/<username>/<project>/<run-id>/` | 每次實驗使用新的獨立目錄，並在 command/config 明確指定 |

以上 NAS 子目錄是建議規劃，**不是已建立或已授權可寫的保證**；
由 Operator 確認掛載、權限與空間。Username 仍是 audit label，分目錄不等於安全隔離。

### 程式不用先手動複製到 NAS

標準方式是開發自己的 Git 專案，commit／push 後由平台準備該 commit 的
submission 專屬 source；平台不會帶入筆電上的未提交修改，也不需要另複製 NAS runner。
一般 config 與 dependency lock 跟程式一起版本化，dataset、weights、venv 與 output 不放 Git。
Private repo 必須由 Operator 確認平台 Git access，不要把 access token 寫進 URL。

例如 Git 專案可以包含：

```text
my-training/
  train.py
  configs/smoke.yaml
  requirements.lock
```

若採用先前 LTX 成功案例的 **Git 程式＋NAS YAML**，也可以直接用 NAS config；
但該 YAML 不在 source commit 裡，須另外記錄其版本／內容或 checksum，
並確認 dataset、venv 和新的 output 路徑，不直接重用歷史 output。

### Venv 必須在 worker 可用，不能只放筆電

標準共用環境位於上述 NAS venv root；提交的 `venv` 可用核准的名稱或完整路徑。
不要直接把筆電的 venv 整包搬過去：Python interpreter、套件、CUDA 與目標 worker
必須相容。即使 NAS 可見，venv 內的 interpreter／symlink 也未必在每台 worker 可用。

目前 MCP **沒有 `create_venv` 工具**；缺環境時把 Python 版本、dependency lock
及 GPU/CUDA 需求交給 Operator，不自行在共享 venv 原地安裝／升級套件。
`list_venvs` 列得出來不代表 worker 驗證通過；其他完整路徑也須 Operator 另行核准。
詳細建立責任與驗證見 [工程師指南](user-guide.md#5-建立-shared-venv)。

## 下一步：把提交資料交給 AI，先不要執行

至少提供下列資料；以下是摘要範本，**不是可直接執行的 command 或提交授權**：

```text
請只使用 Slurm MCP；目前先整理摘要，不要提交、安裝套件或執行程式。
username=<已確認值>
repo_url=<平台可讀取的 Git URL，不含 credentials>
branch=<已推送的完整 commit SHA>
command=<entrypoint、config 與必要參數>
venv=<Operator 核准的名稱或完整路徑>
dataset/base checkpoint=<NAS 版本路徑，或明確不需要>
output/checkpoint/cache=<本次新的獨立 NAS 路徑>
gpu=<核准數量>，mem=<host RAM>，job_name=<實驗名稱>
成功條件=<預期 steps、log 或產物>，停止條件=<何時停止並回報>
先列出缺少資料及待 Operator 核對的 worker／環境／GPU occupancy。
等核對完成且我另行明確確認，才提交一次。
```

使用 [training 遷移資料卡](training-user-pack/migration-card.md) 整理 repo/full commit、
command、dataset/config、venv、GPU/host RAM、獨立 output 與成功／停止條件。
Dataset/output 是 command/config 的內容，不是額外的 MCP tool 參數；
不需要指定 node 時留給 Slurm 排程，`nodelist` 只有 Operator 核准時才指定。
Operator 核對 worker 路徑、環境與實際 occupancy，顯示摘要並取得本次明確確認後，
才呼叫 [submit_job](mcp-tool-reference.md#submit_job) 一次。不要覆寫舊 output。

已成功的 LTX-2.5 五步案例見 [job 545 交接紀錄](mcp-training-handoff-2026-10-20.md)；
其歷史 output 已存在，不可直接重送。MCP 不可用時停止，不走 local/raw fallback。
