# ISSUES.md — Current State Only

_最後更新：2026-04-15 05:35 UTC — Heartbeat #1006（本輪把「剩餘 trade-floor gap 到底卡在 bias50 還是其他 component」從口頭要求變成 machine-readable artifact：`live_decision_quality_drilldown` 現在會輸出 `component_gap_attribution`，直接指出目前 live bull path 的最佳單點修補候選是 `feat_4h_bias50`。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪（#1005）要求本輪處理
- **Next focus**：
  1. 量化剩餘 `0.0262` trade-floor gap 的 component root cause；
  2. 維持 `q35_scaling_audit`、`profile_split`、`support_blocker_state`、`proxy_boundary_verdict` 零漂移；
  3. 持續把 `fin_netflow` 當外部 source auth blocker 管理。
- **Success gate**：
  1. 至少留下 1 個與 `entry-quality` 剩餘 gap attribution 直接相關的 patch / artifact / verify；
  2. 若 bull q35 lane 仍是 `CAUTION / D / 0-layer`，必須明確回答「bias50 還差多少、其他 components 是否更關鍵」；
  3. 若要主張 relax runtime gate，必須證明 `allowed_layers=0` guardrail 沒被破壞且 `entry_quality >= 0.55`。
- **Fallback if fail**：
  - 不得退回只談「q35 calibration 有沒有接上」；
  - 不得無 artifact 就放寬 q35 gate / trade_floor；
  - 若 exact-supported / profile split 再漂移，升級為 blocker。

### 本輪承接結果
- **已處理**：
  - `scripts/live_decision_quality_drilldown.py`
    - 新增 `component_gap_attribution`，machine-read：
      - `remaining_gap_to_floor`
      - `best_single_component`
      - `best_single_component_required_score_delta`
      - `single_component_floor_crossers`
      - `bias50_floor_counterfactual`
    - markdown 同步新增「Gap attribution（哪個 component 真正在卡 floor）」段落。
  - `scripts/hb_parallel_runner.py`
    - fast heartbeat summary 現在會帶出 `live_decision_drilldown.remaining_gap_to_floor / best_single_component / best_single_component_required_score_delta`。
  - `tests/test_live_decision_quality_drilldown.py`
    - 鎖住 gap attribution：當前案例必須辨識 `feat_4h_bias50` 為最佳單點修補候選。
  - `tests/test_hb_parallel_runner.py`
    - 鎖住 summary 持久化新的 drilldown 欄位。
- **驗證已完成**：
  - `source venv/bin/activate && python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q` → **18 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1006` → **通過**
- **本輪明確答案**：
  - 目前 live bull path：`bull / CAUTION / D / 0-layer`
  - current `entry_quality = 0.4658`
  - `trade_floor_gap = -0.0842`
  - `component_gap_attribution.remaining_gap_to_floor = 0.0842`
  - `component_gap_attribution.best_single_component = feat_4h_bias50`
  - `best_single_component_required_score_delta = 0.2807`
  - `bias50 fully relaxed -> entry_quality ≈ 0.7807 / layers ≈ 2`
- **本輪明確不做**：
  - 不直接放寬 q35 gate；
  - 不直接降低 `trade_floor`；
  - 不把單次 `bias50` counterfactual 誤包裝成「現在可交易」；
  - 不把 `fin_netflow` auth blocker 混入 bull live path 根因。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/live_decision_quality_drilldown.py`
  - `scripts/hb_parallel_runner.py`
  - `tests/test_live_decision_quality_drilldown.py`
  - `tests/test_hb_parallel_runner.py`
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q` → **18 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1006`
- **已刷新 artifacts**
  - `data/heartbeat_1006_summary.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `docs/analysis/live_decision_quality_drilldown.md`
  - `data/q35_scaling_audit.json`
  - `docs/analysis/q35_scaling_audit.md`
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`
  - `model/ic_signs.json`

### 資料 / 新鮮度 / canonical target
- Heartbeat #1006：
  - Raw / Features / Labels：**21580 / 13009 / 43193**
  - 本輪增量：**+1 raw / +1 feature / +4 labels**
  - canonical target `simulated_pyramid_win`：**0.5784**
  - 240m labels：**21605 rows / target_rows 12683 / lag_vs_raw 約 3.0h**
  - 1440m labels：**12503 rows / target_rows 12503 / lag_vs_raw 約 23.4h**
  - recent raw age：**約 0.6 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**20/30 pass**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 6/8**
- drift primary window：**recent 100**
  - alerts：`constant_target`, `regime_concentration`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 100%**
  - win_rate：**1.0000**
  - avg_quality：**0.6800**
  - avg_pnl：**+0.0216**
  - avg_drawdown_penalty：**0.0363**
