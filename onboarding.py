"""Static, side-effect-free onboarding content shared by all MCP surfaces."""

GUIDE_VERSION = "1.0.0"
GUIDE_URI = "slurm://guides/onboarding"
PROMPT_NAME = "slurm_onboarding"

ONBOARDING_GUIDE = """# Slurm MCP 自助 onboarding
Guide version: 1.0.0
此版本是指南內容版本，獨立於平台 artifact 版本；入口新增於 platform 1.0.1。

## 1. 連線與第一次使用
使用者設定 MCP client 連線，不需要安裝 MCP server 或 Slurm。
請向 Operator 取得 <MCP_ENDPOINT>、VPN access、核准 username/venv 及資源政策；
設定只保留在 machine-local config，不分享 tokens 或 credentials。
只支援 tools 的 client：先呼叫 get_onboarding_guide。
支援 resources/prompts 的 client：讀 slurm://guides/onboarding 或取得 slurm_onboarding。
本指南只回傳說明，不呼叫 backend、不提交或取消 job、不寫 metadata。

## 2. 工作資料 checklist
- username：使用者已確認的 audit label，不得猜測，也不是登入證明。
- program：repo_url、branch/ref（建議已推送的完整 commit SHA）、command。
- dataset：NAS 上的版本路徑；若不需要 dataset，請明確填「不需要」。
- venv：核准共享環境的名稱或路徑，可用 list_venvs 查詢；不要在共享環境原地 pip install。
- resources：gpu、mem、job_name；nodelist 只有 Operator 核准時指定。
- output：明確指定每個 job 的 output/checkpoint/cache 路徑，避免共用檔名。
資料放 /storage/Internal_NAS/，共享 venv 放 /storage/Internal_NAS/venvs/。
缺資料先問清楚，不自行猜 username、venv、程式或 dataset。
dataset/output 目前仍由 command 指定，不是 submit_job 的獨立欄位。

## 3. 先 discovery，再確認提交
先呼叫 cluster_info、list_venvs；需要 GPU telemetry 時呼叫 gpu_status。
不要寫死 GPU 型號或數量，Slurm IDLE 不代表實體 GPU 無手動 workload。
若 gpu_status 只有 node 標題、資訊不完整或 GPU 已有其他 processes，停止並詢問 Operator。
本版沒有 worker preflight，指南不能驗證所有節點上的 dataset/venv 路徑或 CUDA 相容性。
提交前顯示 username、repo/ref、command、dataset、venv、gpu/mem、nodelist 與 output 摘要，
取得本次明確確認後才呼叫 submit_job。這是 client 指引，不是 backend authorization gate。
成功必須回報 submission_id、job_id、status；有 repo source 時也核對 source_commit。
LLM 整理需求並呼叫 MCP，實際節點/GPU allocation 由 Slurm 分配。

## 4. 範本：第一次只讀檢查
我的 username 是 <username>，venv 是 <venv>。
請先取得 onboarding guide，再查 cluster_info、list_venvs 與 GPU 狀態。
這次不要提交或取消 job。缺資料先詢問，不要在本機執行 training。

## 5. 範本：1 GPU smoke
username=<username>，venv=<venv>，repo_url=<repo-url>，branch=<full-commit-sha>。
dataset=<NAS-version-path 或不需要>，gpu=1，mem=<memory>，job_name=<username>-smoke。
command=<smoke-command，含明確 dataset/output 參數>。
先整理摘要，不要提交；等我明確確認後才呼叫 submit_job。

## 6. 範本：2 GPU distributed training
username=<username>，venv=<venv>，repo_url=<repo-url>，branch=<full-commit-sha>。
dataset=<NAS-version-path>，gpu=2，mem=<memory>，job_name=<username>-train。
command=torchrun --standalone --nproc_per_node=2 <entrypoint> <dataset/output-args>。
先確認程式支援 distributed training；gpu=2 不會自動把單 GPU 程式變成 distributed。
output 建議以 $SLURM_JOB_ID 分目錄；未核准不要指定 nodelist。
先整理摘要，取得我的明確確認後才提交；不要自動跨 node 分配。

## 7. 追蹤與兩步取消
範本：請用 list_jobs、job_history 查 job <job-id>，再以 get_logs 讀 exact log。
不要用 wildcard 猜 log。Queue 不見或 history status 不足以證明 terminal state；
目前沒有獨立 job_status tool，需要時請 Operator 向 Slurm 核對。
取消第一步：查 job <job-id> 的 job name/status，先回報，不要取消。
取消第二步：我確認取消 job <job-id>，只呼叫 cancel_job 並回報結果。

## 8. 失敗與安全界線
MCP 無法連線、submission 失敗或回應缺必要 ID 時停止並回報，通知 Operator。
不得降級到本機/notebook training，也不得使用 raw API fallback。
實際 jobs 都以 shared-hank 身份執行；username 僅為 audit label。
本版尚未啟用 sandbox，沒有強制 dataset/venv 唯讀或跨使用者權限隔離。
Script/log/source paths 有 submission 隔離；training 的 output/cache 隔離仍是使用規範。
不要修改共享 dataset、base checkpoint、venv；host 上其他同權限程序仍可能修改它們。
後續才評估 Bubblewrap、結構化提交及 submission 專屬 output/cache/tmp 強制保護。
本指南不是安全保證，只適合受信任 VPN 團隊。
"""


def get_guide() -> str:
    """Return the same immutable text without inspecting the host or backend."""
    return ONBOARDING_GUIDE