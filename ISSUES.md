# ISSUES.md — Current State Only

_最後更新：2026-04-15 08:59 UTC — Heartbeat #1013（本輪新增 q15 boundary replay artifact，確認 q15 邊界修補已不是主路徑；主 blocker 已收斂到 exact-supported q35 lane 的 trade-floor / bias50 component 問題。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 做 q15 boundary replay / counterfactual artifact；
  2. 驗 `feat_4h_bb_pct_b` 是否真為 candidate patch feature；
  3. 維持 `profile_split / fin_netflow auth blocker / breaker false-positive` 零漂移治理。
- **Success gate**
  1. 至少留下 1 個與 q15 boundary replay 或 exact-lane row generation 直接相關的 patch / artifact / verify；
  2. machine-read 回答 boundary review 是否真的增加 exact-lane current bucket rows；
  3. `q15_support_audit / q15_bucket_root_cause / leaderboard_feature_profile_probe` 對 support route / runtime blocker 描述不得漂移。
- **Fallback if fail**
  - 若 boundary replay 無法增加 exact-lane current bucket rows，就不得再把主焦點放在 boundary review；
  - 若沒有 exact support 證據就 relax runtime gate，視為風控 regression；
  - 若沒有 replay / component artifact，升級為 q15 exact-bucket blocker。

### 本輪承接結果
- **已處理**
  - 新增 `scripts/hb_q15_boundary_replay.py`，產出：
    - `data/q15_boundary_replay.json`
    - `docs/analysis/q15_boundary_replay.md`
  - `scripts/hb_parallel_runner.py` 已接入 q15 boundary replay artifact。
  - 新增測試：
    - `tests/test_q15_boundary_replay.py`
    - `tests/test_hb_parallel_runner.py`（新增 q15 replay diagnostics / runner order 覆蓋）
  - `ARCHITECTURE.md` 已補 `#1013 q15 boundary-replay contract`。
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_q15_boundary_replay.py tests/test_q15_bucket_root_cause.py tests/test_hb_parallel_runner.py -q` → **26 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1013` → **通過**
- **本輪 machine-read 結論**
  - `q15_support_audit.support_route.verdict = exact_bucket_supported`
  - `q15_bucket_root_cause.verdict = current_row_already_above_q35_boundary`
  - `q15_boundary_replay.verdict = boundary_replay_not_applicable`
  - `q15_boundary_replay.component_counterfactual.verdict = bucket_proxy_only_not_trade_floor_fix`
  - `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`
- **本輪明確不做**
  - 不再把 q15 boundary review 當 deployment patch；
  - 不把 `feat_4h_bb_pct_b` 單獨包裝成 trade-floor 修復；
  - 不把 `fin_netflow` auth blocker 混進 q35/q15 component 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_q15_boundary_replay.py`
  - `scripts/hb_parallel_runner.py`
  - `tests/test_q15_boundary_replay.py`
  - `tests/test_hb_parallel_runner.py`
  - `ARCHITECTURE.md`
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_q15_boundary_replay.py tests/test_q15_bucket_root_cause.py tests/test_hb_parallel_runner.py -q` → **26 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1013`
- **已刷新 artifacts**
  - `data/heartbeat_1013_summary.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/q35_scaling_audit.json`
  - `data/q15_support_audit.json`
  - `data/q15_bucket_root_cause.json`
  - `data/q15_boundary_replay.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`
  - `docs/analysis/q15_boundary_replay.md`

### 資料 / 新鮮度 / canonical target
- Heartbeat #1013：
  - Raw / Features / Labels：**21589 / 13018 / 43348**
  - 本輪增量：**+1 raw / +1 feature / +3 labels**
  - canonical target `simulated_pyramid_win`：**0.5756**
  - 240m labels：**21737 rows / target_rows 12815 / lag_vs_raw 約 3.4h**
  - 1440m labels：**12526 rows / target_rows 12526 / lag_vs_raw 約 23.1h**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**19/30 pass**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 6/8**
- drift primary window：**recent 250**
  - alerts：`label_imbalance`, `regime_concentration`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 94.4%**
  - win_rate：**0.9680**
  - avg_quality：**0.6567**
  - avg_pnl：**+0.0206**
  - avg_drawdown_penalty：**0.0410**
- 判讀：canonical lane 健康；本輪主 blocker 不是 drift，而是 **exact-supported q35 lane 仍卡在 trade floor 之下**。

### Live contract / q35 / q15 現況
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - entry_quality_label：**D**
  - decision_quality_label：**B**
  - decision_quality scope：**`regime_label+regime_gate+entry_quality_label`**（rows=`76`）
  - expected_win_rate / quality：**0.9605 / 0.6528**
  - allowed_layers：**0 → 0**
  - `allowed_layers_reason = entry_quality_below_trade_floor`
- `data/q35_scaling_audit.json`
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`
- `data/q15_support_audit.json`
  - `support_route.verdict = exact_bucket_supported`
  - `current_live_structure_bucket = CAUTION|structure_quality_caution|q35`
  - `current_live_structure_bucket_rows = 76`
  - `floor_cross_legality.best_single_component = feat_4h_bias50`
  - `floor_cross_legality.remaining_gap_to_floor = 0.1918`
