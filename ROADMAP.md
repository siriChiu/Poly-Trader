# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 09:33 UTC_

只保留目前計畫，不保留歷史 roadmap。

---

## 已完成
- 已完成本輪 closed-loop diagnostics：
  - `python scripts/recent_drift_report.py`
  - `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
  - `python scripts/live_decision_quality_drilldown.py`
  - `python scripts/hb_q15_support_audit.py`
  - `python scripts/hb_q15_bucket_root_cause.py`
  - `python scripts/hb_q15_boundary_replay.py`
  - `python scripts/full_ic.py`
  - `python scripts/regime_aware_ic.py`
  - `python tests/comprehensive_test.py`
- 已確認本輪 canonical 基線：
  - 1440m canonical rows = **12709**
  - `simulated_pyramid_win = 0.6470`
  - Global IC = **17 / 30**
  - TW-IC = **26 / 30**
  - regime-aware IC = **Bear 5/8 / Bull 6/8 / Chop 4/8**
- 已完成本輪 real forward-progress patch：
  - `scripts/hb_q15_support_audit.py` 新增 **support_progress contract**
  - `support_progress` 現在會持久化：
    - `status`
    - `current_rows`
    - `minimum_support_rows`
    - `gap_to_minimum`
    - `previous_rows`
    - `delta_vs_previous`
    - `stagnant_run_count`
    - `escalate_to_blocker`
    - `history`
  - `tests/test_q15_support_audit.py` 新增 q15 support-progress 回歸測試
  - `ARCHITECTURE.md` 新增 q15 support-progress machine-read contract
- 已完成驗證：
  - `python -m pytest tests/test_q15_support_audit.py -q` → **7 passed**
  - `python scripts/hb_q15_support_audit.py`
  - `python scripts/hb_q15_bucket_root_cause.py`
  - `python scripts/hb_q15_boundary_replay.py`
  - `python tests/comprehensive_test.py` → **6/6 PASS**
- 已刷新本輪 artifact：
  - `data/recent_drift_report.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/q15_support_audit.json`
  - `docs/analysis/q15_support_audit.md`
  - `data/q15_bucket_root_cause.json`
  - `docs/analysis/q15_bucket_root_cause.md`
  - `data/q15_boundary_replay.json`
  - `docs/analysis/q15_boundary_replay.md`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
- 已確認 q15 current blocker 的最新語義：
  - current live row = **`bull / CAUTION / q15`**
  - `deployment_blocker = under_minimum_exact_live_structure_bucket`
  - `current_live_structure_bucket_rows = 4`
  - `minimum_support_rows = 50`
  - `support_progress.status = no_recent_comparable_history`
  - `gap_to_minimum = 46`
  - `floor_cross_verdict = math_cross_possible_but_illegal_without_exact_support`
  - `best_single_component = feat_4h_bias50`
- 已確認 q15 replay / root-cause 線索：
  - `q15_bucket_root_cause.verdict = same_lane_neighbor_bucket_dominates`
  - `candidate_patch_feature = feat_4h_bb_pct_b`
  - `gap_to_q35_boundary = 0.0476`
  - `near_boundary_rows = 21`
  - `q15_boundary_replay.verdict = boundary_replay_not_applicable`
- 已確認 recent pathology 未解除：
  - recent 100 仍是 `100x1 bull pocket`
  - sibling-window `new_compressed = feat_4h_bias20`

---

## 主目標

### 目標 A：把 recent bull pocket 主病灶收斂到 `feat_4h_bias20` root cause
重點：
- `feat_4h_bias50` 已不再是 primary blocker
- current primary pathology 仍是 `recent 100 = 100x1 bull pocket`
- 下一輪必須直接追 `feat_4h_bias20` 為何成為新的 sibling-window `new_compressed`

### 目標 B：把 q15 support accumulation 從「現在有幾筆」升級成「正在增加 / 停滯 / 回退」
重點：
- 本輪已補 `support_progress` contract
- 目前 exact q15 rows = **4 / 50**，但 `status = no_recent_comparable_history`
- 下一輪必須讓 heartbeat summary 保留可比較歷史，否則無法判定 support 是不是卡死

### 目標 C：沿 q15 same-lane neighbor dominance 做最小 component 驗證
重點：
- `hb_q15_bucket_root_cause.py` 已把候選 patch 收斂到 `feat_4h_bb_pct_b`
- 但 `q15_boundary_replay` 仍不適用
- 下一輪若做 q15 patch，只能走 **current row vs dominant q35 neighbor bucket 的最小 counterfactual**，不可回到 q35 舊敘事

---

## 下一步
1. 下一輪先讀 `data/recent_drift_report.json`：
   - 確認 sibling-window `new_compressed` 是否仍為 `feat_4h_bias20`
   - 若仍是，直接做 `feat_4h_bias20` root-cause patch
2. 再讀 `data/q15_support_audit.json`：
   - 檢查 `support_progress.status`
   - 檢查 `support_progress.current_rows / minimum_support_rows`
   - 檢查 `support_progress.delta_vs_previous`
   - 檢查 `support_progress.stagnant_run_count`
   - 檢查 `support_progress.escalate_to_blocker`
3. 若 q15 rows 仍低於 50：
   - 維持 `reference_only_until_exact_support_ready`
   - 禁止把 `feat_4h_bias50` 的數學 floor-cross 當成 deploy 放行
4. 讀 `data/q15_bucket_root_cause.json`：
   - 若 verdict 仍為 `same_lane_neighbor_bucket_dominates`
   - 對 `feat_4h_bb_pct_b / feat_4h_bias50 / feat_4h_dist_bb_lower / feat_4h_dist_swing_low` 做 current row vs dominant q35 neighbor 差值檢查
5. 只有在 A/B/C 主線清楚後，才回頭看 q35 reference artifact 或 dual-role governance

---

## 成功標準
- `data/recent_drift_report.json` 的 sibling-window `new_compressed` 不再是 `feat_4h_bias20`，或至少已留下 1 個對應 patch + verify
- `data/q15_support_audit.json` 的 `support_progress.status` 不再只是 `no_recent_comparable_history`
- q15 exact rows 明確增加，或 heartbeat summary 已能持續累積同 bucket / 同 route 歷史
- 若做 q15 component counterfactual，artifact 必須明確保留 `reference_only_until_exact_support_ready`，不可誤寫成 deployment closure
- `ISSUES.md` / `ROADMAP.md` / `ARCHITECTURE.md` / `data/q15_support_audit.json` 對 q15 blocker 語義一致

---

## Fallback if fail
- 若 `feat_4h_bias20` 仍無 patch：下一輪只能做這件事，不再接受報告式心跳
- 若 q15 support-progress 仍無法進入可比較歷史：下一輪升級成 heartbeat governance blocker
- 若 current live bucket 再切換：先重寫 current-state docs，再評估是否回到 q35 或其他 lane

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
1. Step 0.5 先讀 `ISSUES.md` / `ROADMAP.md`，確認本輪已新增 q15 `support_progress` contract，且它不是 abstract TODO。
2. 先讀最新 `data/recent_drift_report.json`：
   - sibling-window `new_compressed` 是否仍為 `feat_4h_bias20`
   - recent 100 是否仍為 `100x1 bull pocket`
3. 再讀最新 `data/q15_support_audit.json`：
   - `support_progress.status`
   - `support_progress.current_rows`
   - `support_progress.minimum_support_rows`
   - `support_progress.delta_vs_previous`
   - `support_progress.stagnant_run_count`
   - `support_progress.escalate_to_blocker`
4. 若 q15 support 仍未達標，禁止把 `feat_4h_bias50` floor-cross 敘事寫成可 deploy；必須保留 `reference_only_until_exact_support_ready`。
5. 再讀 `data/q15_bucket_root_cause.json`；若 verdict 仍為 `same_lane_neighbor_bucket_dominates`，下一輪只能做最小 component counterfactual，優先檢查 `feat_4h_bb_pct_b`。
