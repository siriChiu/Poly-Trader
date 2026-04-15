# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 12:56 UTC — Heartbeat #1018（`feat_4h_bias50 + feat_pulse (+ feat_nose)` base-mix experiment 已正式落地到 q35 audit / fast heartbeat。結果證明它**明顯優於 structure uplift，但仍無法跨過 trade floor**。當前主路徑已從「base-mix closure 試算」升級成 **base-stack redesign**。）_

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
  - numbered summary：`data/heartbeat_1018_summary.json`

### 本輪新完成：q35 audit 已能 machine-read base-mix trade-floor closure
- `scripts/hb_q35_scaling_audit.py`
  - 新增 `base_component_score_distributions` / `structure_component_score_distributions`
  - 新增 `base_mix_component_experiment`
  - 現在能量化 `bias50 + pulse (+ nose)` uplift 後的 `entry_quality / remaining_gap_to_floor / allowed_layers`
- `scripts/hb_parallel_runner.py`
  - fast heartbeat summary 會同步摘取 `base_mix_component_experiment`
- `tests/test_hb_parallel_runner.py`
  - 新增 regression tests，鎖住 base-mix experiment 與 summary extraction
- `ARCHITECTURE.md`
  - 同步 #1018 q35 base-stack redesign governance contract

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py -q` → **64 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1018` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#1018）：
  - Raw / Features / Labels = **21688 / 13117 / 43421**
  - simulated_pyramid_win = **0.5795**
- label freshness 正常：
  - 240m lag 約 **3.0h**
  - 1440m lag 約 **23.2h**

### IC / drift / live runtime
- Global IC：**19/30**
- TW-IC：**24/30**
- Regime IC：**Bear 5/8 / Bull 6/8 / Chop 5/8**
- drift primary window：**250**
  - interpretation：**distribution_pathology**
  - dominant regime：**bull 98.8%**
- live predictor：
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - entry_quality_label：**D**
  - decision_quality_label：**C**
  - allowed layers：**0 → 0**
  - reason：**entry_quality_below_trade_floor**
  - entry_quality：**0.3725**

### q35 / q15 / component 現況
- `q35_scaling_audit`
  - `scope_applicability.status = current_live_q35_lane_active`
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `segmented_calibration.status = formula_review_required`
  - `segmented_calibration.recommended_mode = exact_lane_formula_review`
  - `deployment_grade_component_experiment.verdict = runtime_patch_improves_but_still_below_floor`
  - `runtime_entry_quality = 0.3725`
  - `runtime_remaining_gap_to_floor = 0.1775`
  - `joint_component_experiment.verdict = joint_component_experiment_improves_but_still_below_floor`
  - `joint_component_experiment.best_scenario.entry_quality_after = 0.3729`
  - `joint_component_experiment.best_scenario.remaining_gap_to_floor = 0.1771`
  - `base_mix_component_experiment.verdict = base_mix_component_experiment_improves_but_still_below_floor`
  - `base_mix_component_experiment.best_scenario = winner_triplet_p75`
  - `base_mix_component_experiment.best_scenario.entry_quality_after = 0.5106`
  - `base_mix_component_experiment.best_scenario.remaining_gap_to_floor = 0.0394`
- `q15_support_audit`
  - `support_route.verdict = exact_bucket_supported`
  - `floor_cross_legality.verdict = legal_component_experiment_after_support_ready`
  - `remaining_gap_to_floor = 0.1775`
  - `best_single_component = feat_4h_bias50`
- 治理結論：
  - **已完成**：q35 audit 不再只看 `bias50` 單點或 `dist_swing_low` 聯合 uplift，現在可直接 machine-read base stack。
  - **未完成**：即使把 `bias50 + pulse + nose` 拉到 winner-triplet-p75，`entry_quality` 仍只有 **0.5106**，距 floor 還差 **0.0394**。
  - **下一步**：主路徑正式改成 **base-stack redesign**；`dist_swing_low` 固定降級成 secondary structure mix。

### Profile split / breaker / source blocker 現況
- profile governance：
  - leaderboard：`core_plus_macro`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - global shrinkage：`core_only`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
- circuit breaker：
  - `verdict = breaker_clear`
  - 1440m canonical live horizon 未觸發 breaker
- source blockers：
  - `fin_netflow`：**auth_missing** / coverage **0.0%**
  - 其餘 sparse sources 目前主要是 **history gap / archive blocker**；`nest_pred` 本輪 latest snapshot 已恢復正常

---

## 當前主目標

### 目標 A：把 trade-floor closure 從「base-mix 試算」升級成真正的 base-stack redesign
目前已確認：
- q35 applicability 仍是 `current_live_q35_lane_active`；
- q15 support 仍是 `exact_bucket_supported`；
- bias50 formula patch 已落地且 runtime 生效；
- 但 `entry_quality` 只有 **0.3725**，距離 floor 還差 **0.1775**；
- 即使 `bias50 + pulse + nose` 拉到 winner-triplet-p75，也只到 **0.5106**。

下一步主目標：
- **不再停留在 component 分位數試算；要直接提出並驗證新的 base-stack patch / contract，回答 bull q35 live lane 是否仍值得部署。**