- `data/q15_bucket_root_cause.json`
  - `verdict = current_row_already_above_q35_boundary`
  - `candidate_patch_type = support_accumulation`
  - `candidate_patch_feature = feat_4h_bb_pct_b`
- `data/q15_boundary_replay.json`
  - `verdict = boundary_replay_not_applicable`
  - `component_counterfactual.verdict = bucket_proxy_only_not_trade_floor_fix`
  - `component_counterfactual.allowed_layers_after = 0`
- 判讀：**exact support 已回來，q15 邊界修補已失效；現在要修的是 q35 exact-supported lane 的 entry floor / bias50 component，不是 boundary。**

### Profile split / governance / blockers
- `data/leaderboard_feature_profile_probe.json`
  - `leaderboard_selected_profile = core_plus_macro`
  - `train_selected_profile = core_plus_macro_plus_4h_structure_shift`
  - `global_recommended_profile = core_only`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
  - `support_governance_route = exact_live_bucket_supported`
- `data/bull_4h_pocket_ablation.json`
  - `bull_exact_live_lane_proxy_rows = 424`
  - `bull_live_exact_lane_bucket_proxy_rows = 161`
  - `current_live_structure_bucket_rows = 76`
- `fin_netflow`
  - coverage：**0.0%**
  - latest status：**auth_missing**
  - archive_window_coverage：**0.0% (0/1715)**
- 判讀：profile split 現在是**後 exact-support 時代的治理停滯**，不是 q15 support 缺失；`fin_netflow` 仍是獨立外部 auth blocker。

---

## 目前有效問題

### P1. exact-supported q35 lane 仍卡在 trade floor 下方，主 blocker 已是 `feat_4h_bias50` component / formula review
**現象**
- `current_live_structure_bucket_rows = 76`（support 已足）
- `entry_quality = 0.3582`，`allowed_layers = 0`
- `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`
- `q15_support_audit.floor_cross_legality.best_single_component = feat_4h_bias50`
- `required_score_delta_to_cross_floor = 0.6393`

**判讀**
- support blocker 已解；
- 現在真正卡住的是 **exact-supported lane 的 floor-gap / bias50 scoring**；
- 下一輪必須直接做 bias50 component experiment / formula review，而不是再修 q15 boundary。

---

### P1. `feat_4h_bb_pct_b` 只能當 bucket proxy，不是 deployable floor fix
**現象**
- `q15_bucket_root_cause.candidate_patch_feature = feat_4h_bb_pct_b`
- `q15_boundary_replay.component_counterfactual.verdict = bucket_proxy_only_not_trade_floor_fix`
- `q15_boundary_replay.component_counterfactual.allowed_layers_after = 0`

**判讀**
- `feat_4h_bb_pct_b` 可以幫助 bucket 判讀 / support 語義；
- 但就算補到跨 q35，仍無法讓 entry quality 跨過 floor；
- 下一輪不得把它包裝成 runtime 放行 patch。

---

### P1. post-threshold profile governance stalled：leaderboard / train / global shrinkage 仍三套語義
**現象**
- leaderboard：`core_plus_macro`
- train：`core_plus_macro_plus_4h_structure_shift`
- global shrinkage：`core_only`
- `dual_profile_state = post_threshold_profile_governance_stalled`

