## Purpose

定義 GPU training 第一版只能在通過離線測試、設定檢查與明確核准後部署至內網，並保留不破壞 Slurm 工作與歷史資料的回滾路徑。

## ADDED Requirements

### Requirement: 部署前 gate 可離線重跑
系統 SHALL 提供一組可重跑的 preflight command，驗證 Python syntax、單元測試、OpenSpec artifacts、machine-local 設定忽略規則及 deployment configuration。Preflight MUST NOT 提交 job、修改 live Slurm configuration 或重啟 service。

#### Scenario: Preflight 全部通過
- **WHEN** operator 在 deployment artifact 上執行文件指定的 preflight command
- **THEN** 每個 gate 回報成功且 command 以零狀態結束

#### Scenario: 任一 gate 失敗
- **WHEN** syntax、test、spec 或 configuration check 任一失敗
- **THEN** rollout 停止且 live services 維持不變

### Requirement: Live rollout 需要明確授權
任何 service restart、endpoint 切換或 Slurm canary submission MUST 在執行前列出目標 node、預期影響、驗證方式與 rollback command，並取得 owner 明確核准。

#### Scenario: 未取得 owner 核准
- **WHEN** artifacts 已通過 preflight 但尚未取得 live rollout 核准
- **THEN** workflow 不執行 restart、endpoint 切換或 canary job

### Requirement: 第一版僅提供內部服務
v1 endpoint SHALL 僅能由核准的內部網路、VPN 或 gateway 存取，且 MUST NOT 直接部署為公開網際網路服務。

#### Scenario: 準備 deployment configuration
- **WHEN** operator 產生 v1 service 或 reverse proxy configuration
- **THEN** configuration 不建立未受控的 public listener
- **AND** 文件列出實際 network boundary

### Requirement: Rollback 保留工作與歷史資料
Rollout SHALL 在切換前保存上一版可啟動 artifact 與必要設定。Rollback MUST NOT 清除 Slurm spool、取消既有 job 或刪除 submission history。

#### Scenario: 新版本 health check 失敗
- **WHEN** service 切換後 MCP discovery、read-only cluster query 或 submission adapter health check 失敗
- **THEN** operator 可依文件恢復上一版 service artifact 與設定
- **AND** 已存在的 Slurm job 與 submission history 保持不變

### Requirement: Canary 驗收經 MCP 路徑執行
取得 live rollout 核准後，v1 SHALL 以專用的低風險 training fixture 經 MCP submission tool 執行 canary，並驗證 submission ID、job ID、source commit、log 關聯與 terminal state。

#### Scenario: Canary 完成
- **WHEN** 核准的 canary job 經 MCP 成功提交並到達 terminal state
- **THEN** acceptance record 包含 request、submission ID、job ID、resolved commit、log path 與結果