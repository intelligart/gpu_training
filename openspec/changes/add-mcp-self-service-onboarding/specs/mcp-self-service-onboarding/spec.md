## Purpose

讓受信任 GPU 平台使用者在連接 MCP 後取得一致的首次使用說明，了解程式、資料集與環境準備、現有提交參數及追蹤方式，並明確區分操作指引與尚未實作的執行隔離能力。

## ADDED Requirements

### Requirement: Discoverable read-only onboarding
MCP SHALL 提供可由 tool 讀取的 onboarding 指南及同內容的 resource/prompt，取得指南 MUST NOT 提交或取消 job、寫入 metadata 或修改 cluster。

#### Scenario: Tool-only client
- **WHEN** client 只支援 MCP tools 並要求首次使用說明
- **THEN** 可取得完整指南，不依賴 resource/prompt 支援且不建立 job

#### Scenario: Consistent optional presentations
- **WHEN** client 讀取 onboarding resource 或取得 onboarding prompt
- **THEN** 必要資料、流程與限制與 guide tool 一致，操作只產生說明內容

### Requirement: Guided submission checklist
指南 SHALL 引導使用者確認 username、程式來源/ref/command、dataset 路徑或明確不需要、venv、GPU/memory 與 output 約定，先做只讀 discovery、顯示摘要並要求明確確認才引導現有 submission；MUST NOT 猜測使用者資料或宣稱已驗證所有 workers。

#### Scenario: Missing user input
- **WHEN** user 未提供 username、venv 或必要的工作資料
- **THEN** 範本引導補齊資料或查詢可用 venv，不指示 agent 自行猜測並提交

#### Scenario: First successful submission workflow
- **WHEN** user 提供完整工作資料並確認提交
- **THEN** 指南使用既有 MCP submission contract，要求回報 submission ID、job ID、status 與固定 source commit

### Requirement: Safe tracking and failure guidance
指南 SHALL 包含 queue/history/exact logs 與明確確認後取消的範本，並在 MCP failure 或資訊不足時要求停止與回報；MUST NOT 建議 local execution、raw API fallback 或假造 terminal state。

#### Scenario: Unavailable MCP
- **WHEN** client 無法連上 submission service
- **THEN** 指南要求停止並通知 Operator，不提供本機或 raw backend training 替代路徑

### Requirement: Honest pilot limitations and compatibility
Onboarding SHALL 保留現有提交 schema，明示 shared-hank identity、dataset/output command 約定、尚未強制唯讀或 sandbox，以及後續 Bubblewrap 評估方向；不得將指南視為已實作的權限隔離。

#### Scenario: User asks about shared input safety
- **WHEN** user 查詢本版是否保證 dataset/venv 不會被修改
- **THEN** 指南說明本版未強制 sandbox，Bubblewrap 與 output enforcement 留待下一階段，並不改變 live execution
