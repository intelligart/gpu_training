# Slurm MCP 工具參考

本頁描述目前 source 的九個 tools；不是新增 API，也不是即時 cluster readiness 報告。
[快速開始](mcp-quickstart.md) · [操作與版本指南](../MCP_GUIDE.md) · [回首頁](../README.md)

## 契約與回傳形式

- 權威實作：[mcp_server.py](../mcp_server.py)。參數表是 **MCP tool arguments**，不是 raw HTTP payload。
- 目前 tools 的 Python 回傳皆為 `str`：查詢通常是排版文字，submit/cancel 成功是 JSON
  序列化字串；client 外層另有 MCP content/envelope。不要假定所有 tools 有一致的 structured output。
- 有些失敗回傳 `Error: ...` 文字，有些 HTTP/telemetry 例外交由 SDK 處理；
  不能只看 transport 成功或 `isError=false` 就判定操作成功。
- 以下 JSON 均為**示意輸入／輸出**，不是新實測；含占位符的提交範例不可原樣送出。
- Username 是 audit label，不是認證。查詢 filter、job ID 或操作確認都不構成權限隔離。

| 分類 | 工具 | 副作用 |
|---|---|---|
| 指南 | [get_onboarding_guide](#get_onboarding_guide) | 只回傳內容，不連 backend |
| 查詢 | [cluster_info](#cluster_info)、[gpu_status](#gpu_status)、[list_venvs](#list_venvs) | 讀取 backend 狀態，不提交 job |
| 查詢 | [list_jobs](#list_jobs)、[job_history](#job_history)、[get_logs](#get_logs) | 讀取 queue／metadata／log |
| 提交 | [submit_job](#submit_job) | 準備 source、寫 artifacts/metadata、提交 Slurm job，可能耗用 GPU/RAM |
| 取消 | [cancel_job](#cancel_job) | 對指定 job 請求取消，可能中止訓練 |

## get_onboarding_guide

**參數：無。** Arguments：`{}`。

回傳完整 zh-TW Markdown 指南，含 `Guide version: 1.0.0`、必要資料、確認／追蹤範本及
pilot 限制。只讀共用內容，不查 host/backend、不寫 metadata、不提交或取消。
Guide version 是內容版本，不是平台 artifact 或 MCP SDK 版本。

## cluster_info

**參數：無。** Arguments：`{}`。

回傳 backend 提供的 Slurm 節點狀態文字；格式取決於 backend，不是固定的 JSON node schema。
Node healthy/IDLE 只反映 scheduler 觀察，不保證沒有 host 上手動 GPU processes。

## gpu_status

**參數：無。** Arguments：`{}`。

回傳各 node 的 state 與 device rows，包含可取得的 model、GPU index、顯存、utilization、
process 摘要；支援目前 MB 指標與 legacy GB 格式，單位會顯示在文字中。
Node error、缺 device telemetry 或格式錯誤不應被當作「GPU 空閒」。
這是狀態查詢，不是 worker preflight、實體 GPU 預約或選卡保證。

## list_venvs

**參數：無。** Arguments：`{}`。

回傳 shared NAS venv 的名稱與路徑，或 `No venvs found.`。
清單不是使用者的所有 conda/venv，也不是每個 worker 上 activate／interpreter／CUDA 的驗證。
Operator 核准的完整環境路徑不一定在此清單；先確認再使用，不原地 pip install。

## list_jobs

| 參數 | 型別 | 必填 | 預設 | 說明 |
|---|---|---|---|---|
| `username` | string | 否 | `""` | 非空時傳給 backend 的 Slurm user filter，空字串查全部 |

回傳 ID、Name、User、State、Time、Node、GPU 的文字表格，或 `No jobs in queue.`。
Pending/running queue 不是完整歷史；queue 消失不能證明成功、失敗或 exit code。
目前 shared Unix identity 與 audit username 不等價，此 filter 不能當作 audit label 或 ownership enforcement。

```json
{"username": ""}
```

## job_history

| 參數 | 型別 | 必填 | 預設 | 說明 |
|---|---|---|---|---|
| `limit` | integer | 否 | `20` | 要求回傳最近的 submission 紀錄數 |

回傳 job ID、submission ID、短版 source commit、name、user、metadata status、
requested nodelist 的文字表格，或 `No job history.`；不是分頁或 per-user 授權介面。
Status 是記錄中的值，不保證已同步 Slurm terminal state；Node 欄亦不保證是實際 allocation。
完整 source commit 應保存 submission 回應，不從短版顯示推斷。

```json
{"limit": 20}
```

## get_logs

| 參數 | 型別 | 必填 | 預設 | 說明 |
|---|---|---|---|---|
| `job_id` | string | 是 | 無 | Slurm job ID |

以 metadata 的 exact path 讀 log，回傳 log 文字，若有路徑則加上 `[Log file: ...]`。
不要用 wildcard 猜其他檔案。Log 尚未建立、讀不到或內容為空不等於 job 沒建立；
log 有 training 字樣也不證明 terminal success 或 checkpoint 品質。

```json
{"job_id": "<job-id>"}
```

## submit_job

先整理完整摘要，確認 username/venv、程式與資料、資源影響、獨立 output 和停止方式，
再取得本次明確確認。以下是互動指引，**不是 backend authorization gate**。

| 參數 | 型別 | 必填 | 預設 | 說明 |
|---|---|---|---|---|
| `command` | string | 是 | 無 | Training command；dataset/config/output 由這裡或 YAML 指定 |
| `username` | string | 是 | 無 | 已確認的 audit label，不變更執行 Unix identity |
| `venv` | string | 是 | 無 | 核准 shared 名稱或完整路徑，worker 必須可用 |
| `gpu` | integer | 否 | `1` | 請求 GPU 數量；backend 接受 1–7，實際依節點與政策 |
| `job_name` | string | 否 | `"job"` | 顯示名稱，不是唯一 job/submission ID |
| `nodelist` | string | 否 | `""` | 空字串由 Slurm 排程；指定節點需 Operator 核准 |
| `repo_url` | string | 否 | `""` | Git source URL；新實驗建議明確提供 |
| `branch` | string | 否 | `"main"` | Requested Git ref，建議已推送的完整 commit SHA |
| `mem` | string | 否 | `""` | Host RAM，例如 `32G`，不是 GPU VRAM；空值由 backend 決定 |

`gpu=2` 不會自動啟動 DDP，也不代表 multi-node。Nodelist 不是實體 GPU index。
沒有 `dataset`、`output`、`dry_run`、preflight 或 timeout 的獨立參數；
若需 command timeout，納入經核准的 command，不捏造 Slurm allocation TimeLimit。

```json
{
  "command": "<training-command-with-fresh-output>",
  "username": "<confirmed-username>",
  "venv": "<approved-venv>",
  "gpu": 1,
  "job_name": "<experiment-name>",
  "nodelist": "",
  "repo_url": "<repo-url>",
  "branch": "<pushed-full-commit-sha>",
  "mem": "32G"
}
```

成功時，工具字串內的 JSON 至少應含以下識別資料；其他 source／script／log 等欄位依回應保存：

```json
{
  "success": true,
  "submission_id": "<submission-id>",
  "job_id": "<job-id>",
  "status": "submitted"
}
```

使用 Git source 時核對完整 `source_commit`。`submitted` 只表示提交回應，
不表示模型開始、完成或品質驗證。Source 只包含可取得的 Git commit，不會自動帶入未提交檔案。
提交可能已建立 job，但 client timeout 或 metadata 寫入失敗；先核對，不直接 retry。

## cancel_job

| 參數 | 型別 | 必填 | 預設 | 說明 |
|---|---|---|---|---|
| `job_id` | string | 是 | 無 | 要取消的 Slurm job ID |

先只讀核對 job ID、submission/name 與使用者本次實驗，再取得明確取消確認。
回傳 backend cancellation result 的 JSON 字串；請求接受不等於已核對 terminal state。
取消後由 queue/log 與必要的 Operator Slurm 查證追蹤，不刪除 log/checkpoint、不 kill host process。

```json
{"job_id": "<confirmed-active-job-id>"}
```

## Resource 與 prompt

| 入口 | 識別名稱 | 參數 | 回傳與限制 |
|---|---|---|---|
| Resource | `slurm://guides/onboarding` | URI | 同一份 Markdown 指南，mime type `text/markdown` |
| Prompt | `slurm_onboarding` | 無 | 同一份指南，以 MCP prompt messages 呈現 |

兩者與 guide tool 內容相同、沒有提交副作用。只支援 tools 的 client 使用
`get_onboarding_guide` 即可，不需要為可選入口缺失而新增另一個 server。

## 錯誤處理：先判斷是否可能已提交

| 情況 | 可得結論 | 下一步 |
|---|---|---|
| 本地參數檢查回覆 username/venv required | Adapter 尚未呼叫 backend 提交 | 補齊已確認值，重新顯示摘要 |
| Source preparation／環境 policy 明確拒絕 | 此階段未成功提交 | 保存錯誤，找 Operator；修正後另確認 |
| `metadata_finalize_failed` 且帶 job ID | Slurm job 已建立，metadata 未完整寫入 | 保存真實 ID／recovery path，交 Operator 查證，不重送 |
| HTTP timeout／服務錯誤／`incomplete success response` | 結果可能不確定，不能保證沒有 job | 核對 history／已知 ID／exact log，必要時找 Operator，不盲目 retry |
| Queue 空或 history 仍為 submitted | Terminal state 未知 | Operator 核對 Slurm；目前沒有獨立 `job_status` tool |
| Cancel request accepted | 取消請求回應，不是最終狀態證明 | 繼續核對正確 job，不自動取消其他工作 |

Human curl 相容入口見 [手動 HTTP 說明](manual-http-submission.md)，不是 AI fallback。
AI training/model 執行仍只經 MCP；MCP 失敗時停止，不改成本機、notebook 或 raw HTTP。
