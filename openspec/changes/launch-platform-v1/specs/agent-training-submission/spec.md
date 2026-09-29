## Purpose

確保 Claude、ChatGPT 與後續註冊的 AI agent 以一致、可稽核且受 Slurm 資源限制的 MCP 工具提交 training，避免在控制主機直接執行訓練程式。

## ADDED Requirements

### Requirement: AI training 一律透過 Slurm MCP 提交
所有註冊的 AI agent integration SHALL 僅使用 Slurm MCP training tool 提交 training、模型執行或 Python training script。Agent MUST NOT 在本機 shell、IDE terminal、notebook runtime 或 raw HTTP submission endpoint 直接啟動該工作負載。

#### Scenario: 使用者要求執行 training
- **WHEN** 使用者透過 Claude、ChatGPT 或其他已註冊 agent 要求 training、模型執行或 Python training script
- **THEN** agent 呼叫 Slurm MCP submission tool
- **AND** 工作負載由 Slurm 配置資源後執行

#### Scenario: MCP 無法使用
- **WHEN** agent 無法連線至 Slurm MCP 或 MCP 回報 submission 失敗
- **THEN** agent 清楚回報失敗且不在本機降級執行工作負載

### Requirement: 提交前取得必要身分與環境
MCP submission tool SHALL 要求非空白的 `username` 與 `venv`，並 SHALL 在缺少其中任一值時拒絕提交。Agent MAY 沿用同一對話中已由使用者確認的值，但 MUST NOT 自行推測其他使用者身分或環境。

#### Scenario: 缺少 username 或 venv
- **WHEN** training request 未提供且對話中未確認 `username` 或 `venv`
- **THEN** agent 在呼叫 submission tool 前向使用者取得缺少的值
- **AND** 系統未建立 Slurm job

#### Scenario: 必要參數已確認
- **WHEN** `username`、`venv`、command 與資源需求通過 validation
- **THEN** MCP 將結構化 submission 傳送至內部 Slurm adapter

### Requirement: Agent 不直接依賴 backend submission API
Raw submission API SHALL 被視為 MCP 與受信任內部 UI 的 implementation boundary，而不是 AI agent 的公開工具介面。Claude、ChatGPT 及其他 agent configuration MUST 僅註冊 MCP endpoint，不得同時註冊 raw submission endpoint。

#### Scenario: 設定新的 AI client
- **WHEN** 管理員為 AI client 建立 training integration
- **THEN** client configuration 只包含核准的 MCP endpoint 與 tools
- **AND** raw backend URL 不被宣告為可直接提交 training 的 agent action

### Requirement: 提交結果可追蹤
成功的 MCP submission SHALL 回傳穩定的 submission identifier 與 Slurm job identifier；失敗回應 SHALL 不得宣稱 job 已建立。

#### Scenario: Slurm 接受 submission
- **WHEN** backend 成功取得 Slurm job ID
- **THEN** MCP 回應包含 submission ID、job ID 與初始狀態

#### Scenario: Slurm 拒絕 submission
- **WHEN** validation、source preparation 或 `sbatch` 失敗
- **THEN** MCP 回應包含可理解的錯誤
- **AND** 不回傳成功狀態或虛構 job ID