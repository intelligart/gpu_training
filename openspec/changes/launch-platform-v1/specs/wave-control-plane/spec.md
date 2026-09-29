## Purpose

建立 `gpu_training` 作為內部跨 repository 規劃、派工及驗證的唯一控制面，同時保留各開源專案的原始碼邊界與既有進行中 change 的歷史完整性。

## ADDED Requirements

### Requirement: 新的內部 change 使用單一規劃來源
系統 SHALL 將新建立的 Slurm、LTX-2、DCGM 與 training 內部 change 儲存在 `gpu_training` 的 OpenSpec planning home。既有 Slurm active changes MUST 留在原 planning home 直到完成並 archive，不得在進行中複製或搬移。

#### Scenario: 建立新的跨 repo change
- **WHEN** coordinator 建立涉及一個或多個 component repo 的內部 change
- **THEN** change artifacts 建立於 `gpu_training/openspec/changes/`
- **AND** artifacts 明確列出每個受影響的 target repo

#### Scenario: 處理既有 Slurm active change
- **WHEN** Slurm planning home 中仍有尚未 archive 的 change
- **THEN** 該 change 繼續由 Slurm planning home 管理至 archive
- **AND** `gpu_training` 不建立一份平行 checklist

### Requirement: Task lane 可獨立認領與驗證
每個準備實作的主要 task lane SHALL 指定 target repo、branch、允許修改的檔案範圍、相依 component commit 與可重跑驗證命令。每個 lane MUST 對應至一張 GitHub issue，小型 checkbox 不得各自重複開 issue。

#### Scenario: 規劃 artifacts 尚未核准
- **WHEN** change 仍在 proposal、design 或 spec review 階段
- **THEN** workflow 不建立實作 issue

#### Scenario: Lane 已核准可實作
- **WHEN** owner 核准 design 且 lane 已具備完整範圍與 acceptance command
- **THEN** coordinator 可為該 lane 建立或重用一張 GitHub issue
- **AND** issue 連回權威 OpenSpec task，而不複製另一份會漂移的 checklist

### Requirement: GitHub mutation 必須指定安全目標
任何 issue 或 pull request mutation MUST 使用明確設定的 `WAVE_GH_REPO`，並 MUST 在執行前顯示目標 repository 與 mutation 清單。Workflow SHALL 拒絕將內部 Wave mutation 送往已知 upstream repository。

#### Scenario: 未設定目標 repository
- **WHEN** 使用者要求建立、關閉、指派或留言 issue，但 `WAVE_GH_REPO` 未設定
- **THEN** workflow 拒絕 mutation 並要求明確設定私有或內部 fork 目標

#### Scenario: 目標是 upstream repository
- **WHEN** `WAVE_GH_REPO` 指向 Slurm、LTX-2 或 DCGM 的官方 upstream
- **THEN** workflow 拒絕內部 Wave mutation
- **AND** 不因目前 checkout 的 `origin` 自動改選其他目標

### Requirement: 完成聲明附帶可重跑證據
Contributor SHALL 在 lane 完成時記錄實際執行的 focused validation 與關鍵結果。實作者 MAY 將 lane 標示為 fixed，但 MUST NOT 自行將其標示為 verified。

#### Scenario: Contributor 完成 lane
- **WHEN** 實作與 focused validation 均完成
- **THEN** issue 與團隊紀錄包含可重跑命令、結果、主要檔案及剩餘風險
- **AND** verified 狀態保留給 reporter 或 reviewer