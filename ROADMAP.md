# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 08:59 UTC — Heartbeat #1013（q15 support 已恢復到 exact-supported q35 lane；主路徑正式從 q15 boundary repair 轉向 bias50 / trade-floor component 修補。）_

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
  - `issues.json`
  - numbered summary：`data/heartbeat_1013_summary.json`

### 本輪新完成：q15 boundary replay artifact 正式進入 fast heartbeat
- `scripts/hb_q15_boundary_replay.py`
  - 新增 q15 boundary replay + `feat_4h_bb_pct_b` minimal counterfactual artifact
  - machine-read：`boundary_replay / component_counterfactual / verdict / next_action / verify_next / carry_forward`
- `scripts/hb_parallel_runner.py`
  - fast heartbeat 自動刷新 q15 boundary replay artifact，並寫入 summary
- `tests/test_q15_boundary_replay.py`
  - 鎖住「boundary 只是 rebucket / bb_pct_b 不是 floor fix」判讀
- `tests/test_hb_parallel_runner.py`
  - 鎖住 q15 replay diagnostics 與 runner order：`leaderboard -> q15 support -> q15 root-cause -> q15 replay`
- `ARCHITECTURE.md`
  - 新增 q15 boundary-replay contract

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_q15_boundary_replay.py tests/test_q15_bucket_root_cause.py tests/test_hb_parallel_runner.py -q` → **26 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1013` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#1013）：
  - Raw / Features / Labels = **21589 / 13018 / 43348**
  - simulated_pyramid_win = **0.5756**
- label freshness 正常：
  - 240m lag 約 **3.4h**
  - 1440m lag 約 **23.1h**

### IC / drift / live runtime
- Global IC：**19/30**
- TW-IC：**19/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 6/8**
- drift primary window：**250**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**bull 94.4%**
- live predictor：
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - entry_quality_label：**D**
  - decision_quality_label：**B**
  - allowed layers：**0 → 0**
  - reason：**entry_quality_below_trade_floor**

### q15 / q35 / component 現況
- `q15_support_audit`
  - `support_route.verdict = exact_bucket_supported`
  - `current_live_structure_bucket = CAUTION|structure_quality_caution|q35`
  - `current_live_structure_bucket_rows = 76`
  - `best_single_component = feat_4h_bias50`
  - `remaining_gap_to_floor = 0.1918`
- `q15_bucket_root_cause`
  - `verdict = current_row_already_above_q35_boundary`
  - `candidate_patch_type = support_accumulation`
  - `candidate_patch_feature = feat_4h_bb_pct_b`
- `q15_boundary_replay`
  - `verdict = boundary_replay_not_applicable`
  - `component_counterfactual.verdict = bucket_proxy_only_not_trade_floor_fix`
