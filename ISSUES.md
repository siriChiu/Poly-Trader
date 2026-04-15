# ISSUES.md — Current State Only

_最後更新：2026-04-15 08:27 UTC — Heartbeat #1012（本輪新增 q15 exact-bucket root-cause artifact，將 q15 0-row blocker 從籠統的 `same_lane_shifted_to_neighbor_bucket` 收斂成可 machine-read 的 boundary / scoring / projection 判讀。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 做 q15 exact-bucket root-cause artifact；
  2. 做 q15 component-to-bucket counterfactual；
  3. 維持 `profile_split / fin_netflow auth blocker / breaker false-positive` 零漂移治理。
- **Success gate**
  1. 至少留下 1 個與 **q15 exact bucket row generation 或 boundary repair** 直接相關的 patch / artifact / verify；
  2. machine-read 回答 `same_lane_shifted_to_neighbor_bucket` 的最小可修補原因；
  3. `q15_support_audit` 與 `leaderboard_feature_profile_probe` 的 `support_governance_route / exact_bucket_proxy_rows` 不得再漂移。
- **Fallback if fail**
  - 若 heartbeat 又把主焦點退回 breaker 或 generic q35，視為 regression；
  - 若沒有 exact support 證據就直接 relax runtime gate，視為風控 regression；
  - 若 next run 仍沒有 exact-bucket repair path，升級為 q15 exact-bucket blocker。

### 本輪承接結果
- **已處理**
  - 新增 `scripts/hb_q15_bucket_root_cause.py`，把 q15 blocker 轉成 machine-readable artifact：`data/q15_bucket_root_cause.json` + `docs/analysis/q15_bucket_root_cause.md`。
  - `scripts/hb_parallel_runner.py` 已接入 q15 root-cause step，fast heartbeat 會自動刷新並寫入 `heartbeat_1012_summary.json`。
  - 已新增測試：
    - `tests/test_q15_bucket_root_cause.py`
    - `tests/test_hb_parallel_runner.py`（新增 root-cause diagnostics / runner order 覆蓋）
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_q15_bucket_root_cause.py tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py -q` → **26 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1012` → **通過**
- **本輪 machine-read 結論**
  - `q15_support_audit.support_route.verdict = exact_bucket_missing_proxy_reference_only`
  - `q15_support_audit.floor_cross_legality.verdict = math_cross_possible_but_illegal_without_exact_support`
  - `q15_bucket_root_cause.verdict = boundary_sensitivity_candidate`
  - `q15_bucket_root_cause.candidate_patch_type = bucket_boundary_review`
  - `q15_bucket_root_cause.candidate_patch_feature = feat_4h_bb_pct_b`
  - `q15_bucket_root_cause.current_live.gap_to_q35_boundary = 0.0116`
  - `q15_bucket_root_cause.exact_live_lane.near_boundary_rows = 2`
