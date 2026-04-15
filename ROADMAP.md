# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 10:51 UTC — Heartbeat #1015（q35 scope-applicability contract 已落地；current live row 已回到 exact-supported q35 lane，主路徑正式收斂到 bias50 component experiment / trade-floor closure。）_

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
  - `data/q15_support_audit.json`
  - `data/q15_bucket_root_cause.json`
  - `data/q15_boundary_replay.json`
  - `data/circuit_breaker_audit.json`
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - numbered summary：`data/heartbeat_1015_summary.json`

### 本輪新完成：q35 scope-applicability contract 進入 heartbeat 閉環
- `scripts/hb_q35_scaling_audit.py`
  - 新增 `scope_applicability.{status,active_for_current_live_row,current_structure_bucket,target_structure_bucket,reason}`
  - q35 artifact 現在能明確告訴 heartbeat：這份 bias50 audit 是 **live-active** 還是 **reference-only**
- `scripts/hb_parallel_runner.py`
  - fast heartbeat summary / console 自動帶出 q35 applicability，避免 q35 結論在錯 lane 上誤導治理主焦點
- `tests/test_hb_parallel_runner.py`
  - 鎖住 non-q35 row 會被判成 `reference_only_current_bucket_outside_q35`
- `ARCHITECTURE.md`
  - 同步 q35 scope-applicability contract

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py -q` → **24 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1015` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#1015）：
  - Raw / Features / Labels = **21682 / 13111 / 43362**
  - simulated_pyramid_win = **0.5786**
- label freshness 正常：
  - 240m lag 約 **3.1h**
  - 1440m lag 約 **23.2h**

### IC / drift / live runtime
- Global IC：**19/30**
- TW-IC：**22/30**
- Regime IC：**Bear 5/8 / Bull 6/8 / Chop 6/8**
- drift primary window：**250**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**bull 97.2%**
- live predictor：
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - entry_quality_label：**D**
  - decision_quality_label：**B**
  - allowed layers：**0 → 0**
  - reason：**entry_quality_below_trade_floor**

### q35 / q15 / component 現況
- `q35_scaling_audit`
  - `scope_applicability.status = current_live_q35_lane_active`
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `segmented_calibration.status = formula_review_required`
  - `recommended_mode = exact_lane_formula_review`
- `q15_support_audit`
  - `support_route.verdict = exact_bucket_supported`
  - `current_live_structure_bucket = CAUTION|structure_quality_caution|q35`
  - `current_live_structure_bucket_rows = 58`
  - `floor_cross_legality.verdict = legal_component_experiment_after_support_ready`
  - `best_single_component = feat_4h_bias50`
  - `remaining_gap_to_floor = 0.0644`
  - `best_single_component_required_score_delta = 0.2147`
- `q15_bucket_root_cause`
  - `verdict = current_row_already_above_q35_boundary`
  - `candidate_patch_type = support_accumulation`
  - `candidate_patch_feature = feat_4h_dist_swing_low`
- `q15_boundary_replay`
  - `verdict = boundary_replay_not_applicable`
- 治理結論：
  - **已完成**：q35 audit 現在能分辨 live-active 與 reference-only；q15 support 已恢復為 exact-supported；boundary replay 持續關閉。
  - **未完成**：exact-supported q35 lane 仍低於 trade floor，runtime 仍是 0 layers。
  - **下一步**：直接做 bias50 component experiment，而不是再回 q15 boundary 或 generic q35 敘事。

### Profile split / breaker / source blocker 現況
- profile governance：
  - leaderboard：`core_plus_macro`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - global shrinkage：`core_only`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
  - `profile_split.verdict = dual_role_required`
- circuit breaker：
  - `verdict = mixed_horizon_false_positive`
  - aligned 1440m live horizon：`release_ready = true`
- `fin_netflow`：**auth_missing** / coverage **0.0%**

---

## 當前主目標

### 目標 A：把 exact-supported q35 lane 從 hold-only 推進到可驗證的 bias50 component experiment
目前已確認：
- q35 applicability 已是 `current_live_q35_lane_active`；
- q15 support 已恢復為 `exact_bucket_supported`；
- current live structure bucket 已是 `CAUTION|structure_quality_caution|q35`；
- support 已足，但 entry quality 仍是 **0.4856**，低於 trade floor；
- `feat_4h_bias50` 是目前最有希望的單點 component。

下一步主目標：
- **做 `feat_4h_bias50` exact-supported q35 lane deployment-grade component experiment，回答它能否把 entry_quality 推過 floor 並帶來 `allowed_layers > 0`。**

