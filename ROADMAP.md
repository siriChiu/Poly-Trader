# ROADMAP.md — Current Plan Only

_最後更新：2026-05-15 04:08:07 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成 / 本輪前進

- **fast heartbeat #1232 完成 collect + diagnostics + docs sync**
  - `Raw=33231 / Features=24418 / Labels=66426`；本輪 collect pipeline `+2/+2/+2`，runner `2/2 passed`，`elapsed=13.1s`。
  - current docs sync 已由 runner 自動完成：`ISSUES.md / ROADMAP.md / ORID_DECISIONS.md` 對齊 `issues.json / live_predict_probe / live_decision_quality_drilldown`。
- **本輪產品化 patch：Dashboard support-stall blocker 可視化**
  - `web/src/components/ConfidenceIndicator.tsx` 新增 support accumulation 停滯卡，顯示 `28/50`、缺口 `22`、連續停滯 `5` 輪、停滯原因與 operator action。
  - `web/src/utils/runtimeCopy.ts` 將 `stalled_under_minimum` / `stalled_support_accumulation` 人類化成「連續停滯 N 輪」，避免 operator 把 `delta=0` 誤讀為中性狀態。
  - `web/src/pages/Dashboard.tsx` 接收完整 `support_progress` typed contract；`tests/test_frontend_decision_contract.py` 鎖定 runtime copy / Dashboard / ConfidenceIndicator contract。
- **驗證已完成**
  - `python -m pytest tests/test_frontend_decision_contract.py -q` → `76 passed`。
  - `cd web && npm run build` → TypeScript + Vite build succeeded。
  - `python -m pytest tests/test_server_startup.py tests/test_hb_predict_probe.py tests/test_hb_parallel_runner.py -q` → `207 passed`。
  - `python scripts/heartbeat_harness_check.py --format text` → `RESULT: PASS`。
  - `python scripts/hb_predict_probe.py` → fresh probe confirms `deployment_blocker=under_minimum_exact_live_structure_bucket` / q35 `28/50` / `allowed_layers=0` / support stall escalated。

---

## 主目標

### 目標 A：補足 current-live q35 exact support，讓 blocker 可被真實解除
**目前真相**
- `deployment_blocker=under_minimum_exact_live_structure_bucket`。
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=28/50` / `gap=22`。
- `support_progress.status=stalled_under_minimum` / `delta_vs_previous=0` / `stagnant_run_count=5` / `stalled_support_accumulation=True` / `escalate_to_blocker=True`。

**成功標準**
- current-live exact support 達 `>=50` 且 support identity 沒有 semantic drift。
- `/`、`/lab`、`/execution`、`/execution/status`、probe、docs 都顯示相同 current-live blocker truth。
- buy/add exposure 在 blocker 解除前持續 fail-closed；risk-off path 保留。

### 目標 B：讓 support-stall 與 score-only redesign 在 operator UI 中不可誤讀
**目前真相**
- q35 redesign 可作 score-layer 研究參考，但 current runtime 仍 `allowed_layers=0`，support `28/50`。
- Dashboard confidence card 已補上 support-stall 直觀卡與 q35 operator action。

**成功標準**
- Operator 一眼能看到：停滯不是中性；q35 分數重設 / base-stack redesign 不能替代 exact support 與 deployment guardrail。
- Frontend contract tests 持續鎖住停滯欄位、中文 copy 與 q35 警示。

### 目標 C：把 high-conviction Top-K OOS gate 維持成研究→影子驗證→部署候選的 fail-closed pipeline
**目前真相**
- `data/high_conviction_topk_oos_matrix.json` fresh；`rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidate_rows=6`。
- nearest candidate 離線通過 OOS/risk gate，但 live gate 仍失敗：`support_route_not_deployable` + `deployment_blocker_active`。

**成功標準**
- Strategy Lab/API 先顯示 nearest-deployable candidate 與 live gate failures，而不是只看最高 ROI。
- live support/venue gates 未過前，所有候選保持 observe/shadow，不可 deploy。

### 目標 D：維持 source / venue / leaderboard governance 的產品真相
**目前真相**
- source blockers：`fin_netflow auth_missing`、`claw auth_missing`、`claw_intensity auth_missing`、`nest_pred tls_verify_failed`。
- venue proof 仍缺 credential/order-ack/fill lifecycle。
- leaderboard dual-role governance active；`leaderboard_count=6`，非 placeholder-only。

**成功標準**
- Venue/source blocker 在 operator-facing surfaces 持續可見且 fail-closed。
- Leaderboard 不回退成 placeholder-only 或混淆 global ranking 與 support-aware production。

---

## 下一輪 gate

1. **current-live q35 support accumulation gate**
   - 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/`、browser `/lab`、browser `/execution/status`。
   - 升級 blocker：若 support rows 仍停在 `28` 且 `stagnant_run_count` 增加，需追資料累積/分桶 identity 路徑，而非重跑模型。
2. **Dashboard support-stall UI guardrail gate**
   - 驗證：`python -m pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`。
   - 升級 blocker：若停滯卡或 q35 score-only 警示從 Dashboard 消失，或 copy 回退成 raw enum。
3. **Top-K OOS fail-closed gate**
   - 驗證：`data/high_conviction_topk_oos_matrix.json`、`/api/models/leaderboard.high_conviction_topk`、Strategy Lab Top-K panel。
   - 升級 blocker：若 OOS-pass row 在 live support gate 未過時被標為 deployable。
4. **venue/source proof gate**
   - 驗證：`data/execution_metadata_smoke.json`、`/execution`、`/execution/status`。
   - 升級 blocker：若 credential/order/fill proof 未補齊卻顯示 runtime-ready。

---

## 成功標準

- current-live blocker 清楚且唯一：`under_minimum_exact_live_structure_bucket`。
- q35 current-live support truth 維持：`28/50`、`gap=22`、`stalled_under_minimum`、`stagnant_run_count=5`。
- Dashboard/Strategy Lab/Execution 不把 support stall、score-only redesign、OOS-pass candidate 或 venue metadata 誤解為 deployment closure。
- 每輪 heartbeat 都完成：facts → patch/productization → verify → docs overwrite sync。