- 判讀：canonical target 與資料新鮮度仍健康；本輪主問題不是 drift，而是 **bull live path 的 current structure bucket 從 q35 漂到 q15，導致 exact live bucket 支撐重新歸零**。

### Live contract / gap attribution / governance
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.5498**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.4658 (D)**
  - `allowed_layers = 0`
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `execution_guardrail_reason = unsupported_exact_live_structure_bucket_blocks_trade`
  - chosen scope：**`regime_label+entry_quality_label` / sample_size=197**
  - expected win rate：**0.9848**
  - expected pyramid quality：**0.6714**
- `data/live_decision_quality_drilldown.json`
  - `remaining_gap_to_floor = 0.0842`
  - `best_single_component = feat_4h_bias50`
  - `best_single_component_required_score_delta = 0.2807`
  - `single_component_floor_crossers = [feat_4h_bias50]`
  - `bias50 fully relaxed -> entry≈0.7807 / layers≈2`
- 判讀：**本輪已正式回答「哪個 component 最該修」：是 `feat_4h_bias50`，不是 nose / pulse / ear，也不是單獨某一個 structure component。**

### Q35 / bull lane / support 狀態
- `data/q35_scaling_audit.json`
  - `overall_verdict = broader_bull_cohort_recalibration_candidate`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`
  - `segmented_calibration.status = segmented_calibration_required`
  - `segmented_calibration.recommended_mode = piecewise_quantile_calibration`
  - `segmented_calibration.runtime_contract_status = piecewise_runtime_active`
  - `reference_cohort = same_gate_same_quality`
  - `exact_bias50_pct = 1.0`
  - `bull_all_bias50_pct = 0.5049`
- `data/bull_4h_pocket_ablation.json`
  - `current_live_structure_bucket = CAUTION|structure_quality_caution|q15`
  - `current_live_structure_bucket_rows = 0`
  - `support_blocker_state = exact_lane_proxy_fallback_only`
  - `exact_bucket_root_cause = same_lane_shifted_to_neighbor_bucket`
  - `supported_neighbor_buckets = [CAUTION|structure_quality_caution|q35]`
- 判讀：#1005 的 `exact_live_bucket_supported` **本輪已失效**；當前 live row 漂到 `q15`，support 重新回到 proxy fallback 狀態。

### Feature profile / leaderboard
- `data/feature_group_ablation.json`
  - `recommended_profile = core_only`
  - `profile_role.role = global_shrinkage_winner`
- `data/leaderboard_feature_profile_probe.json`
  - `leaderboard_selected_profile = core_only`
  - `train_selected_profile = core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - blocked candidate：`core_plus_macro` → `unsupported_exact_live_structure_bucket`
- 判讀：**profile split 仍存在，但已從 aligned 退回 governance split + blocker-aware fallback。**

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. bull live path 的 trade-floor gap 已明確歸因到 `feat_4h_bias50`，但 current lane 重新掉回 proxy fallback
**現象**
- `entry_quality = 0.4658`
- `trade_floor_gap = -0.0842`
- `best_single_component = feat_4h_bias50`
- `best_single_component_required_score_delta = 0.2807`
- `bias50 fully relaxed -> entry≈0.7807 / layers≈2`

**判讀**
- 這已不是「不知道要修哪個 component」；
- 目前最直接的 root cause 是 **bias50 分數在 current q15 lane 被壓成 0**；
- 但因為 exact bucket 支撐是 0，不能直接把 counterfactual 視為 deployable runtime rule。

---

### P1. live exact bucket 支撐從 supported 退回 `exact_lane_proxy_fallback_only`
**現象**
- `current_live_structure_bucket = CAUTION|structure_quality_caution|q15`
- `current_live_structure_bucket_rows = 0`
- `support_blocker_state = exact_lane_proxy_fallback_only`
- `exact_bucket_root_cause = same_lane_shifted_to_neighbor_bucket`
- `execution_guardrail_reason = unsupported_exact_live_structure_bucket_blocks_trade`

**判讀**
- 這是本輪最重要的治理退步；
- 即使 gap attribution 已完成，當前 runtime 也不能直接靠 piecewise bias50 放行，因為 **exact live bucket 根本沒有 recent support**。

---

### P1. q35/bias50 問題已從 exact-lane formula review 退回 `broader_bull_cohort_recalibration_candidate`
**現象**
- `overall_verdict = broader_bull_cohort_recalibration_candidate`
- `segmented_calibration.status = segmented_calibration_required`
- `reference_cohort = same_gate_same_quality`
- `exact_bias50_pct = 1.0`
- `bull_all_bias50_pct = 0.5049`

