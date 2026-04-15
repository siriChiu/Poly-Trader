# ISSUES.md — Current State Only

_最後更新：2026-04-15 05:02 UTC — Heartbeat #1005（本輪把 q35/bias50 問題從「bull cohort segmented calibration 候選」正式推進到 **exact-lane formula review + runtime conservative score 已落地**：當 current `feat_4h_bias50` 已回到 exact-lane p90 內時，predictor / q35 audit 會套用 `exact_lane_elevated_within_p90` 的保守非零分數，而不是繼續把 bias50 壓成 0。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪（#1004）要求本輪處理
- **Next focus**：
  1. 以 `bull_all` 作 reference cohort，落實 `feat_4h_bias50` 的 piecewise / quantile calibration；
  2. 維持 `q35_scaling_audit`、`profile_split`、`support_blocker_state`、`proxy_boundary_verdict` 的零漂移治理；
  3. 持續把 `fin_netflow` 當外部 source auth blocker 管理。
- **Success gate**：
  1. 至少留下 1 個與 **bias50 piecewise / quantile calibration** 直接相關的 patch / artifact / verify；
  2. 若 current bull q35 lane 仍是 `CAUTION / D / 0-layer`，`q35_scaling_audit` 必須再次輸出一致結論，且 docs / summary / issue 不得漂移；
  3. 若要主張 relax runtime gate，必須先證明 current 值已回到 exact lane 可接受區間，而不是只看 broader bull cohort。
- **Fallback if fail**：
  - 若 `q35_scaling_audit` 缺 `segmented_calibration` 或 `reference_cohort`，視為 governance regression；
  - 若有人再次直接放寬 q35 gate 或下修 `trade_floor`，卻沒有新的 calibration patch / verify，視為 contract regression；
  - 若 `profile_split` / exact-supported 狀態再漂移，視為 blocker；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

### 本輪承接結果
- **已處理**：
  - `model/q35_bias50_calibration.py`
    - 新增 **exact-lane formula-review** 分支；
    - 當 `overall_verdict=bias50_formula_may_be_too_harsh`、`status=formula_review_required`、且 current `bias50` 位於 exact-lane `p75~p90` 內時，改用 `segment=exact_lane_elevated_within_p90` 的保守非零 score，而不是 legacy 0 分。
  - `scripts/hb_q35_scaling_audit.py`
    - 當 current `bias50` 已回到 exact-lane `p90` 內時，不再繼續把它判成 broader bull segmentation；
    - 改寫為 `overall_verdict=bias50_formula_may_be_too_harsh`、`segmented_calibration.status=formula_review_required`。
  - `tests/test_api_feature_history_and_predictor.py`
    - 新增 exact-lane formula-review calibration regression test。
  - `tests/test_hb_parallel_runner.py`
    - 新增 formula-review runtime-active regression test。
  - `ARCHITECTURE.md`
    - 同步 q35 contract 的 **exact-lane formula-review** 分支。
- **驗證已完成**：
  - `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q` → **50 passed**
  - `source venv/bin/activate && python scripts/hb_q35_scaling_audit.py` → **通過**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1005` → **通過**
- **本輪明確答案**：
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`
  - `segmented_calibration.status = formula_review_required`
  - `segmented_calibration.recommended_mode = exact_lane_formula_review`
  - `segmented_calibration.runtime_contract_status = piecewise_runtime_active`
  - `piecewise_runtime_preview.segment = exact_lane_elevated_within_p90`
  - current `feat_4h_bias50 = 3.2478`
  - exact lane：`p75 = 3.0207`、`p90 = 3.4106`、`current_bias50_percentile = 0.8763`
  - live bias50 score：`0.0 → 0.1334`
  - live entry quality：`0.4826 → 0.5238`
  - 仍未達 trade floor：`trade_floor_gap = -0.0262`
