# Onboarding 實作與驗證證據

## 目前狀態與範圍

狀態更新：2026-10-21。Change：`add-mcp-self-service-onboarding`，schema：`spec-driven`。

- 平台 `1.0.1` 已於 2026-10-15 部署，後續另套用 MCP GPU telemetry hotfix。
  Guide 內容版本仍為 `1.0.0`，不以內容版本推斷平台版本。
- 共用 zh-TW 內容由 tool `get_onboarding_guide`、resource
  `slurm://guides/onboarding`、prompt `slurm_onboarding` 提供。
- 2026-10-21 比對 checkout 與 installed `mcp_server.py`、`slurm_server.py`、
  `onboarding.py`，三者各自 SHA-256 一致；API/MCP 均 active、NRestarts=0。
  這不是宣稱目前 Git HEAD 或原始 tarball 等於完整 installed release。
- Onboarding 是 additive 只讀入口，不改 submission schema；同次 1.0.1 rollout
  的 HTTP 相容性是另一組變更，見 [手動 HTTP 說明](manual-http-submission.md)。
- Release root 為 `/opt/gpu-platform/releases/1.0.1`，沿用鎖定的 service venv
  `/opt/gpu-platform/venvs/1.0.0`。部署與 hotfix 歷史見
  [1.0.1 部署紀錄](release-1.0.1-test-deployment.md)。
- 實作測試已通過；獨立 reviewer acceptance（task 3.3）仍待執行。
  不自行標 verified，不 archive，也不把已部署視為新帳號 onboarding 完成。
- 本次整理保留其他 worktree 變更，不改 live units/services、帳號、NAS ACL 或 Slurm config，
  不提交 job、不 stage/commit/push。GitHub lanes 未發布：未提供明確的 `WAVE_GH_REPO`。

## 歷史失敗：job 535

Owner 當時核准一個 CPU-only Slurm MCP job：

- Node：`ia-ai-server-5`；username：`hank`；venv：`/opt/gpu-platform/venvs/1.0.0`。
- Allocation：1 GPU（介面下限）、4G RAM、command timeout 180 秒。
  不執行 CUDA/model，不干預其他 GPU processes。
- 影響限短暫 CPU tests、隔離 temporary artifact fixtures、submission metadata 與 exact log。
  不改服務；失敗即停止，若需取消只針對本 job 且另確認。
- Job `535`，submission `2abc26da8da948a0b0ae03c874ed54aa`。
- Exact log：
  `/storage/Internal_NAS/logs/hank/2abc26da8da948a0b0ae03c874ed54aa/slurm_535.out`。
- 13 tests：11 pass、2 fail。七個 submission contract 與四個 guide/mock tests 通過；
  protocol/packaging 因誤用 SDK `_mcp_server` 而失敗。這不是 passing full run。
- Installed MCP `2.2.0` 使用 `_lowlevel_server`；adapter 後續修正，SDK fields 使用
  `input_schema`／`is_error`。不能再把「修正後未重跑」當作目前狀態。
- 當時 `sacct` 回報 accounting disabled；保留 exact log 的失敗證據，不補造 terminal state。

## 後續核准的 MCP 測試：jobs 536–538

三次均為 hank、service venv `1.0.0`、server5、1 GPU allocation／4G；
CPU-only，不做 CUDA、torch import 或真實 nested submission。

| Job | 測試結果 | Exact log |
|---|---|---|
| 536 | focused 19 + legacy 10 passed | `/storage/Internal_NAS/logs/hank/aeffe49554ce4e20a4b331d4d0d21c05/slurm_536.out` |
| 537 | full 40 passed | `/storage/Internal_NAS/logs/hank/6b8a39694e2942b0bb70364236a63231/slurm_537.out` |
| 538 | final full 42 passed | `/storage/Internal_NAS/logs/hank/e6fe15c70a31466298af2c31143d9a08/slurm_538.out` |

2026-10-21 重新讀取以上 exact logs，確認各自 `Ran ... tests`／`OK`。
Jobs 537、538 均明列以下測試通過：

- `test_real_sdk_read_only_client_walkthroughs`：真實 pinned SDK 的 memory transport，
  tools-only 取得 guide；resource/prompt client 發現並讀取相同內容；
  backend mock 禁止任何呼叫，submit_job 必填 schema 保持不變。
