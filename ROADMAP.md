# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 11:36 UTC_

只保留目前計畫，不保留歷史 roadmap。

---

## 已完成
- 已完成本輪 closed-loop diagnostics：
  - `python scripts/recent_drift_report.py`
  - `python scripts/full_ic.py`
  - `python scripts/regime_aware_ic.py`
  - `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
  - `python scripts/live_decision_quality_drilldown.py`
  - `python scripts/hb_q15_support_audit.py`
  - `python scripts/hb_q15_bucket_root_cause.py`
  - `python scripts/hb_q15_boundary_replay.py`
  - `python tests/comprehensive_test.py`
- 已確認本輪 canonical 基線：
  - Raw / Features / Labels = **30527 / 18664 / 43750**
  - 1440m canonical rows = **12709**
  - `simulated_pyramid_win = 0.6470`
  - Global IC = **17 / 30**
  - TW-IC = **26 / 30**
  - regime-aware IC = **Bear 5/8 / Bull 6/8 / Chop 4/8**
- 已完成本輪 real forward-progress patch：
  - `scripts/hb_q15_boundary_replay.py` 新增 **`same_lane_counterfactual_bucket_proxy_only`** verdict
  - q15 boundary artifact 現在會直接把 `feat_4h_bb_pct_b` 最小反事實收斂成 bucket-proxy-only，而不是只留下 `boundary_replay_not_applicable`
  - `tests/test_q15_boundary_replay.py` 新增 same-lane bucket-proxy regression
  - `ARCHITECTURE.md` 已同步 q15 boundary-replay contract
- 已完成驗證：
  - `python -m pytest tests/test_q15_boundary_replay.py -q` → **3 passed**
  - `python scripts/hb_q15_boundary_replay.py` → `same_lane_counterfactual_bucket_proxy_only`
  - `python scripts/hb_q15_support_audit.py`
  - `python scripts/hb_q15_bucket_root_cause.py`
  - `python tests/comprehensive_test.py` → **6/6 PASS**
- 已刷新本輪 artifact：
  - `data/recent_drift_report.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/q15_support_audit.json`
  - `docs/analysis/q15_support_audit.md`
  - `data/q15_bucket_root_cause.json`
  - `docs/analysis/q15_bucket_root_cause.md`
  - `data/q15_boundary_replay.json`
  - `docs/analysis/q15_boundary_replay.md`
- 已把上輪 carry-forward 轉成明確結論：
  - `feat_4h_bb_pct_b` **已證明是 structure proxy，不是 deployable floor fix**
  - q15 `support_progress` **維持 accumulating，但仍只有 4 / 50**
  - `feat_4h_bias50` 仍是目前唯一可單點跨 floor 的 component，但在 support 未達標前只能是 reference-only

---

## 主目標

### 目標 A：直接處理 `feat_4h_bias50 / base stack` 的 q15 floor-gap root cause
重點：
- `hb_q15_support_audit.py` 指向 `best_single_component = feat_4h_bias50`
- `hb_q15_boundary_replay.py` 已證明 `feat_4h_bb_pct_b` 只會 rebucket、不會跨 floor
- 下一輪主線不能再停留在「再做一次 bb_pct_b / boundary review」

### 目標 B：讓 q15 support accumulation 持續可比較
重點：
- 目前 exact q15 rows = **4 / 50**
- `support_progress.status = accumulating`
- 下一輪必須持續保留同一 bucket 歷史，確認是增加、停滯，或回退

### 目標 C：維持 q35 / `feat_4h_bb_pct_b` 的 reference-only 合法性邊界
重點：
- `feat_4h_bb_pct_b` 是 structure proxy，不是 deploy patch
- q35 是 dominant same-lane neighbor bucket，不是 current-live closure
- 任何 component / bucket 實驗都不得越權解除 exact-support blocker

---

## 下一步
1. 下一輪先讀 `data/q15_boundary_replay.json`：
   - 確認 `verdict` 是否仍為 `same_lane_counterfactual_bucket_proxy_only`
   - 若仍是，禁止把 `feat_4h_bb_pct_b` 當 deploy patch；直接做 `feat_4h_bias50 / base stack` floor-gap artifact
2. 再讀 `data/q15_support_audit.json`：
   - 檢查 `support_progress.status`
   - 檢查 `support_progress.current_rows / minimum_support_rows`
   - 檢查 `support_progress.delta_vs_previous`
   - 檢查 `support_progress.stagnant_run_count`
   - 檢查 `support_progress.escalate_to_blocker`
3. 再讀 `data/recent_drift_report.json`：
   - 確認 primary window 是否仍為 recent 100 bull pocket
   - 若 `new_compressed` 仍是 `feat_4h_bb_pct_b`，文件中必須明寫它只是 structure proxy，而不是主 deploy blocker
4. 若 q15 rows 仍低於 50：
   - 維持 `reference_only_until_exact_support_ready`
   - 禁止把 `feat_4h_bias50` floor-cross 寫成 deploy 放行
5. 只有在 A/B/C 三條線明確後，才回頭看 q35 reference artifact 或其他 side quest

---

## 成功標準
- 已留下 1 個直接回答 `feat_4h_bias50 / base stack` 是否為 q15 exact-lane 主 floor-gap blocker 的 artifact 或 patch
- `data/q15_support_audit.json` 的 `support_progress.current_rows` 相比本輪 **不下降**，且歷史鏈持續存在
- `ISSUES.md` / `ROADMAP.md` / `ARCHITECTURE.md` / `data/q15_boundary_replay.json` 對 blocker 的描述一致：**`feat_4h_bb_pct_b` 是 structure proxy；目前主 blocker 是 `feat_4h_bias50 + exact support`**
- 若 component 實驗仍只具 reference value，artifact / probe / docs 都一致保留 `reference_only_until_exact_support_ready`

---

## Fallback if fail
- 若下一輪沒有真正碰 `feat_4h_bias50 / base stack`：升級為 heartbeat empty-progress blocker
- 若 q15 rows 停在 4 且 `support_progress` 轉 stalled/regressed：升級為 support accumulation blocker
- 若 current live bucket 再切換：先重寫 current-state docs，再決定是否切回 q35 或其他 lane

---

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`
- `data/recent_drift_report.json`
- `data/live_predict_probe.json`
- `data/live_decision_quality_drilldown.json`
- `data/q15_support_audit.json`
- `docs/analysis/q15_support_audit.md`
- `data/q15_bucket_root_cause.json`
- `docs/analysis/q15_bucket_root_cause.md`
- `data/q15_boundary_replay.json`
- `docs/analysis/q15_boundary_replay.md`

---

## Carry-forward input for next heartbeat
1. Step 0.5 先讀 `ISSUES.md` / `ROADMAP.md`，確認本輪已把 `feat_4h_bb_pct_b` 正式降級成 structure proxy，而不是 deploy patch。
2. 先讀最新 `data/q15_boundary_replay.json`：
   - `verdict` 是否仍為 `same_lane_counterfactual_bucket_proxy_only`
   - `component_counterfactual.trade_floor_gap_after` 是否仍 < 0
3. 再讀最新 `data/q15_support_audit.json`：
   - `support_progress.status`
   - `support_progress.current_rows`
   - `support_progress.delta_vs_previous`
   - `support_progress.stagnant_run_count`
   - `support_progress.escalate_to_blocker`
4. 再讀 `data/q15_bucket_root_cause.json`：
   - `candidate_patch_feature`
   - `gap_to_q35_boundary`
   - `near_boundary_rows`
5. 若 q15 support 仍未達標，禁止把 bias50 / q35 / bb_pct_b 任一單點敘事寫成 current deploy closure；必須維持 `reference_only_until_exact_support_ready`。
