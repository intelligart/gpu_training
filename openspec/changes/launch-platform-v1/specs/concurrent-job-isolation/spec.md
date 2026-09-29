## Purpose

讓同一使用者、相同 job name 或相同 repository 的多個 training submission 能安全並行，且每個實驗可由固定原始碼、腳本、log 與 metadata 獨立重現。

## ADDED Requirements

### Requirement: 每次 submission 具有唯一身分
系統 SHALL 在準備 job 前產生不可碰撞的 submission ID，並 SHALL 以該 ID 而非 `username` 或 `job_name` 作為 script、run directory、log 與 metadata 的識別基礎。

#### Scenario: 同一使用者同時送出同名 job
- **WHEN** 同一 `username` 併發送出兩個相同 `job_name` 的有效 request
- **THEN** 系統為兩者建立不同 submission ID
- **AND** 兩者的 script、run directory、log 與 metadata 路徑均不相同

### Requirement: 執行中的 source 不受其他 submission 修改
每個 accepted submission SHALL 綁定一個已解析的 source commit，並 SHALL 在該 submission 專屬的 run directory 執行。其他 submission 的 fetch、checkout 或 branch 更新 MUST NOT 改變已接受或執行中 job 所看到的檔案。

#### Scenario: 相同 repo 與 branch 的併發 job
- **WHEN** 兩個 job 從相同 repository 與 branch 幾乎同時提交
- **THEN** 每個 job 在接受時記錄自己的 resolved commit
- **AND** 任一 job 的 source preparation 或執行不會 checkout 或覆寫另一個 job 的 run directory

#### Scenario: Branch 在排隊期間更新
- **WHEN** remote branch 在 job accepted 後、開始執行前出現新 commit
- **THEN** 該 job 仍使用 accepted submission 記錄的 commit

### Requirement: 生成 script 不會互相覆寫
系統 SHALL 以原子方式建立 submission 專屬 script，且 MUST 在呼叫 `sbatch` 前完成內容與權限設定。`job_name` 僅可作為顯示資訊，不得單獨決定 script filename。

#### Scenario: 併發產生 script
- **WHEN** 多個 request 同時進入 script generation
- **THEN** 每個 request 取得內容完整且路徑唯一的 script
- **AND** 一個 request 不會讀取或提交另一個 request 的 script 內容

### Requirement: Metadata 與 log 一對一關聯
系統 SHALL 原子記錄 submission ID、job ID、username、source commit、run directory、script path、log path 與 request parameters。Log lookup MUST 使用該關聯，不得以第一個符合 wildcard 的檔案作為權威結果。

#### Scenario: 查詢同名 job 的 log
- **WHEN** 同一使用者有多個同名 job 且呼叫端以 job ID 查詢 log
- **THEN** 系統只回傳 metadata 對應至該 job ID 的 log

#### Scenario: Metadata 寫入失敗
- **WHEN** Slurm 已接受 job 但 metadata 無法持久化
- **THEN** 系統回報不完整 submission 狀態並留下可供營運修復的 job ID
- **AND** 不將該 submission 回報為完整成功

### Requirement: 清理不得破壞 active job
Run directory、script、metadata 與 log SHALL 遵循明確 retention policy。Cleanup MUST NOT 移除 pending 或 running job 使用中的 artifact。

#### Scenario: 執行清理
- **WHEN** cleanup 檢查一個仍為 pending 或 running 的 submission
- **THEN** 該 submission 的執行 artifact 被保留