- `test_clean_artifact_imports_protocol_and_reproducibility`：兩次建立 artifact，
  確認包含 onboarding 模組；解壓至乾淨 fixture，不依賴 checkout imports，
  重跑 protocol probe，且兩個 tarball SHA-256 相同。

Tests 刻意切到 mutable working tree 檢查候選內容，回應中的 `source_commit`
不是未提交 candidate 的身份。2026-10-21 本次只更新 shell smoke 與文件，
沒有重新執行 Python tests 或提交新的 Slurm job；上述數字是歷史執行結果。
前一輪的 38 項本機 mocked CPU tests 為輔助紀錄，不取代 task 3.2 的 MCP job 證據。

重跑以下 command **必須另取得資源核准並經 MCP 提交，不是本機執行指令**：

```text
cd /storage/SSD2/hank/gpu_training && PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 timeout 180 python -m unittest tests.test_mcp_submission tests.test_submission_api tests.test_legacy_http tests.test_onboarding tests.test_onboarding_protocol tests.test_onboarding_packaging -v
```

重跑前確認 username/venv、node、影響、timeout 與停止方式。以上 command 不授權
另一個 job；新的 tests 組合不沿用歷史 full-suite 的數量或結果。

## 文件限制 checklist

對照共用 guide、MCP_GUIDE、工程師指南與 training 使用者包：

- Dataset/output 是 command/config 約定，不是新增的 backend 必填欄位。
- 沒有自動 worker path/GPU preflight；venv listing、Slurm IDLE 不保證環境相容或 GPU 空閒。
- Username 是 audit label；controller service 使用 shared hank 身份，
  不宣稱跨節點 numeric UID/GID 已一致。
- 沒有 sandbox、強制 dataset/venv 唯讀或跨使用者隔離。
  Output/cache 分目錄是使用規範，不是不可繞過的 enforcement。
- 取得指南不提交、不取消、不寫 metadata；提交確認是 client guidance，不是 backend authorization。
- 無獨立 `job_status`；queue 消失不證明成功，資訊不足交由 Operator 核對。
- MCP failure 不降級本機或 raw HTTP training；人類手動 curl 相容入口不是 AI fallback。

Hank 的 LTX-2.5 jobs 544、545 已完成五步 training；job 545 使用固定 Git source
加 NAS YAML，無額外 NAS runner。這不驗證模型品質、HTTP curl runtime、
歷史 default venv、新帳號 onboarding 或 per-user execution。
詳見 [training 交接紀錄](mcp-training-handoff-2026-10-20.md)；不可直接重送已存在 output 的歷史 command。

## 可重跑的非 Python gates 與只讀 walkthrough

Repository root 執行：

```bash
export PATH="$HOME/.nvm/versions/node/v20.17.0/bin:$HOME/.local/bin:$PATH"
git diff --check
bash scripts/lint-agent-integrations.sh
bash scripts/validate-wave-workflow.sh
openspec validate add-mcp-self-service-onboarding --strict
bash scripts/validate-deployment-config.sh
bash -n deploy/platform-v1/smoke-mcp.sh
```

Deployment validator 只檢查設定、systemd parser 與 temporary artifact，不安裝、不重啟。
Host 既有 netplan/snapd parser warnings 不應誤報為已修復或擴大維護範圍。
Artifact 的新 checksum 只標識本次 build，不覆寫 2026-10-15 原始 tarball 的歷史身份。

在已核准的 private network 執行只讀 MCP smoke；endpoint 只由 Operator
在 machine-local 環境設定：

```bash
: "${MCP_ENDPOINT:?Operator must supply the approved MCP URL}"
bash deploy/platform-v1/smoke-mcp.sh
```

Smoke 執行 initialize、discovery、cluster/GPU 查詢、guide tool call，以及 resource read
與 prompt get，確認三種入口回傳 guide version。此 smoke 不比較完整內容；
完整一致性與零 backend calls 由上述 memory-transport tests 驗證。
MCP HTTP session 的 DELETE 僅關閉測試 session，不是取消 Slurm job。

### 2026-10-21 整理後驗證結果