**判讀**
- 這已不是 exact-support 缺失，而是 **support 恢復後仍未完成 profile 收斂**；
- 但在 trade-floor component 未修前，優先序仍低於 bias50 floor-gap 修補。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `coverage = 0.0%`
- `latest status = auth_missing`
- `archive_window_coverage = 0.0% (0/1715)`

**判讀**
- 仍是外部憑證 blocker；
- 不可與 q35 exact-supported lane 或 bias50 formula review 混寫。

---

## 本輪已清掉的問題

### RESOLVED. q15 boundary replay 是否仍是主修補路徑不清楚
**修前**
- 上輪仍把 q15 boundary replay / `feat_4h_bb_pct_b` counterfactual 當主焦點；
- 尚未 machine-read 驗證 boundary review 是真修補還是已經失效。

**本輪 patch + 證據**
- `scripts/hb_q15_boundary_replay.py`
- `scripts/hb_parallel_runner.py`
- `python -m pytest tests/test_q15_boundary_replay.py tests/test_q15_bucket_root_cause.py tests/test_hb_parallel_runner.py -q` → **26 passed**
- `python scripts/hb_parallel_runner.py --fast --hb 1013`
  - `q15_support_audit.support_route.verdict = exact_bucket_supported`
  - `q15_bucket_root_cause.verdict = current_row_already_above_q35_boundary`
  - `q15_boundary_replay.verdict = boundary_replay_not_applicable`

**狀態**
- **已修復**：q15 boundary replay 是否還值得當主 patch，現在已有 machine-readable 結論；下一輪不得再回 boundary 敘事。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 q15 boundary replay / component counterfactual 正式 machine-read 化。** ✅
2. **確認 q15 support 已恢復、主 blocker 已從 support 轉移到 q35 lane 的 trade-floor / bias50。** ✅
3. **維持 profile split / fin_netflow auth blocker / breaker false-positive 的次級治理定位。** ✅

### 本輪不做
- 不再修 q15↔q35 boundary；
- 不直接 relax runtime gate；
- 不把 `feat_4h_bb_pct_b` 當 trade-floor patch。

---

## Next gate

- **Next focus:**
  1. 對 `feat_4h_bias50` 做 **exact-supported q35 lane component experiment / formula review**，回答它是否能在不破壞 guardrail 的前提下讓 entry_quality 跨過 floor；
  2. 驗證 `core_plus_macro` / `core_plus_macro_plus_4h_structure_shift` / `core_only` 三套 profile 語義在 exact-supported lane 下該如何收斂；
  3. 維持 `q15_boundary_replay / q15_support_audit / leaderboard_feature_profile_probe / fin_netflow auth blocker` 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **bias50 formula review 或 exact-supported q35 lane component experiment** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答：bias50 experiment 是否讓 entry_quality / allowed_layers 真正改善，還是仍只是 calibration 研究；
  3. `q15_boundary_replay` 必須持續證明 boundary 不是主路徑，且 `feat_4h_bb_pct_b` 仍不得被誤寫成 floor fix。

- **Fallback if fail:**
  - 若 bias50 experiment 仍無法把 entry_quality 拉過 floor，下一輪不得繼續只調 bias50；必須升級成 base-mix / pulse / support accumulation 聯合問題；
  - 若沒有 exact-supported q35 lane 的真 patch / verify，又回去談 q15 boundary，視為 regression；
  - 若沒有 exact support 證據就 relax runtime gate，視為風控 regression。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 bias50 formula review contract 被正式擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1013_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
     - `data/q15_bucket_root_cause.json`
     - `data/q15_boundary_replay.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若同時成立：
     - `q15_support_audit.support_route.verdict = exact_bucket_supported`
     - `q15_bucket_root_cause.verdict = current_row_already_above_q35_boundary`
     - `q15_boundary_replay.verdict = boundary_replay_not_applicable`
     - `q15_boundary_replay.component_counterfactual.verdict = bucket_proxy_only_not_trade_floor_fix`
     - `live_predict_probe.allowed_layers = 0`
     則下一輪不得再回 q15 boundary repair；必須直接處理 **bias50 formula review / exact-supported q35 component experiment / profile governance 收斂**。
