# HEARTBEAT.md — Poly-Trader 心跳流程

> 本文件是 heartbeat 執行規範，不是單輪更新 log。每輪產出的 `data/heartbeat_*` summary/progress/report 預設為 generated artifact，不應提交到 git；current state 只落在 `ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md` 與 machine-readable artifacts。

---

## 1. 目標

Heartbeat 的目的不是「回報狀態」，而是讓專案閉環前進：

1. 收集最新事實。
2. 找出 current P0/P1 blocker。
3. 做最小但高價值的 patch。
4. 驗證 patch。
5. overwrite sync current-state docs。
6. 留下下一輪 gate。

若一輪只有 summary、沒有 patch/verify/current-state sync，視為不完整。

---

## 2. 固定順序

1. **Preflight**
   - `git status --short --branch`
   - 確認是否已有未提交變更，避免覆蓋使用者工作。
   - 讀取 `ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md` 與最新 machine artifacts。

2. **Facts collection**
   - raw/features/labels counts
   - live predictor / runtime closure
   - recent drift / circuit breaker
   - leaderboard / strategy state
   - venue readiness / execution metadata

3. **Decision framing**
   - P0/P1 blocker-first。
   - 先分清 current-live blocker、venue blocker、research blocker。
   - 不把 reference-only patch 寫成 deployment closure。

4. **Patch**
   - 優先修會影響 operator truth 或 live safety 的問題。
   - 保持小步、可測、可回滾。
   - 真實交易入口必須 fail-closed。

5. **Verify**
   - targeted pytest
   - frontend contract tests
   - `npm run build`
   - 必要時 browser QA

6. **Docs sync**
   - overwrite `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`。
   - `ARCHITECTURE.md` 只更新穩定契約，不寫每輪流水帳。
   - run logs 留在 ignored `data/heartbeat_*`。

7. **Git hygiene**
   - `git diff --check`
   - secret scan
   - commit with concise heartbeat/change summary
   - push

---

## 3. Current-state docs contract

| File | Contract |
|---|---|
| `ISSUES.md` | 只保留目前有效 blocker 與驗證入口 |
| `ROADMAP.md` | 只保留目前計畫、完成項與下一步 |
| `ORID_DECISIONS.md` | 只保留當前 ORID 判斷 |
| `ARCHITECTURE.md` | 只保留穩定架構與操作契約 |
| `HEARTBEAT.md` | 只保留本流程規範 |

禁止把每輪 heartbeat summary 持續 append 到這些文件。若需要歷史，使用 git history 或本機 ignored artifacts。

---

## 4. Generated artifact policy

預設 ignored / 不提交：

- `data/heartbeat_*_summary.json`
- `data/heartbeat_*_progress.json`
- `data/heartbeat_*_summary.md`
- `data/heartbeat_*_report.md`
- `data/heartbeat_*_report.txt`
- `HEARTBEAT_*_SUMMARY.md`
- `HEARTBEAT_SUMMARY*.md`

可以提交但要有理由與驗證：

- current-state machine artifacts used by API/UI contracts
- docs/analysis 中可重跑且仍被 UI/docs 引用的摘要
- model artifacts only when needed for runtime behavior and no secret/data leakage

---

## 5. Live execution safety contract

在 current-live blocker、initial sync、runtime proof 缺失或 venue proof 缺失時：

- buy/add exposure：fail-closed。
- automation enable：fail-closed。
- reduce/de-risk、manual mode、diagnostics、refresh：保持可用。
- `/api/trade` 必須用 structured 409 告訴前端 blocked side/reason。

此契約優先於任何 UI 便利性或 leaderboard 建議。

---

## 6. 最低驗證組合

```bash
source venv/bin/activate
python -m pytest tests/test_repo_hygiene.py -q
python -m pytest tests/test_server_startup.py -k 'api_trade or current_live_trade_blocker' -q
python -m pytest tests/test_frontend_decision_contract.py -q
cd web && npm run build
```

若修改 heartbeat runner，再加：

```bash
source venv/bin/activate
python -m pytest tests/test_hb_parallel_runner.py -q
```

---

## 7. 失敗處理

- 測試失敗：先修 root cause，不要只改測試文案。
- docs stale：修 overwrite sync 或 artifact source，不追加人工補丁。
- artifact stale：重建或明確標為 stale/reference-only。
- live safety 不明：預設 fail-closed buy/add exposure，保留 reduce/de-risk。