- 上述非 Python gates 通過：Wave 0 errors／0 warnings，OpenSpec strict valid，
  deployment configuration valid，shell syntax／whitespace／AI integration policy 通過。
  Systemd parser 仍有既存 netplan permission 與 snapd RestartMode warnings。
- 直接執行 checkout 的新版 smoke：initialize、discovery、cluster/GPU 查詢與
  guide tool/resource read/prompt get 通過，未提交或取消 Slurm job。
  沒有把新版 smoke 安裝進 live release。
- 兩次建立目前 checkout 的 artifact，checksum 各自驗證通過，`cmp` 確認 tarball
  逐位元一致；從 artifact 讀出的三個 Python 模組也逐一與 checkout `cmp` 相同。
  這次只做 shell 封裝檢查，不宣稱重新執行 clean-import Python tests。
- 文件檢查涵蓋 14 份文件、38 個 local links、8 個 JSON examples；連結存在、
  JSON 可解析，更新範圍未含 private-IP endpoint literal。這不是全面 secret audit。
- Tasks 為 8/9，唯一未勾選項是 3.3；不改獨立 reviewer 權限或驗收標準。
- VS Code Problems tool 在此 session 無可用實作，未宣稱 editor diagnostics 通過；
  以上實際執行的 gates 與只讀 smoke 為本次驗證依據。

## 待確認的提交分組

本次不 stage／commit；以下順序用來避免漏掉依賴，不把所有 dirty files 一次加入。

1. **HTTP 相容性與 worker venv 檢查**：`slurm_server.py`、
   `tests/test_submission_api.py`、`tests/test_legacy_http.py`、
   `docs/manual-http-submission.md`。MCP username/venv 必填規則不變，
   不把人類 curl 入口當作 AI fallback。
2. **Onboarding 與完整封裝**：`mcp_server.py` 的剩餘 onboarding 變更、
   `onboarding.py`、`tests/test_mcp_submission.py` 的剩餘 fake decorators、
   `tests/test_onboarding*.py`、`deploy/platform-v1/artifact.json`、
   `deploy/platform-v1/smoke-mcp.sh`、`scripts/build-platform-v1-artifact.sh`、
   `scripts/preflight-v1.sh`、`scripts/validate-deployment-config.sh`。
   Artifact version/release root 已是 1.0.1，因此須一併帶入既有三個版本路徑變更：
   `deploy/platform-v1/systemd/slurm-api.service`、`slurm-mcp.service`、
   `slurm-api-vpn-bind.conf`，不能只提交 manifest 造成 unit/version 不一致。
3. **目前操作文件與歷史證據**：`MCP_GUIDE.md`、`docs/user-guide.md`、
   `docs/agent-training-integration.md`、`docs/training-user-pack/*.md`、
   本文件、`docs/release-1.0.1-test-deployment.md`、
   `openspec/changes/add-mcp-self-service-onboarding/`。
   `TEAM_LOG.md` 混有更早工作的變更，只挑本次條目；歷史 acceptance 文件另行確認。

三組須協調提交，確保 HTTP 文件引用的部署紀錄及指南入口一併納入最終結果。
不包含 one-shot rollout script、多使用者身份計畫、矩陣 demo、舊 NFS／Slurm 升級草稿、
其他 repository 的變更或 generated build artifacts。沒有 push，也不因提交而重新部署。

## 剩餘驗收

- Task 3.3：獨立 reviewer 重跑 onboarding acceptance 並留證；實作者不能自行 verified。
- 新 MCP client/profile／audit label 的新人實驗尚未開始；
  真正 Unix user／per-user execution 需另案身份設計與明確 live 操作核准。
- Real curl submission、矩陣 demo、取消/resume 與正式長跑不由五步 training 自動完成。
- 不因本文件、tasks 勾選或已部署而授權重新 rollout、重啟或新增 GPU job。

## 歷史交接說明

2026-10-12 的 4/9、source-candidate-only、修正後尚未重跑，是當時的部分交接狀態。
後續 jobs 536–538 與 1.0.1 rollout 已取代那些目前狀態描述，但不抹除 job 535 的失敗。
Proposal/design 的初始 planning 敘述保留為歷史決策背景；
目前實作進度以 tasks 與本文件列出的實際證據為準。
