# GPU Platform Roadmap

本文件只收錄尚未建立 OpenSpec change 的方向；active work 以
`openspec/changes/` 為準，不在此重複 task checklist。

## Planned

- v1 上線後建立 identity、SSO、RBAC 與 job ownership security change。
- 將 Training domain 依負載與發布週期評估抽成獨立 private service/repository。
- 建立 component upstream update detection；production merge/deploy 維持人工核准。
- 逐步以 DCGM exporter/adapter 取代臨時 SSH `nvidia-smi` 查詢。