- **本輪明確不做**
  - 不直接 relax q15 runtime gate；
  - 不把 q35 generic scaling 重新升級成主 blocker；
  - 不把 `fin_netflow` auth blocker 與 q15 exact-bucket root cause 混寫。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_q15_bucket_root_cause.py`
  - `scripts/hb_parallel_runner.py`
  - `tests/test_q15_bucket_root_cause.py`
  - `tests/test_hb_parallel_runner.py`
  - `ARCHITECTURE.md`
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_q15_bucket_root_cause.py tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py -q` → **26 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1012`
- **已刷新 artifacts**
  - `data/heartbeat_1012_summary.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/q35_scaling_audit.json`
  - `data/q15_support_audit.json`
  - `data/q15_bucket_root_cause.json`
  - `data/circuit_breaker_audit.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`
  - `docs/analysis/q15_bucket_root_cause.md`

### 資料 / 新鮮度 / canonical target
- Heartbeat #1012：
  - Raw / Features / Labels：**21588 / 13017 / 43345**
  - 本輪增量：**+1 raw / +1 feature / +2 labels**
  - canonical target `simulated_pyramid_win`：**0.5756**
  - 240m labels：**21735 rows / target_rows 12813 / lag_vs_raw 約 3.4h**
  - 1440m labels：**12525 rows / target_rows 12525 / lag_vs_raw 約 23.1h**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**18/30 pass**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 6/8**
- drift primary window：**recent 250**
  - alerts：`label_imbalance`, `regime_concentration`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 94.4%**
  - win_rate：**0.9680**
  - avg_quality：**0.6569**
  - avg_pnl：**+0.0207**
  - avg_drawdown_penalty：**0.0414**
  - tail_target_streak：**3x0**（since `2026-04-14 08:33:04.582411`）
- 判讀：canonical 1440m lane 仍健康；本輪主 blocker 仍是 q15 exact support / bucket repair，不是 drift，也不是 breaker。

### Live contract / q15 support / root-cause artifact
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - entry_quality_label：**D**
  - decision_quality_label：**B**
  - decision_quality scope：**`regime_label+regime_gate+entry_quality_label`**（rows=`76`）
  - expected_win_rate / quality：**0.9605 / 0.6536**
  - allowed_layers：**0 → 0**
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `execution_guardrail_reason = unsupported_exact_live_structure_bucket_blocks_trade`
- `data/q15_support_audit.json`
  - `support_governance_route = exact_live_bucket_proxy_available`
  - `preferred_support_cohort = bull_live_exact_bucket_proxy`
  - `exact_live_bucket_proxy_rows = 4`
  - `exact_live_lane_proxy_rows = 421`
  - `supported_neighbor_rows = 158`
  - `support_route.verdict = exact_bucket_missing_proxy_reference_only`
  - `floor_cross_legality.verdict = math_cross_possible_but_illegal_without_exact_support`
  - `remaining_gap_to_floor = 0.1148`
  - `best_single_component = feat_4h_bias50`
- `data/q15_bucket_root_cause.json`
  - `verdict = boundary_sensitivity_candidate`
  - `candidate_patch_type = bucket_boundary_review`
  - `candidate_patch_feature = feat_4h_bb_pct_b`
  - `current_live.structure_quality = 0.3384`
  - `gap_to_q35_boundary = 0.0116`
  - `exact_live_lane.bucket_counts.q15 = 4`
  - `exact_live_lane.dominant_neighbor_bucket = CAUTION|structure_quality_caution|q35`
  - `exact_live_lane.dominant_neighbor_rows = 158`
  - `exact_live_lane.near_boundary_rows = 2`
- 判讀：本輪已把 `same_lane_shifted_to_neighbor_bucket` 收斂成 **q15↔q35 邊界敏感候選**，但這仍只是 research artifact；在 exact support 未達 deployment 門檻前，不可直接放寬 runtime gate。

### Q35 / support route / profile split
- `data/q35_scaling_audit.json`
  - `overall_verdict = broader_bull_cohort_recalibration_candidate`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`
