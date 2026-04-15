# ISSUES.md — Current State Only

_最後更新：2026-04-15 10:51 UTC — Heartbeat #1015（本輪新增 q35 scope-applicability contract，避免 q35 bias50 audit 在 live row 離開 q35 時被誤判成當輪主 blocker；目前 live row 已回到 exact-supported q35 lane，主 blocker 明確收斂到 bias50 component / trade-floor gap。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 做 `feat_4h_bias50` exact-supported q35 lane component experiment / formula review；
  2. 驗證 profile governance 在 exact-supported lane 下如何收斂；
  3. 維持 q15 boundary replay / source auth blocker / breaker false-positive 零漂移治理。
- **Success gate**
  1. 至少留下 1 個與 bias50 formula review 或 entry floor 改善直接相關的 patch / artifact / verify；
  2. machine-read 回答 bias50 experiment 是否真正提高 entry_quality / allowed_layers；
  3. `q15_boundary_replay` 必須持續證明 boundary 不是主修補路徑。
- **Fallback if fail**
  - 若 bias50 experiment 仍無法跨過 floor，下一輪改查 pulse / base mix / support accumulation 聯合路徑；
  - 若又回去談 q15 boundary，視為 regression；
  - 若沒有 bias50 component artifact，升級為 trade-floor blocker。

### 本輪承接結果
- **已處理**
  - 新增 q35 scope-applicability 機制：
    - `scripts/hb_q35_scaling_audit.py`
    - `scripts/hb_parallel_runner.py`
    - `tests/test_hb_parallel_runner.py`
    - `ARCHITECTURE.md`
  - q35 artifact 現在會明確輸出 `scope_applicability.{status,active_for_current_live_row,...}`，避免 q35 calibration 在 live row 其實不在 q35 時被誤寫成主路徑。
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py -q` → **24 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1015` → **通過**
- **本輪 machine-read 結論**
  - `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
  - `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`
  - `q15_support_audit.support_route.verdict = exact_bucket_supported`
  - `q15_support_audit.floor_cross_legality.verdict = legal_component_experiment_after_support_ready`
  - `q15_boundary_replay.verdict = boundary_replay_not_applicable`
- **本輪明確不做**
  - 不放寬 runtime gate；
  - 不把 q15 boundary replay 重新升回主 patch；
  - 不把 `fin_netflow` auth blocker 混寫成 bias50 / q35 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_q35_scaling_audit.py`：新增 `scope_applicability`，把 q35 audit 明確標成 live-active 或 reference-only。
  - `scripts/hb_parallel_runner.py`：fast heartbeat summary / console 現在會同步帶出 q35 applicability，避免治理焦點漂移。
  - `tests/test_hb_parallel_runner.py`：新增 non-q35 row reference-only 覆蓋，並鎖住 diagnostics 解析。
  - `ARCHITECTURE.md`：同步 q35 scope-applicability contract。
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py -q` → **24 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1015`
- **已刷新 artifacts**
  - `data/heartbeat_1015_summary.json`
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
- Heartbeat #1015：
  - Raw / Features / Labels：**21682 / 13111 / 43362**
  - 本輪增量：**+1 raw / +1 feature / +1 label**
  - canonical target `simulated_pyramid_win`：**0.5786**
  - 240m labels：**21743 rows / target_rows 12821 / lag_vs_raw 約 3.1h**
  - 1440m labels：**12534 rows / target_rows 12534 / lag_vs_raw 約 23.2h**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**22/30 pass**
- Regime IC：**Bear 5/8 / Bull 6/8 / Chop 6/8**
- drift primary window：**recent 250**
  - alerts：`label_imbalance`, `regime_concentration`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 97.2%**
  - win_rate：**0.9520**
  - avg_quality：**0.6448**
  - avg_pnl：**+0.0204**
  - avg_drawdown_penalty：**0.0421**
- 判讀：canonical lane 健康，當前卡點不是 drift，而是 **exact-supported q35 lane 仍低於 trade floor**。

### Live contract / q35 / q15 現況
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - entry_quality_label：**D**
  - decision_quality_label：**B**
  - decision_quality scope：**`regime_label+regime_gate+entry_quality_label`**（rows=`58`）
  - expected_win_rate / quality：**0.8966 / 0.5976**
  - allowed_layers：**0 → 0**
  - `allowed_layers_reason = entry_quality_below_trade_floor`
- `data/q35_scaling_audit.json`
  - `scope_applicability.status = current_live_q35_lane_active`
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `segmented_calibration.status = formula_review_required`
  - `segmented_calibration.recommended_mode = exact_lane_formula_review`
  - `counterfactuals.gate_allow_only_changes_layers = false`
- `data/q15_support_audit.json`
  - `support_route.verdict = exact_bucket_supported`
  - `current_live_structure_bucket = CAUTION|structure_quality_caution|q35`
  - `current_live_structure_bucket_rows = 58`
  - `floor_cross_legality.verdict = legal_component_experiment_after_support_ready`
  - `best_single_component = feat_4h_bias50`
  - `remaining_gap_to_floor = 0.0644`
  - `best_single_component_required_score_delta = 0.2147`
- `data/q15_bucket_root_cause.json`
  - `verdict = current_row_already_above_q35_boundary`
  - `candidate_patch_type = support_accumulation`
  - `candidate_patch_feature = feat_4h_dist_swing_low`
