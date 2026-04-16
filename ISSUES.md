# ISSUES.md — Current State Only

_最後更新：2026-04-17 05:46 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪主線是 **live q15 deployment blocker truth + artifact freshness truth**。

本輪已完成的直接產品化前進：
- 修正 `scripts/hb_predict_probe.py`：現在每次執行都會**同步覆寫** `data/live_predict_probe.json`
- 這解掉一個 productization 級真相問題：後續 `live_decision_quality_drilldown.py` / `hb_q15_support_audit.py` 不再默默吃舊 probe snapshot
- 已用最新 probe → drilldown → q15 audit 重跑，runtime artifacts 已從舊 q35 snapshot 對齊到**目前真實 q15 live row**

目前 live 真相：
- live path：`bull / CAUTION / D`
- `structure_bucket = CAUTION|structure_quality_caution|q15`
- `allowed_layers_raw = 0`
- `allowed_layers = 0`
- `deployment_blocker = under_minimum_exact_live_structure_bucket`
- q15 exact support：**4 / 50**
- `support_progress.status = accumulating`
- `feat_4h_bias50` 仍是最佳單點 floor-crosser，但在 support 未達標前只可做 **reference-only calibration research**

驗證：
- `./venv/bin/python -m pytest tests/test_hb_predict_probe.py tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py::test_collect_q15_support_audit_diagnostics_reads_support_and_floor_verdicts -q` → **10 passed**
- runtime refresh：
  - `./venv/bin/python scripts/hb_predict_probe.py`
  - `./venv/bin/python scripts/live_decision_quality_drilldown.py`
  - `HB_RUN_LABEL=20260417-cron ./venv/bin/python scripts/hb_q15_support_audit.py`
- 產物確認：
  - `data/live_predict_probe.json` → current live row 已是 q15 / 4 rows
  - `docs/analysis/live_decision_quality_drilldown.md` → floor gap `0.2355`、best single component `feat_4h_bias50`
  - `data/q15_support_audit.json` → support progress `4/50`, `accumulating`, `delta_vs_previous=+4`

---

## Open Issues

### P0. q15 exact support 仍低於 deployment minimum，live 不能放行
**現況**
- current live bucket：`CAUTION|structure_quality_caution|q15`
- exact support：`4 / 50`
- `support_progress.status = accumulating`
- `deployment_blocker = under_minimum_exact_live_structure_bucket`

**風險**
- 即使 exact rows 已從 0 增加到 4，仍遠低於 deployment-grade minimum
- 若把「開始累積」誤讀成「已可部署」，會讓 runtime / docs /人工判讀再次失真

**下一步**
- 持續 machine-check `support_progress`
- exact rows 未達 50 前，保持 blocker，不得用 proxy/neighbor 當 release 證據

### P0. q15 floor gap 的最佳單點修補仍只是研究，不是 release path
**現況**
- drilldown：`remaining_gap_to_floor = 0.2355`
- q15 audit：`best_single_component = feat_4h_bias50`
- q15 audit：`required_score_delta_to_cross_floor ≈ 0.7767`
- legality verdict：`math_cross_possible_but_illegal_without_exact_support`

**風險**
- 若先做 bias50 calibration，而 exact support 還沒到 minimum，會把研究結果誤包裝成 deployment closure

**下一步**
- 在 q15 exact support 達標前，bias50 只保留為 reference-only component experiment
- support ready 後才允許進入 component patch + regression verify

### P1. collect-enabled freshness / full fast-lane 還沒有在本輪重新閉環
**現況**
- 本輪聚焦在 runtime artifact freshness truth 與 q15 blocker 對齊
- collect/watchdog/freshness 不是本輪驗證重點

**風險**
- 若把 artifact truth 修正誤讀成整體 live-ready，會忽略 collect/freshness 仍需另一次閉環確認

**下一步**
- 下一輪重跑 collect-enabled heartbeat，確認 freshness / candidate governance / runtime blocker 同步健康

---

## Not Issues
- 不是「仍停在舊 q35 live row」：本輪已修正 probe 持久化，current artifacts 已對齊 q15 live row
- 不是「support 完全停滯」：q15 exact rows 已由 0 增至 4，當前是 **accumulating**，不是 stalled
- 不是「bias50 已可直接解 blocker」：目前 legality 仍明確是 **illegal without exact support**

---

## Current Priority
1. 把 q15 exact support 從 `4 / 50` 繼續累積到 deployment minimum，並持續追 `support_progress`
2. 在 support 未達標前，禁止把 `feat_4h_bias50` calibration research 誤寫成 live release
3. 下一輪重做 collect-enabled freshness 閉環，確認資料新鮮度與 runtime 真相同步成立