### 目標 B：停止讓 q15 boundary / generic q35 敘事搶走主頻寬
目前已確認：
- `q15_boundary_replay.verdict = boundary_replay_not_applicable`
- `q15_bucket_root_cause.verdict = current_row_already_above_q35_boundary`
- q35 artifact 現在會先回答 `scope_applicability`

下一步主目標：
- **將 q15 boundary 固定降級成 reference-only 診斷，不再讓 heartbeat 回到過時路徑。**

### 目標 C：收斂 post-threshold profile governance
目前已確認：
- leaderboard / train / global shrinkage 仍是三套語義；
- `dual_profile_state = post_threshold_profile_governance_stalled`。

下一步主目標：
- **在 bias50 component path 初步驗證後，再收斂 `core_plus_macro` / `core_plus_macro_plus_4h_structure_shift` / `core_only` 的角色邊界。**

### 目標 D：維持 blocker-aware governance
目前已確認：
- mixed-horizon breaker 仍是 false positive，不應搶主焦點；
- `fin_netflow` 仍是 auth blocker。

下一步主目標：
- 持續維持零漂移，但不讓它們重新搶走 bias50 component 修補的主頻寬。

---

## 接下來要做

### 1. 做 `feat_4h_bias50` exact-supported q35 lane component experiment
要做：
- 在 exact-supported q35 lane 上做 bias50 formula / score counterfactual；
- 驗證調整後：
  - entry quality 是否跨過 `0.55`；
  - allowed layers 是否 > 0；
  - runtime / guardrail 是否不回歸；
- 產出 machine-readable JSON + markdown；
- 驗證 fast heartbeat summary 能直接摘取 `scope_applicability / verdict / floor delta / layers_after`。

### 2. 鎖住 q15 boundary path 已降級
要做：
- 持續檢查：
  - `q15_support_audit.support_route.verdict`
  - `q15_bucket_root_cause.verdict`
  - `q15_boundary_replay.verdict`
  - `q35_scaling_audit.scope_applicability.status`
- 若 q35 仍是 live-active、boundary replay 仍關閉，就不再回 q15 boundary 當主路徑。

### 3. 做 post-threshold profile governance 收斂
要做：
- 在 exact-supported lane 下重新比較：
  - `leaderboard_selected_profile`
  - `train_selected_profile`
  - `global_recommended_profile`
  - `profile_split`
  - `dual_profile_state`
- 但在 bias50 component 沒驗前，不把 profile 收斂排到第一優先。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 q35 / bias50 / profile 問題。

---

## 暫不優先

以下本輪後仍不排最前面：
- 回頭做 q15 boundary review
- 直接 relax runtime gate
- 再次調查 mixed-horizon breaker
- UI 美化與 fancy controls

原因：
> 當前真正的 live blocker 已收斂成 **exact-supported q35 lane 的 bias50 component / trade-floor gap**；q15 support 已解、boundary replay 已持續關閉。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **bias50 component experiment / entry floor closure** 直接相關的真 patch / run / verify。
2. `q35_scaling_audit.scope_applicability.status`、`q15_support_audit.support_route.verdict`、`q15_boundary_replay.verdict` 對 live path 的描述必須零漂移。
3. mixed-horizon circuit breaker 不得回歸。
4. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 做 `feat_4h_bias50` exact-supported q35 lane component experiment / formula review；
  2. 驗證 profile governance 在 exact-supported lane 下如何收斂；
  3. 維持 q15 boundary replay / source auth blocker / breaker false-positive 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **bias50 component experiment / floor-gap closure** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答 bias50 experiment 是否讓 `entry_quality >= 0.55` 且 `allowed_layers > 0`；
  3. `q35_scaling_audit.scope_applicability.status` 必須持續正確反映 live-active vs reference-only。

- **Fallback if fail:**
  - 若 bias50 experiment 仍無法跨過 floor，下一輪改查 pulse / base mix 聯合路徑；
  - 若 q35 applicability 又變 reference-only，下一輪先處理 current bucket 的 support / component 問題；
  - 若 next run 沒有 bias50 component artifact，升級為 trade-floor blocker。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 bias50 component experiment contract 被正式採納）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1015_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若同時成立：
     - `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
     - `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`
     - `q15_support_audit.support_route.verdict = exact_bucket_supported`
     - `live_predict_probe.allowed_layers = 0`
     則下一輪不得再回 q15 boundary / generic q35 敘事；必須直接處理 **bias50 component experiment / trade-floor closure / profile governance 收斂**。
