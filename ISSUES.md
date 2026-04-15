# ISSUES.md — Current State Only

_最後更新：2026-04-15 13:30 UTC — Heartbeat #1019（已把 **base-stack redesign** 正式落地成 machine-readable audit。結論：**current bull q35 live lane 不缺 exact support，但任何保留正向 discrimination 的 redesign 都無法跨過 trade floor；只有 ear-heavy 非辨識性權重才會假性跨 floor，因此主 blocker 已正式升級成 `bull q35 no-deploy governance blocker`。**）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 把 `feat_4h_bias50 + feat_pulse + feat_nose` 升級成 **base-stack redesign**；
  2. 維持 `feat_4h_dist_swing_low` 為 secondary structure mix；
  3. 維持 profile governance / source blockers / q15 boundary replay 零漂移治理。
- **Success gate**
  1. 至少留下 1 個與 **base-stack redesign** 直接相關的 patch / artifact / verify；
  2. machine-read 回答 redesign 後是否讓 `entry_quality >= 0.55` 且 `allowed_layers > 0`；
  3. `base_mix_component_experiment` 必須持續存在並反映 live-active q35 lane 狀態。
- **Fallback if fail**
  - 若 redesign 後仍無法跨過 floor，下一輪升級為 **bull q35 no-deploy governance blocker**；
  - 若 q35 applicability 轉成 reference-only，先處理 current bucket support / component；
  - 若沒有新 patch 只剩報告，視為 `HEARTBEAT FAILED: NO FORWARD PROGRESS`。

### 本輪承接結果
- **已處理**
  - `scripts/hb_q35_scaling_audit.py`
    - 新增 `base_stack_redesign_experiment={verdict,machine_read_answer,best_discriminative_candidate,best_floor_candidate,unsafe_floor_cross_candidate}`。
    - 直接用 runtime exact lane 做 support-aware / discriminative reweight grid search，回答 redesign 是否真的可部署。
    - `recommended_action` 現在會在 redesign 失敗時直接升級為 **bull q35 no-deploy governance blocker**。
  - `scripts/hb_parallel_runner.py`
    - fast heartbeat summary 已同步摘取 `base_stack_redesign_experiment`。
    - q35 console 摘要現在會顯示 redesign verdict / entry_quality / positive_discriminative_gap。
  - `tests/test_hb_parallel_runner.py`
    - 新增 redesign regression：鎖住「只有 ear-heavy 非辨識性權重能假性跨 floor」這個治理結論。
  - `ARCHITECTURE.md`
    - 同步 #1019 base-stack redesign → no-deploy governance contract。
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py -q` → **65 passed**
  - `source venv/bin/activate && python scripts/hb_q35_scaling_audit.py` → **通過**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1019` → **通過**
- **本輪 machine-read 結論**
  - `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
  - `q15_support_audit.support_route.verdict = exact_bucket_supported`
  - `deployment_grade_component_experiment.runtime_entry_quality = 0.3944`
  - `deployment_grade_component_experiment.runtime_remaining_gap_to_floor = 0.1556`
  - `joint_component_experiment.best_scenario.entry_quality_after = 0.3954`
  - `base_mix_component_experiment.best_scenario.entry_quality_after = 0.5090`
  - `base_mix_component_experiment.best_scenario.remaining_gap_to_floor = 0.0410`
  - `base_stack_redesign_experiment.verdict = base_stack_redesign_floor_cross_requires_non_discriminative_reweight`
  - `base_stack_redesign_experiment.best_discriminative_candidate.current_entry_quality_after = 0.3767`
  - `base_stack_redesign_experiment.best_discriminative_candidate.remaining_gap_to_floor = 0.1733`
  - `base_stack_redesign_experiment.best_floor_candidate.current_entry_quality_after = 0.8375`
  - `base_stack_redesign_experiment.unsafe_floor_cross_candidate != null`
  - `live_predict_probe.allowed_layers = 0`
- **本輪明確不做**
  - 不直接 relax runtime gate；
  - 不把 ear-heavy 權重假跨 floor 包裝成可部署 redesign；
  - 不讓 profile split / sparse-source blockers 取代 bull q35 no-deploy 主 blocker。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_q35_scaling_audit.py`
    - 新增 `base_stack_redesign_experiment`。
    - 現在可同時區分：
      - `best_discriminative_candidate`（保留正向 discrimination 的 redesign）
      - `best_floor_candidate`（只看 current row floor 最大化）
      - `unsafe_floor_cross_candidate`（假跨 floor，不可部署）
  - `scripts/hb_parallel_runner.py`
    - fast summary / console 會同步輸出 redesign 結論。
  - `tests/test_hb_parallel_runner.py`
    - 鎖住「ear-heavy floor-cross = unsafe」回歸測試。
  - `ARCHITECTURE.md`
    - 已同步 q35 redesign → no-deploy governance contract。
- **Tests（已通過）**
  - `python -m pytest tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py -q` → **65 passed**
