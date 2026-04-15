# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 05:35 UTC — Heartbeat #1006（本輪已把「trade-floor gap 根因拆解」正式落地成 machine-readable contract：`live_decision_quality_drilldown` 現在會直接輸出 `component_gap_attribution`。同時也確認 current live bull bucket 已從 q35 漂到 q15，exact support 重新歸零，治理焦點必須轉向 q15 lane support / calibration，而不是繼續停在 generic gap 問題。）_

本文件只保留**目前已落地能力、當前主目標、下一步 gate**，不保留歷史 roadmap 敘事。

---

## 已完成

### Canonical heartbeat / diagnostics
- fast heartbeat 持續刷新：
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/q35_scaling_audit.json`
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `issues.json`
  - numbered summary：`data/heartbeat_1006_summary.json`

### 本輪新完成：entry-quality gap attribution contract 已落地
- `scripts/live_decision_quality_drilldown.py`
  - 新增 `component_gap_attribution`
  - 會輸出：
    - `remaining_gap_to_floor`
    - `best_single_component`
    - `best_single_component_required_score_delta`
    - `single_component_floor_crossers`
    - `bias50_floor_counterfactual`
- `scripts/hb_parallel_runner.py`
  - fast heartbeat summary 現在會同步保存：
    - `live_decision_drilldown.remaining_gap_to_floor`
    - `live_decision_drilldown.best_single_component`
    - `live_decision_drilldown.best_single_component_required_score_delta`
- `tests/test_live_decision_quality_drilldown.py`
  - 鎖住 `feat_4h_bias50` 必須被辨識為最佳單點修補候選
- `tests/test_hb_parallel_runner.py`
  - 鎖住 summary 持久化新的 gap attribution 欄位

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q` → **18 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1006` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#1006）：
  - Raw / Features / Labels = **21580 / 13009 / 43193**
  - simulated_pyramid_win = **0.5784**
- label freshness 正常：
  - 240m lag 約 **3.0h**
  - 1440m lag 約 **23.4h**

### IC / drift / live contract
- Global IC：**19/30**
- TW-IC：**20/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 6/8**
- drift primary window：**100**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**bull 100%**
- live predictor：
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.4658 (D)**
  - allowed layers：**0**
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `execution_guardrail_reason = unsupported_exact_live_structure_bucket_blocks_trade`
  - chosen scope：**`regime_label+entry_quality_label`**（sample_size=197）
  - expected win rate：**0.9848**
  - expected pyramid quality：**0.6714**

### 本輪新結論：gap root cause 已回答，但 current live lane 支撐惡化
- `data/live_decision_quality_drilldown.json`
  - `remaining_gap_to_floor = 0.0842`
  - `best_single_component = feat_4h_bias50`
  - `best_single_component_required_score_delta = 0.2807`
  - `single_component_floor_crossers = [feat_4h_bias50]`
  - `bias50 fully relaxed -> entry≈0.7807 / layers≈2`
- `data/q35_scaling_audit.json`
  - `overall_verdict = broader_bull_cohort_recalibration_candidate`
  - `segmented_calibration.status = segmented_calibration_required`
  - `reference_cohort = same_gate_same_quality`
- `data/bull_4h_pocket_ablation.json`
  - `current_live_structure_bucket = CAUTION|structure_quality_caution|q15`
  - `current_live_structure_bucket_rows = 0`
  - `support_blocker_state = exact_lane_proxy_fallback_only`
- **治理結論**：
  - generic gap attribution 已完成；
  - 但 current live lane 不再是 #1005 的 q35 exact-supported 狀態；
  - 下一步必須轉成 **q15 lane support + q15 piecewise calibration** 治理。

### 模型 / shrinkage / bull support 對齊
- global recommended profile：**`core_only`**
- production train profile：**`core_plus_macro_plus_4h_structure_shift`**
- leaderboard selected profile：**`core_only`**
- dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
- blocked candidate：`core_plus_macro` → `unsupported_exact_live_structure_bucket`

### Source blocker
- `fin_netflow` 仍是 **auth_missing**
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵

---

## 當前主目標

### 目標 A：從 generic gap attribution 轉進 **q15 lane bias50 calibration**
目前已確認：
- 問題最直接卡在 `feat_4h_bias50`；
- `feat_4h_bias50` 是唯一 single-component floor crosser；
- 但 current lane 已變成 `CAUTION|structure_quality_caution|q15`，不再是 q35 exact-supported。

下一步主目標：
- **釐清 q15 lane 是否存在可保守上線的 piecewise / quantile bias50 calibration**；
- 不能直接把 #1005 的 exact-lane formula-review 套回來。

### 目標 B：把 q15 live bucket support route machine-readable 化
目前已確認：
- `current_live_structure_bucket_rows = 0`
- `support_blocker_state = exact_lane_proxy_fallback_only`
- `exact_bucket_root_cause = same_lane_shifted_to_neighbor_bucket`
- `supported_neighbor_buckets = [CAUTION|structure_quality_caution|q35]`

下一步主目標：
- heartbeat / probe / ablation / docs 必須明確回答：
  - q15 是短暫漂移還是穩定新 lane？
  - 應採 exact-bucket proxy、exact-lane proxy、neighbor bucket，還是保持 blocker？

### 目標 C：維持 profile split 與 blocker-aware ranking 語義
目前已確認：
- global best：`core_only`
- production train best：`core_plus_macro_plus_4h_structure_shift`
- leaderboard 現在因 live bucket 無 support 而退回 global winner

下一步主目標：
- **確保這組 split 是治理結果，不是 artifact 漂移**；
- 若 q15 support 補回，才重新檢查 leaderboard / production 是否該重新靠攏。

### 目標 D：維持 source auth blocker 與 live bull lane 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 q15 / bias50 / support route 敘事

---

## 接下來要做

### 1. 做 q15 lane 的 bias50 piecewise / quantile calibration 候選
要做：
- 用 `same_gate_same_quality` / q15 相關 cohort 比較當前 `bias50` 所處分位；
- 確認是否有保守但可驗證的 q15 bias50 score extension；
- 保留 `allowed_layers=0` guardrail，除非 support 與 calibration 同時成立。

### 2. 做 q15 support route 決策
要做：
- 明確比較：
  - `exact_live_bucket`
  - `bull_live_exact_lane_bucket_proxy`
  - `bull_exact_live_lane_proxy`
  - `supported_neighbor_buckets`
- 目標不是強行放行，而是**正式決定 q15 應該如何治理**。

### 3. 維持 blocker-aware feature-profile governance
要做：
- 持續檢查：
  - `leaderboard_selected_profile`
  - `train_selected_profile`
  - `blocked_candidate_profiles`
  - `support_blocker_state`
  - `proxy_boundary_verdict`
- 若 q15 support 未恢復，leaderboard fallback 到 `core_only` 不視為 bug；
  但 docs / summary 必須講清楚原因。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 q15 live path 問題

---

## 暫不優先

以下本輪後仍不排最前面：
- 直接放寬 q35/q15 runtime gate
- 直接調低 `trade_floor`
- 重新追已回答的 generic component attribution
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸已不是「不知道 gap 卡哪個 component」，而是 **current q15 lane 沒 support，且 bias50 需要新的 cohort-aware calibration**。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **q15 lane bias50 calibration 或 q15 support route** 直接相關的真 patch / run / verify。
2. `live_decision_quality_drilldown / q35_scaling_audit / bull_4h_pocket_ablation / leaderboard_feature_profile_probe` 對 `q15` 狀態的描述必須零漂移。
3. 若 current live bucket 仍 rows=0，必須再次明確回答該 lane 的治理路徑，而不是只重述 blocker 名稱。
4. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 針對 `q15` live lane 做 bias50 calibration 候選分析；
  2. 明確決定 q15 support route（proxy / neighbor / blocker）；
  3. 維持 `profile_split`、`support_blocker_state`、`proxy_boundary_verdict`、`fin_netflow auth blocker` 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q15 lane bias50 calibration 或 q15 support route** 直接相關的 patch / artifact / verify；
  2. 若 current live bucket 仍是 `CAUTION|structure_quality_caution|q15` 且 rows=0，必須明確回答治理路徑；
  3. 若要主張 relax runtime gate，必須先證明新 lane 有 support 且沒有破壞 `allowed_layers=0` guardrail。

- **Fallback if fail:**
  - 若 heartbeat 又把焦點退回 generic gap attribution，視為 regression；
  - 若無 support 證據就直接把 bias50 piecewise 套到 q15 live lane，視為 contract regression；
  - 若 leaderboard / train / support 語義再漂移，視為 blocker；
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
     - `current_live_structure_bucket = CAUTION|structure_quality_caution|q15`
     - `current_live_structure_bucket_rows = 0`
     - `support_blocker_state = exact_lane_proxy_fallback_only`
     - `overall_verdict = broader_bull_cohort_recalibration_candidate`
     則下一輪不得再把焦點放回 generic gap attribution；必須直接處理 **q15 lane support + bias50 calibration**。