- **本輪明確不做**：
  - 不直接放寬 q35 gate；
  - 不直接降低 `trade_floor`；
  - 不把 exact-lane formula review 誤寫成「已可進場」；
  - 不把 `fin_netflow` auth blocker 混進 q35 根因。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `model/q35_bias50_calibration.py`
  - `scripts/hb_q35_scaling_audit.py`
  - `tests/test_api_feature_history_and_predictor.py`
  - `tests/test_hb_parallel_runner.py`
  - `ARCHITECTURE.md`
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q` → **50 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_q35_scaling_audit.py`
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1005`
- **已刷新 artifacts**
  - `data/heartbeat_1005_summary.json`
  - `data/q35_scaling_audit.json`
  - `docs/analysis/q35_scaling_audit.md`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `model/ic_signs.json`

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #1005：
  - Raw / Features / Labels：**21578 / 13007 / 43185**
  - 本輪增量：**+1 raw / +1 feature / +1 label**（summary 最終落點）
  - canonical target `simulated_pyramid_win`：**0.5785**
  - 240m labels：**21598 rows / target_rows 12676 / lag_vs_raw 約 3.2h**
  - 1440m labels：**12502 rows / target_rows 12502 / lag_vs_raw 約 23.4h**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**20/30 pass**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 6/8**
- primary drift window：**recent 100**
  - alerts：`constant_target`, `regime_concentration`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 100%**
  - win_rate：**1.0000**
  - avg_quality：**0.6796**
  - avg_pnl：**+0.0216**
  - avg_drawdown_penalty：**0.0367**
- 判讀：canonical recent window 仍健康；本輪主 blocker 已從「bull cohort segmented calibration 尚未實作」轉為 **exact-lane formula review 已落地，但仍差 0.0262 才跨過 trade floor**。

### Train / leaderboard / live contract
- `model/last_metrics.json`
  - `feature_profile = core_plus_macro_plus_4h_structure_shift`
  - Train=`67.5%`
  - CV=`71.7% ± 9.9pp`
  - `n_features = 21`
- `data/feature_group_ablation.json`
  - `recommended_profile = core_only`
  - `profile_role.role = global_shrinkage_winner`
- `data/bull_4h_pocket_ablation.json`
  - `bull_all.recommended_profile = core_plus_macro_plus_4h_structure_shift`
  - `production_profile_role.role = bull_exact_supported_production_profile`
- `data/leaderboard_feature_profile_probe.json`
  - `train_selected_profile = leaderboard_selected_profile = core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = aligned`
  - `profile_split.verdict = dual_role_required`
  - `support_blocker_state = exact_live_bucket_supported`
  - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.4516**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.5238 (D)**
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `allowed_layers = 0`
  - chosen scope：**`regime_label+entry_quality_label` / sample_size=197**
  - expected win rate：**0.9848**
  - expected pyramid quality：**0.6713**
- 判讀：live contract、profile split、exact-supported semantics 仍穩定；**bias50 已不再是 0 分，但整體 entry quality 仍未跨 0.55 floor**。

### Q35 / bias50 calibration 診斷
- `data/q35_scaling_audit.json`
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`
  - `segmented_calibration.status = formula_review_required`
  - `segmented_calibration.recommended_mode = exact_lane_formula_review`
  - `segmented_calibration.runtime_contract_status = piecewise_runtime_active`
  - `piecewise_runtime_preview.segment = exact_lane_elevated_within_p90`
  - exact lane：`current_bias50_percentile = 0.8763`、`percentile_band = elevated_but_within_p90`
  - same-gate same-quality reference：`p90 = 3.4106`、`current_bias50_percentile = 0.8829`
  - `gate_allow_only_changes_layers = false`
  - `required_bias50_cap_for_floor = 1.2965`
- 判讀：**本輪已證明 runtime 公式分支存在且生效**；剩餘問題不是「有沒有 calibration」，而是 **目前保守 score 仍不足以跨過 trade floor**。

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. q35/bias50 已進入 **exact-lane formula review** 階段，但 current bull live path 仍差 `0.0262` 才過 floor
**現象**
- current live row：
  - `regime_gate = CAUTION`
  - `entry_quality = 0.5238`
  - `entry_quality_label = D`
  - `allowed_layers = 0`
  - `allowed_layers_reason = entry_quality_below_trade_floor`
- q35 audit：
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `segmented_calibration.status = formula_review_required`
  - `segmented_calibration.runtime_contract_status = piecewise_runtime_active`

**關鍵證據**
- current `feat_4h_bias50 = 3.2478`
- exact lane：`p75 = 3.0207`、`p90 = 3.4106`
- runtime bias50 score：`0.0 → 0.1334`
- `trade_floor_gap = -0.0262`
- `required_bias50_cap_for_floor = 1.2965`

**判讀**
- 這題已不是「runtime 尚未吃到公式」；
- 也不是「應直接回到 broader bull segmentation」；
- **真正待做的是拆解剩餘 0.0262 gap：判斷下一步該繼續微調 exact-lane bias50 score，還是轉去修 nose / structure mix。**

---

### P1. current bull live path 的剩餘 blocker 已從 pure bias50 轉成 **entry-quality 組成拆解問題**
**現象**
- `bias50_calibration.applied = true`
- `bias50 weighted_contribution = 0.0534`
- 但最終 `entry_quality = 0.5238 < 0.55`
- current 組成：
  - `feat_nose weighted_contribution = 0.0927`
  - `feat_pulse weighted_contribution = 0.2687`
  - `feat_ear weighted_contribution = 0.1493`
  - `structure_quality = 0.4025`

**判讀**
- bias50 已從 hard-zero 解除；
- 下一輪不能再只盯 q35 audit verdict，必須直接比較 **bias50 再加多少才合理** 與 **其他 entry-quality components 是否更值得修**。

---