- `data/leaderboard_feature_profile_probe.json`
  - `leaderboard_selected_profile = core_only`
  - `train_selected_profile = core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `support_governance_route = exact_live_bucket_proxy_available`
- 判讀：profile split 仍是治理背景；本輪主變化不是 profile，而是 q15 bucket boundary evidence 已落成 machine-readable artifact。

### Breaker / source blockers
- `data/circuit_breaker_audit.json`
  - `root_cause.verdict = mixed_horizon_false_positive`
  - mixed scope：**streak=142 / recent50 win_rate=0.00 / 全部 240m**
  - aligned 1440m scope：**release_ready=true**
- `fin_netflow`
  - coverage：**0.0%**
  - latest status：**auth_missing**
  - archive_window_coverage：**0.0% (0/1714)**
- 判讀：breaker 治理維持正常；`fin_netflow` 仍是外部憑證 blocker，與 q15 root cause 分開治理。

---

## 目前有效問題

### P1. q15 exact bucket 仍未達 deployment support，runtime 仍被 blocker 壓成 0 層
**現象**
- `current_live_structure_bucket = CAUTION|structure_quality_caution|q15`
- `current_live_structure_bucket_rows = 0`
- `support_route.verdict = exact_bucket_missing_proxy_reference_only`
- `execution_guardrail_reason = unsupported_exact_live_structure_bucket_blocks_trade`

**判讀**
- q15 blocker 仍在；
- 本輪沒有放寬 gate，而是把 blocker 的最小可修補原因拆成可 machine-read artifact。

---

### P1. q15 root cause 已收斂為 boundary sensitivity candidate，但尚未通過 legality / replay 驗證
**現象**
- `q15_bucket_root_cause.verdict = boundary_sensitivity_candidate`
- `candidate_patch_feature = feat_4h_bb_pct_b`
- `gap_to_q35_boundary = 0.0116`
- `near_boundary_rows = 2`

**判讀**
- 這代表 q15↔q35 boundary review 可以列入候選，但仍只是 **research path**；
- 下一輪必須做 replay / counterfactual 驗證，回答 boundary review 是否真的能增加 exact-lane current bucket rows，且不能把 0-row blocker 假裝成已解。

---

### P1. `feat_4h_bias50` 仍是 floor gap 最佳單點 component，但在 support 未達標前只能當 calibration research
**現象**
- `floor_cross_legality.best_single_component = feat_4h_bias50`
- `best_single_component_required_score_delta = 0.3827`
- `legal_to_relax_runtime_gate = false`

**判讀**
- bias50 仍是 floor-gap 主角；
- 但本輪主決策已更精確：**先驗 boundary / bucket repair 是否真的產生 exact support，再回頭談 bias50 deploy 級 patch**。

---

### P1. production / leaderboard profile split 仍存在，但優先序低於 q15 exact-bucket repair
**現象**
- global shrinkage winner：`core_only`
- production train profile：`core_plus_macro_plus_4h_structure_shift`
- `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`

**判讀**
- split 仍是治理事實；
- 但本輪主 blocker 已更具體化為 q15 boundary / exact support 問題，不應把主帶寬拉回 profile 收斂。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1714)**

**判讀**
- 仍是外部憑證 blocker；
- 不可與 q15 / boundary review / profile split 混寫。

---

## 本輪已清掉的問題

### RESOLVED. q15 0-row blocker 只有籠統文字敘述，沒有 machine-readable root-cause artifact
**修前**
- 文件只停留在 `same_lane_shifted_to_neighbor_bucket` 敘述；
- heartbeat 無法 machine-read 判斷到底該優先做 boundary review、structure scoring，還是 projection 修復。

**本輪 patch + 證據**
- `scripts/hb_q15_bucket_root_cause.py`
  - 新增 q15 exact-bucket root-cause artifact
- `scripts/hb_parallel_runner.py`
  - fast heartbeat 自動刷新 q15 root-cause artifact 並寫入 summary
- `python -m pytest tests/test_q15_bucket_root_cause.py tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py -q`
  - **26 passed**
- `python scripts/hb_parallel_runner.py --fast --hb 1012`
  - `q15_bucket_root_cause.verdict = boundary_sensitivity_candidate`
  - `q15_bucket_root_cause.candidate_patch_feature = feat_4h_bb_pct_b`
  - `q15_bucket_root_cause.exact_live_lane.near_boundary_rows = 2`

**狀態**
- **已修復**：q15 blocker 現在有 machine-readable root-cause artifact，可直接作為下一輪 Step 0.5 的輸入。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 q15 0-row blocker 從籠統文字收斂成 machine-readable root-cause artifact。** ✅
2. **驗證 q15 support route / floor-cross legality / root-cause artifact 能同時存在且不互相漂移。** ✅
3. **維持 breaker / profile split / fin_netflow auth blocker 的次級治理定位。** ✅

### 本輪不做
- 不直接 relax q15 runtime gate；
- 不把 q35 generic scaling 重新包裝成主 blocker；
- 不在沒有 replay 驗證前直接修改 q15↔q35 boundary。

---

## Next gate

- **Next focus:**
  1. 針對 `q15_bucket_root_cause.verdict = boundary_sensitivity_candidate`，做 **q15↔q35 boundary replay / counterfactual**，回答 boundary review 是否真的能增加 exact-lane current bucket rows；
  2. 針對 `candidate_patch_feature = feat_4h_bb_pct_b` 做最小反事實驗證，確認它是 boundary candidate 還是其實只是 structure scoring proxy；
  3. 維持 `profile_split / fin_netflow auth blocker / mixed-horizon breaker false-positive` 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q15 boundary replay / exact-lane row generation** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答：boundary review 是否真的增加 exact-lane current bucket rows，或只是把 blocker 假裝成已解；
  3. `q15_support_audit`、`q15_bucket_root_cause`、`leaderboard_feature_profile_probe` 對 `support_governance_route / exact_bucket_proxy_rows / runtime blocker` 的描述必須持續一致。

- **Fallback if fail:**
  - 若 boundary replay 無法增加 exact-lane current bucket rows，下一輪不得繼續把主焦點放在 boundary review，必須降級回 structure component scoring / support accumulation；
  - 若沒有 exact support 證據就直接 relax runtime gate，視為風控 regression；
  - 若 next run 仍沒有 boundary replay 或 component counterfactual 證據，升級為 q15 exact-bucket blocker。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 q15 boundary / bucket contract 被正式擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1012_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q15_support_audit.json`
     - `data/q15_bucket_root_cause.json`
     - `data/leaderboard_feature_profile_probe.json`
     - `data/bull_4h_pocket_ablation.json`
  3. 若同時成立：
     - `q15_support_audit.support_route.verdict = exact_bucket_missing_proxy_reference_only`
     - `q15_bucket_root_cause.verdict = boundary_sensitivity_candidate`
     - `q15_bucket_root_cause.current_live.gap_to_q35_boundary <= 0.02`
     - `q15_bucket_root_cause.exact_live_lane.near_boundary_rows > 0`
     - `live_predict_probe.allowed_layers = 0`
     則下一輪不得再回 generic q35 / breaker；必須直接處理 **q15 boundary replay / feat_4h_bb_pct_b counterfactual / exact-lane row generation**。