### 目標 B：固定 `feat_4h_dist_swing_low` 為 secondary structure mix
目前已確認：
- `joint_component_experiment` 只把 `entry_quality` 從 **0.3725 → 0.3729**；
- 它已不是主 blocker。

下一步主目標：
- **把 `dist_swing_low` 鎖定成 secondary mix / support-accumulation 路徑，不再寫成主 closure。**

### 目標 C：維持 post-threshold profile governance，但不搶主焦點
目前已確認：
- leaderboard / train / global shrinkage 仍是三套語義；
- `dual_profile_state = post_threshold_profile_governance_stalled`。

下一步主目標：
- **等 base-stack redesign 有答案後，再收斂 `core_plus_macro` / `core_plus_macro_plus_4h_structure_shift` / `core_only` 的角色邊界。**

### 目標 D：維持 blocker-aware governance
目前已確認：
- `fin_netflow` 仍是 auth blocker；
- 其他 sparse blockers 仍是 history/archive 問題；
- 1440m breaker clear，不應搶主焦點。

下一步主目標：
- 持續維持零漂移，但不讓它們重新搶走 base-stack redesign 主頻寬。

---

## 接下來要做

### 1. 把 `bias50 + pulse + nose` 升級成 base-stack redesign patch
要做：
- 不只重跑分位數 experiment，而是提出新的 base-stack 設計（權重 / score contract / deployment gate）並落成可重跑 artifact；
- 驗證調整後：
  - `entry_quality` 是否跨過 `0.55`；
  - `allowed_layers` 是否 > 0；
  - runtime / q35 applicability / q15 support / execution guardrail 是否不回歸；
- 產出 machine-readable JSON + markdown；
- 讓 fast heartbeat summary 能直接摘取 `best_base_mix_scenario / runtime_gap / redesign_verdict / machine_read_answer`。

### 2. 鎖住 `feat_4h_dist_swing_low` 已降級成 secondary mix
要做：
- 持續檢查：
  - `q35_scaling_audit.joint_component_experiment.verdict`
  - `q15_bucket_root_cause.candidate_patch_feature`
  - `q15_support_audit.floor_cross_legality.best_single_component`
- 若 `dist_swing_low` uplift 仍只帶來極小改善，就不得再把它寫成主要 trade-floor closure 路徑。

### 3. 做 post-threshold profile governance 收斂
要做：
- 在 base-stack 主 blocker 確認後，再重新比較：
  - `leaderboard_selected_profile`
  - `train_selected_profile`
  - `global_recommended_profile`
  - `profile_split`
  - `dual_profile_state`
- 但在 `entry_quality < 0.55` 時，不把 profile 收斂排到第一優先。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 對其餘 sparse sources 持續區分 `history gap` vs `current fetch blocker`；
- 不把它們重包裝成 q35 / base-stack 問題。

---

## 暫不優先

以下本輪後仍不排最前面：
- 再次把 `feat_4h_dist_swing_low` 單獨拿出來當主 closure
- 直接 relax runtime gate
- 先做 profile split 收斂
- UI 美化與 fancy controls

原因：
> 當前真正的 live blocker 已收斂成 **base stack 就算拉到 winner-triplet-p75 仍差 0.0394**；structure uplift 已被反證為次要因素。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **base-stack redesign** 直接相關的真 patch / run / verify。
2. 必須 machine-read 回答 redesign 後是否讓 `entry_quality >= 0.55` 且 `allowed_layers > 0`。
3. `q35_scaling_audit.scope_applicability.status`、`q15_support_audit.support_route.verdict`、`q15_boundary_replay.verdict` 對 live path 的描述必須零漂移。
4. `feat_4h_dist_swing_low` 不得再被誤寫成主 closure，而要維持 secondary mix 定位。
5. `fin_netflow` 需持續被正確標成 auth blocker；其它 sparse blockers 需維持正確 history-gap / snapshot-only 語義。

---

## Next gate

- **Next focus:**
  1. 做 `feat_4h_bias50 + feat_pulse + feat_nose` 的 **base-stack redesign**；
  2. 維持 `feat_4h_dist_swing_low` 的 secondary structure mix 定位；
  3. 維持 profile governance / source blockers / q15 boundary replay 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **base-stack redesign** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答 redesign 是否讓 `entry_quality >= 0.55` 且 `allowed_layers > 0`；
  3. `base_mix_component_experiment` 必須持續正確反映 live-active q35 lane 的 closure 狀態。

- **Fallback if fail:**
  - 若 redesign 後仍無法跨過 floor，下一輪升級為 **bull q35 no-deploy governance blocker**；
  - 若 q35 applicability 又變 reference-only，下一輪先處理 current bucket 的 support / component 問題；
  - 若 next run 沒有 base-stack redesign artifact，升級為 trade-floor blocker。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 base-stack redesign contract 再被細化）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1018_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
     - `data/q15_bucket_root_cause.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若同時成立：
     - `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
     - `q15_support_audit.support_route.verdict = exact_bucket_supported`
     - `q35_scaling_audit.base_mix_component_experiment.verdict = base_mix_component_experiment_improves_but_still_below_floor`
     - `live_predict_probe.allowed_layers = 0`
     則下一輪不得再回 `dist_swing_low` 單點 uplift；必須直接處理 **base-stack redesign**。
