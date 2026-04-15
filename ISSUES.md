# ISSUES.md — Current State Only

_最後更新：2026-04-15 07:57 UTC — Heartbeat #1011（本輪修正 q15 support audit 讀取順序與 preferred support cohort 漂移，讓 q15 治理 artifact 改為讀取最新 leaderboard candidate probe 後再判定 support route。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 直接處理 `CAUTION|structure_quality_caution|q15` 的 support route / component gap / floor-cross legality；
  2. 不得再把主焦點退回 breaker；
  3. 維持 `profile_split / fin_netflow auth blocker` 零漂移治理。
- **Success gate**
  1. 至少留下 1 個與 q15 support 或 component gap 直接相關的 patch / artifact / verify；
  2. machine-read 回答 `feat_4h_bias50` 是否能合法跨 floor；
  3. mixed-horizon breaker 不得回歸。
- **Fallback if fail**
  - 不得無 q15 support 證據就直接 relax runtime gate；
  - 若 proxy / neighbor 仍不足 deployment 級證據，升級為 exact-bucket blocker。

### 本輪承接結果
- **已處理**
  - 找到 q15 artifact 新 root cause：`scripts/hb_parallel_runner.py` 先跑 `hb_q15_support_audit.py`、後跑 `hb_leaderboard_candidate_probe.py`，導致 q15 audit 讀到**前一輪** leaderboard probe，support route / proxy rows 可能漂移。
  - 已修 patch：
    - `scripts/hb_parallel_runner.py`：改成 **先刷新 leaderboard candidate probe，再執行 q15 support audit**。
    - `scripts/hb_q15_support_audit.py`：當 route=`exact_live_bucket_proxy_available` 且 exact-bucket proxy rows>0 時，`preferred_support_cohort` 強制對齊 `bull_live_exact_bucket_proxy`，不再誤沿用 exact-lane proxy 名稱。
    - `tests/test_hb_parallel_runner.py`：新增 main-flow regression test，鎖住 `leaderboard -> q15 audit` 執行順序。
    - `tests/test_q15_support_audit.py`：更新 preferred support cohort 斷言。
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py -q` → **23 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1011` → **通過**
- **本輪明確答案**
  - `q15_support_audit.support_route.support_governance_route = exact_live_bucket_proxy_available`
  - `q15_support_audit.support_route.preferred_support_cohort = bull_live_exact_bucket_proxy`
  - `q15_support_audit.support_route.exact_live_bucket_proxy_rows = 4`
  - `q15_support_audit.support_route.exact_live_lane_proxy_rows = 420`
  - `q15_support_audit.floor_cross_legality.verdict = math_cross_possible_but_illegal_without_exact_support`
  - `best_single_component = feat_4h_bias50`，但 **current q15 exact bucket rows 仍為 0/50**，因此仍不可 deployment。
