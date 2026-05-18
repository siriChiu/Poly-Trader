# Heartbeat Harness Q&A Gate

> 用一問一答把 heartbeat 從「代理努力工作」升級為「代理在明確 harness 中工作」。每輪都要能回答問題、指出證據、說明失敗時怎麼收斂。

---

## 使用方式

- 每輪 heartbeat 開始時，先跑 `python scripts/heartbeat_harness_check.py --format text`。
- 不需要把完整問答貼進最終回覆；但內部決策必須能對應到下列 gate。
- 若任何 gate 答案是「不知道」或「無 evidence」，不要硬做大 patch；先補可觀測性、契約或文件地圖。

---

## Phase 0 — Context map

### HQ0_context_map
**問：我是否已經拿到最短可用地圖，而不是把整個 repo 塞進上下文？**

**答題規則：**
- 已讀 `AGENTS.md`、`HEARTBEAT.md`、`AI_AGENT_ROLE.md`。
- 若 `graphify-out/` 存在，先讀 `graphify-out/GRAPH_REPORT.md` 與 wiki index，或用 `graphify query` 定位。
- 清楚知道本輪會碰哪些檔案，以及哪些 dirty files 不能覆蓋。
- 工程 heartbeat 必須已取得上一輪 PM heartbeat 的結論與決定（cron `context_from` 或 PM current-state docs），並把它列為本輪輸入。

**證據：** `git status --short --branch`、相關 docs 路徑、必要 graphify query、上一輪 PM heartbeat handoff。

**若失敗：** 停止改碼，先補入口地圖或縮小任務範圍。

---

## Phase 1 — Goal and boundary

### HQ1_goal_and_boundary
**問：這輪 heartbeat 的 human intent 是什麼，邊界是什麼？**

**答題規則：**
- 用一句話寫出目標。
- 先寫明本輪承接哪一條 PM heartbeat 結論 / 決定，再從工程事實選 P0/P1。
- 明確說出不做什麼：不追交易頻率、不降低 gates、不把 reference patch 當 deployment closure。
- 若目標含真實交易，buy/add exposure 一律 fail-closed 直到 runtime proof 充足。

**證據：** 使用者要求、上一輪 PM heartbeat 結論 / 決定、`ISSUES.md` current priority、`ROADMAP.md` next gate。

**若失敗：** 只做 facts collection，不做 risky patch。

---

## Phase 2 — Current truth

### HQ2_current_truth
**問：現在的 runtime / research / governance 真相是什麼？**

**答題規則：**
- 至少分開三類：current-live blocker、research blocker、venue/source blocker。
- 優先讀 machine-readable artifacts，再同步 Markdown 敘事。
- 不允許用 stale artifact 當 fresh truth。

**證據入口：**
- `data/live_predict_probe.json`
- `data/live_decision_quality_drilldown.json`
- `data/recent_drift_report.json`
- `data/high_conviction_topk_oos_matrix.json`
- `data/execution_metadata_smoke.json`
- `issues.json`

**若失敗：** 先刷新 probe 或標示 stale/reference-only。

---

## Phase 3 — Missing capability

### HQ3_missing_capability
**問：阻塞的是模型/資料問題，還是 harness 能力不足？**

**答題規則：**
把缺口歸類為其中一種：

1. **Map gap**：代理不知道該讀哪裡。
2. **Tool gap**：有事實但沒有腳本可穩定重跑。
3. **Signal gap**：UI/API/artifact 沒有暴露可讀證據。
4. **Constraint gap**：規則只寫在文件，沒有 test/lint/checker。
5. **Review gap**：patch 沒有可重現的驗證方式。

**證據：** 失敗測試、缺失檔案、artifact 欄位缺失、UI copy 漂移。

**若失敗：** 本輪 patch 應優先補 harness，而不是堆更多策略邏輯。

---

## Phase 4 — Patch contract

### HQ4_patch_contract
**問：最小、可測、可回滾的 patch 是什麼？**

**答題規則：**
- 一輪只修 1–3 個高價值點。
- 優先修 operator truth、live safety、docs/artifact split-brain、機械檢查缺口。
- 不改未知 dirty files；不把 generated run logs 加進 git。

**證據：** `git diff --name-only` 與 targeted file list。

**若失敗：** 拆小，或先寫 plan / contract test。

---

## Phase 5 — Verification loop

### HQ5_verification_loop
**問：我如何讓另一個代理不信任我也能驗證？**

**答題規則：**
- 每個 patch 至少有一個機械驗證：pytest、script、build、API smoke、browser QA、artifact schema。
- 驗證命令要貼近修改範圍。
- 若驗證耗時或環境缺依賴，明確列出已跑與未跑原因。

**最低 harness 驗證：**

```bash
python scripts/heartbeat_harness_check.py --format text
python -m pytest tests/test_heartbeat_harness_contract.py -q
```

**Runtime API compact probes（需要本地 API 服務已啟動）：**

```bash
curl -fsS http://127.0.0.1:8000/api/status | python scripts/hb_compact_status_probe.py
curl -fsS http://127.0.0.1:8000/api/models/leaderboard | python scripts/hb_compact_leaderboard_probe.py
curl -fsS http://127.0.0.1:8000/api/execution/overview | python scripts/hb_compact_execution_overview_probe.py
```

**若失敗：** 先修 root cause，不用敘事蓋過紅燈。

---

## Phase 6 — Docs sync

### HQ6_docs_sync
**問：current-state docs 是否和 machine-readable truth 對齊？**

**答題規則：**
- `ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md` 只保留 current state。
- `HEARTBEAT.md`、`docs/harness/*` 是 evergreen process / contract，不記錄單輪流水帳。
- `ARCHITECTURE.md` 只記穩定契約。

**證據：** docs diff、harness checker、`git diff --check`。

**若失敗：** 修 overwrite sync 或來源 artifact；不要 append 補丁段落。

---

## Phase 7 — Failure escalation

### HQ7_failure_escalation
**問：如果同一問題又失敗，下一輪要怎麼升級？**

**答題規則：**
- 同一 blocker 連續 2 輪未動：改問 missing harness capability。
- 連續 3 輪 report-only：下一輪必須修一個 checker/test/artifact/source-of-truth。
- 同一路徑 3 次 patch 無效：比較 alternative architecture，而不是繼續 prompt tuning。

**證據：** issue ID、上輪 gate、失敗命令、fallback。

**若失敗：** 開/更新 P0/P1 blocker。

---

## Phase 8 — User report

### HQ8_user_report
**問：最後回報是否讓使用者 30 秒內知道系統前進在哪？**

**答題規則：**
- 使用繁體中文，先說完成與驗證，再說仍阻塞什麼。
- 列出實際檔案與命令結果。
- 若未 commit/push，要明確說原因（例如既有 dirty files 非本輪產生）。

**證據：** final summary、git status、commit hash（若有）。

---

## 最小問答輸出模板

```text
Q: 這輪目標？
A: <一句話 human intent + 邊界>

Q: 目前唯一 P0/P1？
A: <blocker + machine evidence>

Q: 缺的是策略還是 harness？
A: <Map/Tool/Signal/Constraint/Review gap>

Q: 本輪 patch？
A: <files + why minimal>

Q: 驗證？
A: <commands + pass/fail>

Q: 下一輪 gate？
A: <success condition + fallback>
```