### P1. global shrinkage winner 與 production bull profile 的雙軌治理仍需維持零漂移
**現象**
- `global_recommended_profile = core_only`
- `train_selected_profile = leaderboard_selected_profile = core_plus_macro_plus_4h_structure_shift`
- `profile_split.verdict = dual_role_required`
- `dual_profile_state = aligned`

**判讀**
- 這不是 parity blocker；
- 這是**刻意保留的雙軌治理**：global winner 管 shrinkage，production winner 管 bull exact-supported live lane。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1705)**

**判讀**
- 仍是**外部憑證 blocker**，不是 q35 / formula review 根因。

---

## 本輪已清掉的問題

### RESOLVED. q35 runtime 仍被描述成「尚未吃到 piecewise 公式」
**修前**
- 文件與治理語義仍把 q35 問題寫成「bull cohort segmented calibration 待落地」；
- 但 current row 其實已回到 exact-lane p90 內，真實 blocker 是 legacy bias50 線性公式仍給 0 分。

**本輪 patch + 證據**
- `model/q35_bias50_calibration.py`
  - 新增 `segment=exact_lane_elevated_within_p90`
  - 支援 `status=formula_review_required` / `recommended_mode=exact_lane_formula_review`
- `scripts/hb_q35_scaling_audit.py`
  - current row 回到 exact-lane p90 內時，改寫為 `overall_verdict=bias50_formula_may_be_too_harsh`
- `python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q`
  - **50 passed**
- `python scripts/hb_q35_scaling_audit.py`
  - `runtime_contract_status = piecewise_runtime_active`
- `python scripts/hb_parallel_runner.py --fast --hb 1005`
  - `data/live_predict_probe.json` 顯示：
    - `bias50_calibration.applied = true`
    - `bias50 score = 0.1334`
    - `entry_quality = 0.5238`

**狀態**
- **已修復**：runtime 現在不再把 exact-lane p90 內的高側 row 一律壓成 bias50=0；heartbeat 也不再把這題錯報成「runtime 未吃到新公式」。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 q35/bias50 問題從 broader bull segmentation 轉成 exact-lane formula review。** ✅
2. **讓 predictor / q35 audit 對 exact-lane 高側 row 真正套用保守非零 bias50 score。** ✅
3. **保留 `allowed_layers = 0`，避免把 formula review 誤解為 gate 已放寬。** ✅

### 本輪不做
- 不直接放寬 q35 gate；
- 不直接降低 `trade_floor`；
- 不把 `fin_netflow` auth blocker 混進 q35 根因；
- 不把 `entry_quality = 0.5238` 誤包裝成可交易。

---

## Next gate

- **Next focus:**
  1. 量化 `entry_quality` 剩餘 **0.0262 gap** 的來源，決定應繼續微調 exact-lane bias50 score，或轉去修 `nose / structure_quality`；
  2. 維持 `q35_scaling_audit`、`profile_split`、`support_blocker_state`、`proxy_boundary_verdict` 的零漂移治理；
  3. 持續把 `fin_netflow` 當外部 source auth blocker 管理。

- **Success gate:**
  1. next run 必須留下至少一個與 **剩餘 0.0262 trade-floor gap 根因拆解** 直接相關的 patch / artifact / verify；
  2. 若 current bull q35 lane 仍是 `CAUTION / D / 0-layer`，必須明確回答「差距主要來自 bias50 還是其他 entry-quality component」，不能再只重述 `formula_review_required`；
  3. 若要主張 relax runtime gate，必須先證明新 patch 沒有破壞 `allowed_layers=0` 的 guardrail 語義，且 entry quality 真正越過 `0.55`。

- **Fallback if fail:**
  - 若下一輪又把 q35 問題退回 `broader_bull_cohort_recalibration_candidate`，但 current 仍位於 exact-lane p90 內，視為 governance regression；
  - 若 bias50 score 被放大到跨過 floor，卻沒有對應 artifact / verify / guardrail 證據，視為 contract regression；
  - 若 `profile_split` / exact-supported 狀態再漂移，視為 blocker；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 exact-lane formula review 再擴充成新的 runtime rule）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1005_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q35_scaling_audit.json`
     - `docs/analysis/q35_scaling_audit.md`
     - `data/feature_group_ablation.json`
     - `data/bull_4h_pocket_ablation.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若 `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`、`segmented_calibration.status = formula_review_required`、`piecewise_runtime_preview.applied = true`、`live_predict_probe.entry_quality = 0.5238 ± 誤差`、`allowed_layers_reason = entry_quality_below_trade_floor`、`support_blocker_state = exact_live_bucket_supported` 同時成立，下一輪不得再把焦點放回「有沒有 q35 piecewise calibration」；必須直接拆解剩餘 `0.0262` gap 是 **bias50 最後一哩** 還是 **其他 entry-quality component**。