- **本輪明確不做**
  - 不直接放寬 q15 runtime gate；
  - 不把 q35 scaling 問題誤包裝成當前主 blocker；
  - 不把 `fin_netflow` auth blocker 混進 q15 live root cause。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_q15_support_audit.py`
  - `scripts/hb_parallel_runner.py`
  - `tests/test_q15_support_audit.py`
  - `tests/test_hb_parallel_runner.py`
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py -q` → **23 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1011`
- **已刷新 artifacts**
  - `data/heartbeat_1011_summary.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/q35_scaling_audit.json`
  - `data/q15_support_audit.json`
  - `data/circuit_breaker_audit.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`
  - `docs/analysis/q15_support_audit.md`

### 資料 / 新鮮度 / canonical target
- Heartbeat #1011：
  - Raw / Features / Labels：**21587 / 13016 / 43343**
  - 本輪增量：**+1 raw / +1 feature / +2 labels**
  - canonical target `simulated_pyramid_win`：**0.5756**
  - 240m labels：**21734 rows / target_rows 12812 / lag_vs_raw 約 3.0h**
  - 1440m labels：**12524 rows / target_rows 12524 / lag_vs_raw 約 23.2h**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**17/30 pass**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 6/8**
- drift primary window：**recent 250**
  - alerts：`label_imbalance`, `regime_concentration`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 94.4%**
  - win_rate：**0.9720**
  - avg_quality：**0.6609**
  - avg_pnl：**+0.0208**
  - avg_drawdown_penalty：**0.0407**
  - tail_target_streak：**2x0**（since `2026-04-14 08:33:04.582411`）
- 判讀：canonical target 與 recent 1440m lane 仍健康；本輪主 blocker 不是 drift，也不是 breaker，而是 q15 exact bucket support + bias50 floor gap。

### Live contract / q15 support / component gap
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - entry_quality_label：**D**
  - decision_quality_label：**B**
  - decision_quality scope：**`regime_label+regime_gate+entry_quality_label`**（rows=`76`）
  - expected_win_rate / quality：**0.9737 / 0.6667**
  - allowed_layers：**0 → 0**
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `execution_guardrail_reason = unsupported_exact_live_structure_bucket_blocks_trade`
- `data/live_decision_quality_drilldown.json`
  - `remaining_gap_to_floor = 0.1071`
  - `best_single_component = feat_4h_bias50`
  - `best_single_component_required_score_delta = 0.357`
  - `current_live_structure_bucket = CAUTION|structure_quality_caution|q15`
  - `current_live_structure_bucket_rows = 0`
- `data/q15_support_audit.json`
  - `support_governance_route = exact_live_bucket_proxy_available`
  - `preferred_support_cohort = bull_live_exact_bucket_proxy`
  - `exact_live_bucket_proxy_rows = 4`
  - `exact_live_lane_proxy_rows = 420`
  - `supported_neighbor_rows = 157`
  - `support_route.verdict = exact_bucket_missing_proxy_reference_only`
  - `floor_cross_legality.verdict = math_cross_possible_but_illegal_without_exact_support`
  - `legal_to_relax_runtime_gate = false`
- 判讀：本輪已把 q15 support audit 與最新 leaderboard probe 對齊；**數學上 bias50 可補 gap，但在 exact q15 bucket 仍 0/50 rows 時只能做 calibration research，不能 deployment。**

### Q35 / support route / profile split
- `data/q35_scaling_audit.json`
  - `overall_verdict = broader_bull_cohort_recalibration_candidate`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`
- `data/bull_4h_pocket_ablation.json`
  - `bull_exact_live_lane_proxy_rows = 420`
  - `bull_live_exact_lane_bucket_proxy_rows = 4`
  - `bull_supported_neighbor_buckets_proxy_rows = 157`
