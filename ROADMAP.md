# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 13:30 UTC — Heartbeat #1019（`base_stack_redesign_experiment` 已正式落地到 q35 audit / fast heartbeat。結果證明：**current bull q35 lane 的 exact support 已足夠，但任何保留正向 discrimination 的 redesign 都無法跨過 trade floor；只有 ear-heavy 非辨識性權重才會假性跨 floor。** 當前主路徑已從「base-stack redesign」升級成 **bull q35 no-deploy governance**。）_

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
  - numbered summary：`data/heartbeat_1019_summary.json`

### 本輪新完成：q35 audit 已能 machine-read base-stack redesign 是否可部署
- `scripts/hb_q35_scaling_audit.py`
  - 新增 `base_stack_redesign_experiment`
  - 現在可同時產出：
    - `best_discriminative_candidate`
    - `best_floor_candidate`
    - `unsafe_floor_cross_candidate`
  - 能直接回答 safe redesign 是否真能讓 `entry_quality >= 0.55` / `allowed_layers > 0`
- `scripts/hb_parallel_runner.py`
  - fast heartbeat summary 會同步摘取 `base_stack_redesign_experiment`
  - q35 console 摘要會輸出 redesign verdict / discriminative gap / unsafe floor-cross
- `tests/test_hb_parallel_runner.py`
  - 新增 redesign regression，鎖住「只有 ear-heavy 權重可假性跨 floor」
- `ARCHITECTURE.md`
  - 同步 #1019 no-deploy governance contract

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py -q` → **65 passed**
- `source venv/bin/activate && python scripts/hb_q35_scaling_audit.py` → **通過**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1019` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#1019）：
  - Raw / Features / Labels = **21689 / 13118 / 43447**
  - simulated_pyramid_win = **0.5799**
- label freshness 正常：
  - 240m lag 約 **3.0h**
  - 1440m lag 約 **23.3h**

### IC / drift / live runtime
- Global IC：**19/30**
- TW-IC：**26/30**
- Regime IC：**Bear 5/8 / Bull 6/8 / Chop 5/8**
- drift primary window：**250**
  - interpretation：**distribution_pathology**
  - dominant regime：**bull 99.6%**
- live predictor：
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - entry_quality_label：**D**
  - decision_quality_label：**C**
  - allowed layers：**0 → 0**
  - reason：**entry_quality_below_trade_floor**
  - entry_quality：**0.3944**

### q35 / q15 / redesign 現況
- `q35_scaling_audit`
  - `scope_applicability.status = current_live_q35_lane_active`
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `segmented_calibration.status = formula_review_required`
  - `segmented_calibration.recommended_mode = exact_lane_formula_review`
  - `deployment_grade_component_experiment.runtime_entry_quality = 0.3944`
  - `deployment_grade_component_experiment.runtime_remaining_gap_to_floor = 0.1556`
  - `joint_component_experiment.best_scenario.entry_quality_after = 0.3954`
  - `base_mix_component_experiment.best_scenario.entry_quality_after = 0.5090`
  - `base_mix_component_experiment.best_scenario.remaining_gap_to_floor = 0.0410`
  - `base_stack_redesign_experiment.verdict = base_stack_redesign_floor_cross_requires_non_discriminative_reweight`
  - `base_stack_redesign_experiment.best_discriminative_candidate.entry_quality_after = 0.3767`
  - `base_stack_redesign_experiment.best_floor_candidate.entry_quality_after = 0.8375`
  - `base_stack_redesign_experiment.unsafe_floor_cross_candidate != null`
- `q15_support_audit`
  - `support_route.verdict = exact_bucket_supported`
  - `floor_cross_legality.verdict = legal_component_experiment_after_support_ready`
  - `remaining_gap_to_floor = 0.1556`
  - `best_single_component = feat_4h_bias50`
- 治理結論：
  - **已完成**：q35 audit 不再只看 base-mix，現在能正式判定 redesign 是否具 deployment 意義。
  - **已確認**：current bull q35 lane 的 support 已足夠，問題不是 support shortage。
  - **新結論**：safe redesign 仍無法跨 floor；只有 unsafe ear-heavy 權重能假性跨 floor，因此這條 lane 必須升級成 **no-deploy governance blocker**。

### Profile split / breaker / source blocker 現況
- profile governance：
  - leaderboard：`core_plus_macro`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - global shrinkage：`core_plus_4h`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
- circuit breaker：
  - `verdict = breaker_clear`
  - 1440m canonical live horizon 未觸發 breaker
- source blockers：
  - `fin_netflow`：**auth_missing** / coverage **0.0%**
  - 其餘 sparse sources 目前主要是 **history gap / archive blocker**

---

## 當前主目標

### 目標 A：把 bull q35 live lane 正式治理成 no-deploy governance blocker
目前已確認：
- q35 applicability 仍是 `current_live_q35_lane_active`；
- q15 support 仍是 `exact_bucket_supported`；
- bias50 formula patch 已落地且 runtime 生效；
- base-mix 最佳情境仍只到 **0.5090**；
- redesign 只有 ear-heavy 非辨識性權重會假性跨 floor。

下一步主目標：
- **不再把這條 lane 寫成「差一點 closure」；要直接把 no-deploy governance blocker propagated 到主要治理 surface。**

