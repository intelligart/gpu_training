# 連線設定（client only）

本文件是範本，不會自動修改你的設定。已經看得到 Slurm tools 的 client 不需要重設。
請選自己的 client；以下使用團隊核准的內部 MCP `http://192.168.51.48:8766/mcp`。
須有 VPN／內網 access；`8766` 是 MCP，`8765` 是 API，不可混用，不是公開服務。
不要把個人設定或 secrets 寫入 shared repository；不複製個人設定給其他人。

## VS Code／GitHub Copilot

使用 VS Code 的使用者層級 MCP 設定，或核准且不追蹤的 machine-local 設定。
若已有其他 server，合併這一個 entry，不覆蓋整份設定。

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

啟動／重新載入 server，在 tool picker 啟用 Slurm tools。
若 client 要求 trust/permission，第一次只使用讀取 tools；不要給通用 shell/SSH 管理權限。

## Claude Code

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

`.mcp.json` 只放 `type` 與 `url`，不要加 `"tools": [...]`，否則 Claude Code 會整個略過
該 server。工具限制改用 `.claude/settings.local.json` 的 permissions：只讀與監控工具放
`allow`；`submit_job`／`cancel_job` 不放 allow 也不放 deny，每次執行前由本人確認。
`username` 只是自填稽核標籤，一律填自己的；`cancel_job` 不檢查擁有者，只取消自己的 job。project-scope
server 第一次要在該目錄執行 `claude` 走信任／核准對話框，之後 `claude mcp list` 應顯示
`✔ Connected`；不要手改 `~/.claude.json` 去繞過核准。詳見
[三分鐘只讀快速開始](../mcp-quickstart.md#claude-code)。

若團隊政策要求既有 trusted VPN/private HTTP profile 的 local-scope bridge，可改用
`mcp-remote`（使用自己的 local 設定，不以 project-wide shared config 發布；需要
Node.js／npx，bridge 不是在使用者端安裝 Slurm server）：

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

`--allow-http` 僅用於 Operator 已核准的 private HTTP/VPN profile；HTTPS profile 移除它。
第一次 npx 可能需要 package download；公司政策不允許時找 Operator 提供核准方式，不改用 raw API。

## ChatGPT／其他 client

只有支援 remote MCP 且經管理員核准的 client 才能使用。
請新增管理員提供的 connector；不支援時停止，不提供 Custom Action/raw backend 替代路徑。
不同 client 的設定格式不同，不要直接貼 VS Code JSON。

## 連線驗收

可發現 `get_onboarding_guide`、`cluster_info`、`list_venvs`、`gpu_status`、`list_jobs`、`job_history`、
`get_logs`、`submit_job`、`cancel_job`。第一次只執行 P0 的只讀工具。
1.0.1 已部署 guide tool/resource/prompt；先呼叫 `get_onboarding_guide`。
支援可選入口的 client 也可讀 `slurm://guides/onboarding` 或取得 `slurm_onboarding`；
只支援 tools 的 client 不需要這兩種入口。三者是同一份內容，不會提交或取消 job。
若 guide 工具缺失，核對 Operator 指定的 endpoint／版本與 client 設定，停止提交並通知 Operator；
可先讀 [使用者包](README.md)，不要自行修 server 或重啟服務。

失敗時提供 client 名稱／版本、錯誤訊息與是否已接 VPN；遮掉 tokens／credentials。
工具不見、無法連線或 discovery 失敗時通知 Operator，不自行換 endpoint、改 firewall 或呼叫 raw API。