- `data/leaderboard_feature_profile_probe.json`
  - `leaderboard_selected_profile = core_only`
  - `train_selected_profile = core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `support_governance_route = exact_live_bucket_proxy_available`
- 判讀：q35 不再是當前主 blocker；profile split 仍是治理背景，但主焦點仍是 q15 exact bucket support。

### Breaker / source blockers
- `data/circuit_breaker_audit.json`
  - `root_cause.verdict = mixed_horizon_false_positive`
  - mixed scope：**streak=141 / recent50 win_rate=0.00 / 全部 240m**
  - aligned 1440m scope：**release_ready=true**
- `fin_netflow`
  - coverage：**0.0%**
  - latest status：**auth_missing**
  - archive_window_coverage：**0.0% (0/1713)**
- 判讀：breaker 治理已維持正常；`fin_netflow` 仍是外部憑證 blocker，與 q15 deployment blocker 分開治理。

---

## 目前有效問題

### P1. q15 current live bucket 仍為 0 rows，runtime 仍被 exact support blocker 壓成 0 層
**現象**
- `current_live_structure_bucket = CAUTION|structure_quality_caution|q15`
- `current_live_structure_bucket_rows = 0`
- `minimum_support_rows = 50`
- `execution_guardrail_reason = unsupported_exact_live_structure_bucket_blocks_trade`

**判讀**
- 本輪已修正 q15 artifact 漂移，但 blocker 本身仍在；
- exact-bucket proxy=4、exact-lane proxy=420、neighbor=157 只能作治理參考，仍不足 deployment。

---

### P1. `feat_4h_bias50` 仍是首要 gap，但在 exact support 未達標前只能列為 calibration research
**現象**
- `remaining_gap_to_floor = 0.1071`
- `best_single_component = feat_4h_bias50`
- `required_score_delta_to_cross_floor = 0.357`
- `floor_cross_legality.verdict = math_cross_possible_but_illegal_without_exact_support`

**判讀**
- 這不是「放寬 gate 就能解」的問題；
- 下一輪應先驗證 q15 exact bucket 是否可擴充到 minimum support，再決定 bias50 是否能進入 deployment 級 patch。

---

### P1. production / leaderboard profile split 仍存在，但優先序低於 q15 blocker
**現象**
- global shrinkage winner：`core_only`
- production train profile：`core_plus_macro_plus_4h_structure_shift`
- `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`

**判讀**
- split 仍是治理事實；
- 但在 q15 exact bucket 未補足前，不應把主治理帶寬耗在 profile 收斂。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1713)**

**判讀**
- 仍是外部憑證 blocker；
- 不可與 q15 / profile / breaker 根因混寫。

---

## 本輪已清掉的問題

### RESOLVED. q15 support audit 讀到 stale leaderboard probe，導致 support route / preferred cohort 漂移
**修前**
- `hb_parallel_runner.py` 先跑 q15 audit、後跑 leaderboard candidate probe；
- q15 audit 可能引用前一輪 leaderboard artifact，造成 `support_governance_route / proxy_rows / preferred_support_cohort` 與最新 runtime 事實不同步。

**本輪 patch + 證據**
- `scripts/hb_parallel_runner.py`
  - q15 support audit 改為在 leaderboard candidate probe 之後執行
- `scripts/hb_q15_support_audit.py`
  - 當 route=`exact_live_bucket_proxy_available` 時，`preferred_support_cohort` 對齊 `bull_live_exact_bucket_proxy`
- `python -m pytest tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py -q`
  - **23 passed**
- `python scripts/hb_parallel_runner.py --fast --hb 1011`
  - `q15_support_audit.support_route.support_governance_route = exact_live_bucket_proxy_available`
  - `q15_support_audit.support_route.preferred_support_cohort = bull_live_exact_bucket_proxy`
  - `leaderboard_feature_profile_probe.alignment.support_governance_route = exact_live_bucket_proxy_available`
  - `leaderboard_feature_profile_probe.alignment.bull_exact_live_bucket_proxy_rows = 4`

**狀態**
- **已修復**：q15 support artifact 與最新 leaderboard governance input 已同步；下一輪可直接信任這份 audit 當 q15 決策前提。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **修掉 q15 support artifact 的 stale-input 問題。** ✅
2. **確認 q15 support route 與 preferred cohort 的 machine-readable 結論。** ✅
3. **把主焦點收斂回 exact q15 support + bias50 gap，而不是 breaker / q35。** ✅

### 本輪不做
- 不直接 relax q15 runtime gate；
- 不把 q35 recalibration 誤升級成當前 deploy blocker；
- 不在 `COINGLASS_API_KEY` 缺失時假裝 sparse-source blocker 已解。

---

## Next gate

- **Next focus:**
  1. 直接調查 **為何 q15 exact bucket 仍 0 rows**，把 `same_lane_shifted_to_neighbor_bucket` 拆成可 patch 的 bucket-boundary / structure-threshold 根因；
  2. 針對 `feat_4h_bias50` 做 **q15 lane 專屬 counterfactual**，回答要增加 exact bucket rows 應調哪個結構欄位，而不是只看 floor gap；
  3. 維持 `profile_split / fin_netflow auth blocker / mixed-horizon breaker false-positive` 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q15 exact bucket row generation / boundary repair** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答：`same_lane_shifted_to_neighbor_bucket` 的最小可修補原因是 bucket 邊界、structure scoring、還是 live row projection；
  3. `q15_support_audit` 與 `leaderboard_feature_profile_probe` 的 `support_governance_route / exact_bucket_proxy_rows` 必須持續一致。

- **Fallback if fail:**
  - 若 next run 仍只有 proxy / neighbor 治理、沒有 exact bucket repair path，升級成 **q15 exact-bucket blocker**；
  - 若又出現 q15 audit 與 leaderboard probe 漂移，視為 runner regression；
  - 若沒有 exact support 證據就直接 relax runtime gate，視為風控 regression。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 q15 exact-bucket row generation contract 被正式擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1011_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q15_support_audit.json`
     - `data/leaderboard_feature_profile_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `data/circuit_breaker_audit.json`
  3. 若同時成立：
     - `q15_support_audit.support_route.verdict = exact_bucket_missing_proxy_reference_only`
     - `q15_support_audit.floor_cross_legality.legal_to_relax_runtime_gate = false`
     - `leaderboard_feature_profile_probe.alignment.support_governance_route = exact_live_bucket_proxy_available`
     - `live_predict_probe.current_live_structure_bucket = CAUTION|structure_quality_caution|q15`
     - `live_predict_probe.allowed_layers = 0`
     則下一輪不得再討論 generic q35 或 breaker；必須直接處理 **q15 exact bucket row generation / same-lane-to-neighbor shift root cause**。
