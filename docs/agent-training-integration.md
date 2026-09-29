# AI Training Integration Contract

Claude、GitHub Copilot、ChatGPT 與後續 AI client 共用同一個 training contract：

```text
AI client -> approved remote MCP endpoint -> internal adapter -> Slurm
```

## Client 設定

1. 僅註冊管理員提供的 remote MCP endpoint。
2. 只啟用核准的 Slurm training tools；提交使用 `submit_job`。
3. 不把 internal adapter、Dashboard endpoint、SSH 或 terminal 設成 training action。
4. Endpoint、token 與憑證放在 client 的 secret store 或 machine-local 設定，不提交
   進 repository。
5. Client 不支援 remote MCP 時，該 client 暫不支援 training；不得建立 raw API
   fallback。

## Submission 行為

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