- `data/q15_boundary_replay.json`
  - `verdict = boundary_replay_not_applicable`
- 判讀：**q15 support 已恢復、boundary replay 持續關閉；主 blocker 已收斂到 q35 exact-supported lane 的 bias50 / trade-floor gap。**

### Profile split / governance / blockers
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard：`core_plus_macro`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - global shrinkage：`core_only`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
  - `profile_split.verdict = dual_role_required`
- `fin_netflow`
  - coverage：**0.0%**
  - latest status：**auth_missing**
  - archive_window_coverage：**0.0% (0/1806)**
- 判讀：profile split 仍未收斂，但優先序低於 q35 bias50 floor-gap；`fin_netflow` 仍是獨立外部 auth blocker。

---

## 目前有效問題

### P1. exact-supported q35 lane 仍低於 trade floor，主 blocker 是 `feat_4h_bias50` formula review / component experiment
**現象**
- `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
- `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`
- `q15_support_audit.support_route.verdict = exact_bucket_supported`
- live `entry_quality = 0.4856`，`allowed_layers = 0`
- `best_single_component = feat_4h_bias50`
- `remaining_gap_to_floor = 0.0644`
- `best_single_component_required_score_delta = 0.2147`

**判讀**
- q35 路徑現在重新成為 live-active，不再只是 reference-only；
- support 已達標，下一輪可以正式做 deployment-grade bias50 component experiment；
- 但本輪尚未證明提高 bias50 後 `entry_quality / allowed_layers` 真的改善，因此 blocker 仍在。

---

### P1. post-threshold profile governance stalled：leaderboard / train / global shrinkage 仍三套語義
**現象**
- leaderboard：`core_plus_macro`
- train：`core_plus_macro_plus_4h_structure_shift`
- global shrinkage：`core_only`
- `dual_profile_state = post_threshold_profile_governance_stalled`

**判讀**
- exact-supported live bucket 已回來，但 production profile 與 global shrinkage winner 仍未完成角色邊界收斂；
- 仍需保留 dual-role governance，但優先序低於 bias50 floor-gap 修補。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `coverage = 0.0%`
- `latest status = auth_missing`
- `archive_window_coverage = 0.0% (0/1806)`

**判讀**
- 仍是外部憑證 blocker；
- 不可與 q35 / bias50 / profile split 混寫。

---

## 本輪已清掉的問題

### RESOLVED. q35 bias50 audit 會在 live row 不在 q35 時誤導 heartbeat 主焦點
**修前**
- q35 audit 沒有 machine-read scope applicability；
- heartbeat 只能看到 q35 verdict，無法分辨它是當前 live blocker 還是 reference-only artifact。

**本輪 patch + 證據**
- `scripts/hb_q35_scaling_audit.py`：新增 `scope_applicability`
- `scripts/hb_parallel_runner.py`：summary / console 帶出 applicability
- `tests/test_hb_parallel_runner.py`：新增 non-q35 reference-only 覆蓋
- `python -m pytest tests/test_hb_parallel_runner.py -q` → **24 passed**
- `python scripts/hb_parallel_runner.py --fast --hb 1015`
  - `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`

**狀態**
- **已修復**：heartbeat 現在能 machine-read q35 結論是否真的作用於 current live row，避免治理焦點漂移。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 q35 bias50 audit 加上 scope-applicability contract，鎖住 q35 結論何時可當 live blocker。** ✅
2. **確認 current live row 已回到 exact-supported q35 lane，主 blocker 正式收斂到 bias50 formula review / floor-gap。** ✅
3. **維持 profile split / fin_netflow auth blocker / q15 boundary replay 的次級治理定位。** ✅

### 本輪不做
- 不直接 relax runtime gate；
- 不回 q15 boundary repair；
- 不把 source auth blocker 重新包裝成 q35 問題。

---

## Next gate

- **Next focus:**
  1. 對 `feat_4h_bias50` 做 **exact-supported q35 lane deployment-grade component experiment**，直接驗證 `entry_quality` 能否跨過 `0.55`、`allowed_layers` 能否 > 0；
  2. 釐清 `core_plus_macro` / `core_plus_macro_plus_4h_structure_shift` / `core_only` 在 exact-supported lane 下的角色邊界；
  3. 維持 `q15_boundary_replay / fin_netflow auth blocker / breaker false-positive` 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **bias50 component experiment / floor-gap closure** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答：bias50 experiment 後 `entry_quality` 是否 ≥ `0.55`、`allowed_layers` 是否 > 0；
  3. `q35_scaling_audit.scope_applicability.status` 與 `q15_support_audit.support_route.verdict` 不得漂移。

- **Fallback if fail:**
  - 若 bias50 單點 experiment 仍無法跨過 floor，下一輪升級為 **bias50 + pulse/base mix 聯合問題**；
  - 若 q35 applicability 又回 reference-only，下一輪必須先處理 current bucket support / component 問題，不得硬套 q35 結論；
  - 若沒有新 patch 只剩報告，視為 `HEARTBEAT FAILED: NO FORWARD PROGRESS`。

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
     則下一輪不得再回 q15 boundary / generic q35 敘事；必須直接做 **bias50 component experiment / trade-floor closure / profile governance 收斂**。
