# AI Training Integration Contract

Claude、GitHub Copilot、ChatGPT 與後續 AI client 共用同一個 training contract：

```text
AI client -> approved remote MCP endpoint -> internal adapter -> Slurm
```

這是 **AI client** 的 contract，不是禁止人類使用 curl。受信任的手動 HTTP 入口
另見 [手動 HTTP 相容說明](manual-http-submission.md)；已部署的 1.0.1 手動
相容修正不解除 AI MCP-only／明確 username 與 venv／不得 fallback 的規則。

## Client 設定

1. 僅註冊管理員提供的 remote MCP endpoint。
2. 只啟用核准的 Slurm training tools；提交使用 `submit_job`。
3. 不把 internal adapter、Dashboard endpoint、SSH 或 terminal 設成 training action。
4. Endpoint、token 與憑證放在 client 的 secret store 或 machine-local 設定，不提交
   進 repository。
5. Client 不支援 remote MCP 時，該 client 暫不支援 training；不得建立 raw API
   fallback。

## Submission 行為

- Onboarding 1.0.1 已部署。新 server 首次使用先呼叫 `get_onboarding_guide`；
   支援 resources/prompts 的 client 可讀 `slurm://guides/onboarding` 或取得 `slurm_onboarding`。
   三種入口都是只讀且使用同一份內容；tools-only client 不依賴可選入口。
- Client 只連 Operator 提供的 `<MCP_ENDPOINT>`，不需要安裝 MCP server。
- 先用 `cluster_info`、`list_venvs` 做 discovery，補齊 program repo/ref/command、dataset
   路徑或明確不需要、GPU/memory 與 output 約定；整理摘要，取得本次明確確認才提交。
   確認是 client guidance，不是 backend authorization gate。
- Dataset/output 目前只在 command 中指定；未提供 worker path/GPU preflight、sandbox、
   強制唯讀或跨使用者隔離。所有 jobs 以 shared `hank` 執行，username 是 audit label。
   手動 GPU workloads 與缺失 telemetry 交 Operator 核對；Bubblewrap/強制保護另案處理。
- 追蹤使用 `list_jobs`、`job_history`、`get_logs` exact log；目前沒有 `job_status`，
   資訊不足不推斷 terminal state。先查 job ID/name，再取得明確確認才 `cancel_job`。

- 每次 training 都需要使用者已確認的 `username` 與 `venv`。
- Agent 可以沿用同一對話中已確認的值，但不得由路徑、登入名稱或其他使用者推測。
- MCP 無法使用或回報錯誤時，agent 清楚回報且停止，不在本機、notebook 或 IDE
  terminal 執行 training。
- 成功回應必須包含 `submission_id`、Slurm `job_id` 與初始 `status`；缺少任一值
   視為失敗。

## Client-specific Notes

### Claude

使用 machine-local Claude MCP 設定連至 approved endpoint。Repository 只保存本文件
與行為規則，不保存 endpoint 或 secret。

### GitHub Copilot

使用 VS Code machine-local MCP 設定。Workspace instructions 強制 training 只使用 MCP
tool；MCP tool permission 可按 session 或 workspace 核准。

### ChatGPT

只在支援 remote MCP 的受管理 workspace 中新增 approved MCP connector。若目前方案或
workspace 不支援 MCP，保持 training integration 關閉，不以 Custom Action/raw API
取代。

## 驗收

- 缺少 `username` 或 `venv` 時沒有建立 Slurm job。
- MCP 斷線時沒有本機程序或 raw adapter request。
- Client 設定只出現 MCP endpoint。
- 成功提交可由 submission ID、job ID、初始 status 與 audit source 追蹤。