**判讀**
- current row 不再是 #1005 那種「回到 exact-lane p90 內」情境；
- 現在要做的是 **q15 lane / broader bull cohort 的 piecewise quantile calibration**，不是沿用上一輪的 exact-lane formula-review 敘事。

---

### P1. leaderboard / production profile split 重新進入 blocker-aware fallback
**現象**
- `leaderboard_selected_profile = core_only`
- `train_selected_profile = core_plus_macro_plus_4h_structure_shift`
- `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
- blocked candidate：`core_plus_macro` with `unsupported_exact_live_structure_bucket`

**判讀**
- 這不是 docs 漂移，而是 **current live bucket 支撐改變造成的真治理分裂**；
- 需要先把 live bucket support 問題講清楚，再談 profile 統一。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1707)**

**判讀**
- 仍是外部憑證 blocker；
- 不可混入 bull live lane / q35 校準根因。

---

## 本輪已清掉的問題

### RESOLVED. 「剩餘 trade-floor gap 到底卡哪個 component」仍需人工讀圖猜測
**修前**
- #1005 已要求下一輪直接回答 component root cause；
- 但 artifact 仍只給 entry-quality breakdown，沒有 machine-readable attribution。

**本輪 patch + 證據**
- `scripts/live_decision_quality_drilldown.py`
  - 新增 `component_gap_attribution`
- `scripts/hb_parallel_runner.py`
  - summary 持久化 `remaining_gap_to_floor / best_single_component / best_single_component_required_score_delta`
- `python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q`
  - **18 passed**
- `python scripts/hb_parallel_runner.py --fast --hb 1006`
  - `data/live_decision_quality_drilldown.json` 明確輸出：
    - `remaining_gap_to_floor = 0.0842`
    - `best_single_component = feat_4h_bias50`
    - `single_component_floor_crossers = [feat_4h_bias50]`

**狀態**
- **已修復**：heartbeat 現在可以 machine-read 回答 gap root cause，不再需要人工從 component 列表反推。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把剩餘 trade-floor gap 轉成 machine-readable component attribution。** ✅
2. **確認 current live bucket 是否仍 exact-supported。** ✅（答案：否，已退回 proxy fallback）
3. **用 fast heartbeat 重跑所有 canonical diagnostics，確認 drift / IC / support / leaderboard 沒有口徑漂移。** ✅

### 本輪不做
- 不直接放寬 q35 gate；
- 不直接調低 `trade_floor`；
- 不把 `bias50 fully relaxed` 當成現在可上線的 runtime 規則；
- 不把 `fin_netflow` auth blocker 混入這輪 bull lane root cause。

---

## Next gate

- **Next focus:**
  1. 針對 `CAUTION|structure_quality_caution|q15` 做 **piecewise / quantile bias50 calibration** 候選分析，確認是否存在可保守上線的 q15 runtime 分段；
  2. 補強 current live bucket support diagnostics：回答 q15 是短暫漂移、還是需要正式新增 q15 proxy/support lane；
  3. 維持 `profile_split`、`support_blocker_state`、`proxy_boundary_verdict`、`fin_netflow auth blocker` 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q15 lane bias50 calibration 或 q15 support route** 直接相關的 patch / artifact / verify；
  2. 若 current live bucket 仍是 `q15` 且 rows=0，必須明確回答「要走 q15 proxy、neighbor bucket、還是保持 blocker」，不能只重述 `unsupported_exact_live_structure_bucket_blocks_trade`；
  3. 若要主張 relax runtime gate，必須先證明新 lane 有足夠 support，且 `allowed_layers=0` guardrail 沒被假放寬。

- **Fallback if fail:**
  - 若下一輪又把焦點退回「gap 卡哪個 component」，視為 regression（本輪已回答）；
  - 若無 support 證據就直接把 bias50 piecewise 套到 q15 live lane，視為 contract regression；
  - 若 `leaderboard / train / support_blocker_state` 語義再漂移，升級 blocker；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 q15 support / calibration contract 再擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1006_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `docs/analysis/live_decision_quality_drilldown.md`
     - `data/q35_scaling_audit.json`
     - `docs/analysis/q35_scaling_audit.md`
     - `data/bull_4h_pocket_ablation.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若同時成立：
     - `best_single_component = feat_4h_bias50`
     - `support_blocker_state = exact_lane_proxy_fallback_only`
     - `current_live_structure_bucket = CAUTION|structure_quality_caution|q15`
     - `current_live_structure_bucket_rows = 0`
     - `overall_verdict = broader_bull_cohort_recalibration_candidate`
     - `execution_guardrail_reason = unsupported_exact_live_structure_bucket_blocks_trade`
     則下一輪不得再把主焦點放回 generic gap attribution；必須直接處理 **q15 lane 的 bias50 calibration / support route**。