- `q35_scaling_audit`
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`
- 治理結論：
  - **已完成**：q15 support blocker 已解除，boundary replay 是否仍值得修補也已 machine-read 關閉；
  - **未完成**：exact-supported q35 lane 仍低於 trade floor，runtime 依然 0 layers；
  - **下一步**：直接做 bias50 / exact-supported component experiment，而不是再回 q15 boundary。

### Profile split / breaker / source blocker 現況
- profile governance：
  - leaderboard：`core_plus_macro`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - global shrinkage：`core_only`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
- circuit breaker：
  - `verdict = mixed_horizon_false_positive`
  - aligned 1440m live horizon：`release_ready = true`
- `fin_netflow`：**auth_missing** / coverage **0.0%**

---

## 當前主目標

### 目標 A：把 exact-supported q35 lane 從 hold-only 推進到可驗證的 component experiment
目前已確認：
- q15 support 已恢復為 `exact_bucket_supported`；
- current live structure bucket 已是 `CAUTION|structure_quality_caution|q35`；
- support 已足，但 entry quality 仍是 **0.3582**，低於 trade floor；
- `feat_4h_bias50` 是目前最有希望的單點 component。

下一步主目標：
- **做 `feat_4h_bias50` exact-supported q35 lane component experiment / formula review，回答它能否在不破壞 guardrail 的前提下把 entry quality 推過 floor。**

### 目標 B：停止把 q15 boundary / `feat_4h_bb_pct_b` 誤當主修補路徑
目前已確認：
- `q15_boundary_replay.verdict = boundary_replay_not_applicable`
- `q15_boundary_replay.component_counterfactual.verdict = bucket_proxy_only_not_trade_floor_fix`
- `q15_bucket_root_cause.verdict = current_row_already_above_q35_boundary`

下一步主目標：
- **將 q15 boundary 與 `feat_4h_bb_pct_b` 固定降級成 reference-only / bucket-proxy 診斷，不再讓 heartbeat 回到過時路徑。**

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
- 持續維持零漂移，但不讓它們重新搶走 trade-floor component 修補的主頻寬。

---

## 接下來要做

### 1. 做 `feat_4h_bias50` exact-supported q35 lane experiment
要做：
- 檢查 `bias50_formula_may_be_too_harsh` 是否可轉成 guarded formula review；
- 驗證 `feat_4h_bias50` 拉升後：
  - entry quality 是否跨過 `0.55`；
  - allowed layers 是否 > 0；
  - runtime / guardrail 是否不回歸；
- 產出 machine-readable JSON + markdown
- 驗證 fast heartbeat summary 能直接摘取 `verdict / floor delta / layers_after`

### 2. 鎖住 q15 boundary path 已降級
要做：
- 持續檢查：
  - `q15_support_audit.support_route.verdict`
  - `q15_bucket_root_cause.verdict`
  - `q15_boundary_replay.verdict`
  - `q15_boundary_replay.component_counterfactual.verdict`
- 若這四項仍是本輪狀態，不再回 q15 boundary replay 當主路徑

### 3. 做 post-threshold profile governance 收斂
要做：
- 在 exact-supported lane 下重新比較：
  - `leaderboard_selected_profile`
  - `train_selected_profile`
  - `global_recommended_profile`
  - `dual_profile_state`
- 但在 bias50 component 沒驗前，不把 profile 收斂排到第一優先

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 q35 / bias50 / profile 問題

---

## 暫不優先

以下本輪後仍不排最前面：
- 回頭做 q15 boundary review
- 把 `feat_4h_bb_pct_b` 當 floor-gap 主修補
- 再次調查 mixed-horizon breaker
- UI 美化與 fancy controls

原因：
> 當前真正的 live blocker 已經收斂成 **exact-supported q35 lane 的 trade-floor / bias50 component 問題**；q15 support 已解，boundary replay 已 machine-read 關閉。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **bias50 formula review 或 exact-supported q35 component experiment** 直接相關的真 patch / run / verify。
2. `q15_support_audit / q15_bucket_root_cause / q15_boundary_replay / heartbeat summary` 對 q15/q35/support/floor 的描述必須零漂移。
3. mixed-horizon circuit breaker 不得回歸。
4. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 做 `feat_4h_bias50` exact-supported q35 lane component experiment / formula review；
  2. 驗證 profile governance 在 exact-supported lane 下如何收斂；
  3. 維持 q15 boundary replay / source auth blocker / breaker false-positive 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **bias50 formula review 或 entry floor 改善** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答 bias50 experiment 是否真正提高 entry_quality / allowed_layers；
  3. `q15_boundary_replay` 必須持續證明 boundary 不是主修補路徑，且 `feat_4h_bb_pct_b` 仍不得被誤判成 floor fix。

- **Fallback if fail:**
  - 若 bias50 experiment 仍無法跨過 floor，下一輪改查 pulse / base mix / support accumulation 聯合路徑；
  - 若沒有 exact-supported lane 的真 patch / verify，又回去談 q15 boundary，視為 regression；
  - 若 next run 仍沒有 bias50 component artifact，升級為 trade-floor blocker。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 bias50 formula review contract 被正式採納）

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
     則下一輪不得再回 q15 boundary / bb_pct_b proxy repair；必須直接處理 **bias50 formula review / exact-supported q35 component experiment / profile governance 收斂**。