- **Runtime verify（已通過）**
  - `python scripts/hb_q35_scaling_audit.py`
  - `python scripts/hb_parallel_runner.py --fast --hb 1019`
- **已刷新 artifacts**
  - `data/heartbeat_1019_summary.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/q35_scaling_audit.json`
  - `data/q15_support_audit.json`
  - `data/q15_bucket_root_cause.json`
  - `data/q15_boundary_replay.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`

### 資料 / 新鮮度 / canonical target
- Heartbeat #1019：
  - Raw / Features / Labels：**21689 / 13118 / 43447**
  - 本輪增量：**+1 raw / +1 feature / +26 labels**
  - canonical target `simulated_pyramid_win`：**0.5799**
  - 240m labels：**21822 rows / target_rows 12900 / lag_vs_raw 約 3.0h**
  - 1440m labels：**12540 rows / target_rows 12540 / lag_vs_raw 約 23.3h**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**26/30 pass**
- Regime IC：**Bear 5/8 / Bull 6/8 / Chop 5/8**
- drift primary window：**recent 250**
  - alerts：`label_imbalance`, `regime_concentration`, `regime_shift`
  - interpretation：**distribution_pathology**
  - dominant_regime：**bull 99.6%**
  - win_rate：**0.9360**
  - avg_quality：**0.6303**
  - avg_pnl：**+0.0200**
  - avg_drawdown_penalty：**0.0467**
- 判讀：近期 bull 強集中仍需顯式標記，但本輪 live blocker 已不是 support 缺口，而是 **q35 live lane 的 trade-floor closure 在安全 redesign 下仍失敗**。

### Live contract / q35 / q15 現況
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - entry_quality_label：**D**
  - decision_quality_label：**C**
  - `entry_quality = 0.3944`
  - `allowed_layers = 0 → 0`
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - base components：`bias50=0.2347`, `nose=0.2716`, `pulse=0.3644`, `ear=0.9787`
- `data/q35_scaling_audit.json`
  - `scope_applicability.status = current_live_q35_lane_active`
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `segmented_calibration.status = formula_review_required`
  - `segmented_calibration.recommended_mode = exact_lane_formula_review`
  - `deployment_grade_component_experiment.runtime_entry_quality = 0.3944`
  - `deployment_grade_component_experiment.runtime_remaining_gap_to_floor = 0.1556`
  - `joint_component_experiment.best_scenario.entry_quality_after = 0.3954`
  - `base_mix_component_experiment.best_scenario.entry_quality_after = 0.5090`
  - `base_mix_component_experiment.best_scenario.remaining_gap_to_floor = 0.0410`
  - `base_stack_redesign_experiment.best_discriminative_candidate.weights = pulse-only`
  - `base_stack_redesign_experiment.best_discriminative_candidate.entry_quality_after = 0.3767`
  - `base_stack_redesign_experiment.best_floor_candidate.weights = ear-only`
  - `base_stack_redesign_experiment.best_floor_candidate.entry_quality_after = 0.8375`
  - `base_stack_redesign_experiment.unsafe_floor_cross_candidate` **存在**
- `data/q15_support_audit.json`
  - `support_route.verdict = exact_bucket_supported`
  - `floor_cross_legality.verdict = legal_component_experiment_after_support_ready`
  - `remaining_gap_to_floor = 0.1556`
  - `best_single_component = feat_4h_bias50`
- 判讀：**exact support 已足夠、q35 lane 仍是 live-active；真正結論是這條 lane 只有靠破壞 discrimination 的 ear-heavy 權重才會跨 floor，因此 deployment closure 不成立。**

### Profile split / governance / blockers
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard：`core_plus_macro`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - global shrinkage：`core_plus_4h`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
  - `profile_split.verdict = dual_role_required`
- sparse-source blockers
  - `fin_netflow`：**auth_missing / coverage 0.0% / archive_window_coverage 0.0% (0/1813)**
  - 其餘 blocked sparse sources：目前仍以 **history gap / snapshot archive** 為主
- 判讀：profile split 與 sparse blockers 仍需治理，但優先序仍低於 bull q35 no-deploy 主 blocker。

---

## 目前有效問題