### 目標 B：固定 `feat_4h_dist_swing_low` 為 secondary structure mix
目前已確認：
- `joint_component_experiment` 只把 `entry_quality` 從 **0.3944 → 0.3954**；
- 它已不是主 blocker。

下一步主目標：
- **把 `dist_swing_low` 鎖定成 secondary mix / support-accumulation 路徑，不再寫成主 closure。**

### 目標 C：維持 post-threshold profile governance，但不搶主焦點
目前已確認：
- leaderboard / train / global shrinkage 仍是三套語義；
- `dual_profile_state = post_threshold_profile_governance_stalled`。

下一步主目標：
- **等 no-deploy blocker propagated 後，再收斂 `core_plus_macro` / `core_plus_macro_plus_4h_structure_shift` / `core_plus_4h` 的角色邊界。**

### 目標 D：維持 blocker-aware governance
目前已確認：
- `fin_netflow` 仍是 auth blocker；
- 其他 sparse blockers 仍是 history/archive 問題；
- 1440m breaker clear，不應搶主焦點。

下一步主目標：
- 持續維持零漂移，但不讓它們重新搶走 bull q35 no-deploy 主頻寬。

---

## 接下來要做

### 1. 把 bull q35 no-deploy blocker propagated 到主要治理 surface
要做：
- 不只在 q35 audit 提醒，而是讓主要治理輸出都能 machine-read 這條 lane **不可部署**；
- 驗證調整後：
  - current blocker 是否明確標成 `non-discriminative reweight / unsafe_floor_cross_candidate`；
  - `entry_quality` / `allowed_layers` / support / applicability 語義不回歸；
  - fast heartbeat summary 能直接摘取 no-deploy blocker。

### 2. 鎖住 `feat_4h_dist_swing_low` 已降級成 secondary mix
要做：
- 持續檢查：
  - `q35_scaling_audit.joint_component_experiment.verdict`
  - `q15_bucket_root_cause.candidate_patch_feature`
  - `q15_support_audit.floor_cross_legality.best_single_component`
- 若 `dist_swing_low` uplift 仍只帶來極小改善，就不得再把它寫成主要 trade-floor closure 路徑。

### 3. 做 post-threshold profile governance 收斂
要做：
- 在 no-deploy blocker 清楚 propagated 後，再重新比較：
  - `leaderboard_selected_profile`
  - `train_selected_profile`
  - `global_recommended_profile`
  - `profile_split`
  - `dual_profile_state`
- 但在 bull q35 lane 仍 `allowed_layers=0` 時，不把 profile 收斂排到第一優先。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 對其餘 sparse sources 持續區分 `history gap` vs `current fetch blocker`；
- 不把它們重包裝成 bull q35 no-deploy 問題。

---

## 暫不優先

以下本輪後仍不排最前面：
- 再次把 `feat_4h_dist_swing_low` 單獨拿出來當主 closure
- 直接 relax runtime gate
- 再追一次 base-stack 權重微調
- 先做 profile split 收斂
- UI 美化與 fancy controls

原因：
> 當前真正的 live blocker 已收斂成 **只有 unsafe ear-heavy 權重才會讓 q35 lane 假性跨 floor**；這不是 deployment closure，而是明確的 no-deploy 信號。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **bull q35 no-deploy governance** 直接相關的真 patch / run / verify。
2. 必須 machine-read 回答：safe redesign 為何失敗、unsafe floor-cross 為何不可部署。
3. `q35_scaling_audit.scope_applicability.status`、`q15_support_audit.support_route.verdict`、`leaderboard_feature_profile_probe.alignment.dual_profile_state` 必須維持零漂移。
4. `feat_4h_dist_swing_low` 不得再被誤寫成主 closure，而要維持 secondary mix 定位。
5. `fin_netflow` 需持續被正確標成 auth blocker；其它 sparse blockers 需維持正確 history-gap / snapshot-only 語義。

---

## Next gate

- **Next focus:**
  1. 把 **bull q35 no-deploy governance blocker** 變成主治理輸出；
  2. 維持 `feat_4h_dist_swing_low` 的 secondary structure mix 定位；
  3. 維持 profile governance / source blockers / q15 boundary replay 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **bull q35 no-deploy governance** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答 blocker 是 `unsafe_floor_cross_candidate` / `non-discriminative reweight`，不是 support shortage；
  3. `base_stack_redesign_experiment` 必須持續正確反映 live-active q35 lane 的 no-deploy 狀態。

- **Fallback if fail:**
  - 若 no-deploy blocker 仍只存在 q35 audit、未 propagated 到主治理 surface，下一輪直接 patch predictor / summary contract；
  - 若 q35 applicability 又變 reference-only，下一輪先處理 current bucket 的 support / component 問題；
  - 若 next run 沒有 no-deploy governance artifact，升級為 governance blocker 漂移問題。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 no-deploy governance contract 再擴大到 predictor / API surface）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1019_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若同時成立：
     - `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
     - `q15_support_audit.support_route.verdict = exact_bucket_supported`
     - `q35_scaling_audit.base_stack_redesign_experiment.verdict = base_stack_redesign_floor_cross_requires_non_discriminative_reweight`
     - `q35_scaling_audit.base_stack_redesign_experiment.unsafe_floor_cross_candidate != null`
     - `live_predict_probe.allowed_layers = 0`
     則下一輪不得再追 base-stack closure；必須直接把 **bull q35 no-deploy governance blocker** 變成主治理輸出。