### P1. bull q35 live lane 已確認不具 deployment closure：需升級為 no-deploy governance blocker
**現象**
- `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
- `q15_support_audit.support_route.verdict = exact_bucket_supported`
- `deployment_grade_component_experiment.runtime_entry_quality = 0.3944`
- `base_mix_component_experiment.best_scenario.entry_quality_after = 0.5090`
- `base_mix_component_experiment.best_scenario.remaining_gap_to_floor = 0.0410`
- `base_stack_redesign_experiment.best_discriminative_candidate.current_entry_quality_after = 0.3767`
- `base_stack_redesign_experiment.best_discriminative_candidate.mean_gap = 0.2303`
- `base_stack_redesign_experiment.best_floor_candidate.current_entry_quality_after = 0.8375`
- `base_stack_redesign_experiment.best_floor_candidate.mean_gap = -0.0109`
- `base_stack_redesign_experiment.unsafe_floor_cross_candidate != null`
- `live_predict_probe.allowed_layers = 0`

**判讀**
- support 已足夠，主 blocker 不再是 exact bucket coverage；
- `bias50 + pulse (+ nose)` 的 base-mix 已接近 floor，但仍差 **0.0410**；
- 進一步做 redesign 後，**唯一跨 floor 的候選是 ear-heavy 非辨識性權重**，這會讓 exact-lane 正負樣本分離失效；
- 因此這條 bull q35 lane 不能再被描述成「差最後一點 closure」，而是應正式升級成 **no-deploy governance blocker**。

---

### P1. post-threshold profile governance stalled：leaderboard / train / global shrinkage 仍三套語義
**現象**
- leaderboard：`core_plus_macro`
- train：`core_plus_macro_plus_4h_structure_shift`
- global shrinkage：`core_plus_4h`
- `dual_profile_state = post_threshold_profile_governance_stalled`

**判讀**
- 仍需保留 dual-role governance；
- 但在 bull q35 no-deploy blocker 尚未明確 propagated 前，不能搶走主修補頻寬。

---

### P1. sparse-source blockers 仍存在，`fin_netflow` 仍是 live auth blocker
**現象**
- `fin_netflow`：`auth_missing`, `coverage=0.0%`
- blocked sparse features：**8 個**
- 其餘 blocked sparse features 主要仍是 history/archive 缺口

**判讀**
- `fin_netflow` 仍是外部憑證 blocker；
- 其他 sparse sources 主要是 history/archive 問題，不應與 bull q35 no-deploy blocker 混寫。

---

## 本輪已清掉的問題

### RESOLVED. heartbeat 缺少可驗證的 base-stack redesign artifact
**修前**
- heartbeat 只能 machine-read `base_mix_component_experiment`，無法正式回答「保留 discrimination 的 redesign 是否值得繼續」。

**本輪 patch + 證據**
- `scripts/hb_q35_scaling_audit.py`：新增 `base_stack_redesign_experiment`
- `scripts/hb_parallel_runner.py`：新增 redesign summary extraction / console diagnostics
- `tests/test_hb_parallel_runner.py`：新增 redesign regression
- `python -m pytest tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py -q` → **65 passed**
- `python scripts/hb_q35_scaling_audit.py`
  - `base_stack_redesign_experiment.verdict = base_stack_redesign_floor_cross_requires_non_discriminative_reweight`
  - `best_discriminative_candidate.entry_quality_after = 0.3767`
  - `best_floor_candidate.entry_quality_after = 0.8375`
  - `unsafe_floor_cross_candidate != null`

**狀態**
- **已修復**：heartbeat 現在能正式 machine-read 判定「safe redesign 不可部署；unsafe redesign 只能當 blocker 證據」。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 base-stack redesign 做成 machine-readable artifact，直接回答 safe redesign 是否真能跨過 trade floor。** ✅
2. **若 redesign 失敗，正式把 bull q35 lane 升級為 no-deploy governance blocker。** ✅（文件已升級）
3. **維持 q15 exact support / profile governance / sparse blockers 的零漂移治理。** ✅

### 本輪不做
- 不直接 relax runtime gate；
- 不把 ear-heavy 權重假跨 floor 誤包裝成成功 redesign；
- 不讓 profile split / sparse-source blocker 取代 bull q35 no-deploy 主焦點。

---

## Next gate

- **Next focus:**
  1. 把 **bull q35 no-deploy governance blocker** 明確 propagated 到 live governance / summary / docs（不能只停在 q35 audit artifact）；
  2. 維持 `feat_4h_dist_swing_low` 的 secondary structure mix 定位，不再回到 structure closure 敘事；
  3. 維持 profile governance / `fin_netflow` auth blocker / sparse-source history blockers 的零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **bull q35 no-deploy governance** 直接相關的真 patch / artifact / verify；
  2. 必須 machine-read 回答：current blocker 是 `unsafe_floor_cross_candidate` / `non-discriminative reweight`，而不是 support shortage 或 boundary 問題；
  3. `q35_scaling_audit.scope_applicability.status`、`q15_support_audit.support_route.verdict`、`leaderboard_feature_profile_probe.alignment.dual_profile_state` 不得回歸漂移。

- **Fallback if fail:**
  - 若 no-deploy blocker 仍只存在 audit、未 propagated 到主要治理 surface，下一輪直接 patch predictor / summary contract，把該 lane 顯式標成 deployment-blocked；
  - 若 current live row 離開 q35 lane，下一輪先切換到 current bucket blocker，q35 僅保留 reference-only；
  - 若 next run 沒有新 patch 只剩報告，視為 `HEARTBEAT FAILED: NO FORWARD PROGRESS`。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 no-deploy governance contract 再被擴大到 predictor / API surface）

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
     則下一輪不得再追 `dist_swing_low` closure、單點 `bias50` closure、或 base-stack 權重微調；必須直接處理 **bull q35 no-deploy governance blocker** 的主路徑。 
