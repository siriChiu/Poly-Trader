# ISSUES.md — Current State Only

_最後更新：2026-04-15 18:10 UTC — Heartbeat #1024（本輪已修正 **q15_support_audit 把 standby q15 route 誤寫成 current-live deployment closure** 的治理錯誤：現在 q15 audit 會 machine-read `scope_applicability`，當 current live row 已回到 q35 lane 時，會明確降成 `exact_supported_component_experiment_ready_but_current_live_not_q15`，避免心跳主焦點被錯誤帶回 q15。新的主 blocker 已收斂為：**current bull q35 live lane 仍停在 `entry_quality=0.4196 / allowed_layers=0`，但 q35 audit 已證明存在保留正向 discrimination 的 base-stack redesign 候選可把 current row 推到 `0.5505 / 1 layer`；下一輪必須做 runtime 契約驗證，而不是再把 q15 standby route 當主戰場。**)_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 驗證 q15 exact-supported component deployment；
  2. 保持 q35 drift 已解狀態，改追 current live floor gap；
  3. 之後再收斂 post-threshold profile governance。
- **Success gate**
  1. 至少留下 1 個與 q15 exact-supported component verify 直接相關的 patch / artifact / verify；
  2. `q15_support_audit.component_experiment.machine_read_answer.preserves_positive_discrimination` 不得再停在 `not_measured_requires_followup_verify`；
  3. `live_predict_probe` / `live_decision_quality_drilldown` / `q15_support_audit` / heartbeat summary 必須對同一條 live row 給出一致結論。
- **Fallback if fail**
  - 若 q15 verify 失敗或失去 discrimination，降回 research-only / no-deploy；
  - 若 current live row 離開 q35/q15 path，退回 support accumulation / bucket governance；
  - 若沒有新 patch，只剩報告，視為 `HEARTBEAT FAILED: NO FORWARD PROGRESS`。

### 本輪承接結果
- **已處理**
  - `scripts/hb_q15_support_audit.py`
    - 新增 `scope_applicability.{status,active_for_current_live_row,current_structure_bucket,target_structure_bucket,reason}`；
    - 當 current live row 不在 q15 lane 時，`component_experiment.verdict` 會改成 `exact_supported_component_experiment_ready_but_current_live_not_q15`；
    - `preserves_positive_discrimination_status` 會改成 `not_applicable_current_live_not_q15_lane`，阻止 q15 standby artifact 被誤當成 current-live deployment closure。
  - `scripts/hb_parallel_runner.py`
    - `collect_q15_support_audit_diagnostics()` 與 console summary 現在會同步帶出 `scope_applicability`；
    - fast heartbeat 可直接 machine-read 看出 q15 lane 是否真的 active。
  - `tests/test_q15_support_audit.py`
    - 補上 q15 active lane 與 q35 current-live standby lane 的 regression tests。
  - `ARCHITECTURE.md`
    - 補上 q15 support audit 的 `scope_applicability` / standby-route contract，避免之後再把 inactive q15 lane 誤寫成 current-live deployment。
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py -q` → **37 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1024` → **通過**
- **本輪 machine-read 結論**
  - `q15_support_audit.scope_applicability.status = current_live_not_q15_lane`
  - `q15_support_audit.scope_applicability.active_for_current_live_row = false`
  - `q15_support_audit.component_experiment.verdict = exact_supported_component_experiment_ready_but_current_live_not_q15`
  - `q15_support_audit.component_experiment.machine_read_answer.preserves_positive_discrimination_status = not_applicable_current_live_not_q15_lane`
  - **結論：上輪把 q15 exact-supported component verify 當成 current-live 主路徑已不再成立；本輪已把這個治理錯位修掉。**
- **本輪明確不做**
  - 不把 q15 standby route 直接併進 runtime；
  - 不先處理 sparse-source auth，避免搶走 current bull q35 live lane 的主頻寬；
  - 不把 profile split 當第一優先，因為 live current row 的 q35 runtime verify 更接近 deployment closure。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_q15_support_audit.py`：新增 q15 `scope_applicability` 與 inactive-q15 standby verdict。
  - `scripts/hb_parallel_runner.py`：fast heartbeat 直接揭露 q15 lane active/inactive 狀態。
  - `tests/test_q15_support_audit.py`：鎖住 q15-active / q35-current-live standby 的 machine-read 契約。
  - `ARCHITECTURE.md`：同步 q15 support audit 新治理契約。
- **Tests（已通過）**
  - `python -m pytest tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py -q` → **37 passed**
- **Runtime verify（已通過）**
  - `python scripts/hb_parallel_runner.py --fast --hb 1024`
- **已刷新 artifacts**
  - `data/heartbeat_1024_summary.json`
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
- Heartbeat #1024：
  - Raw / Features / Labels：**21776 / 13205 / 43520**
  - 本輪增量：**+1 raw / +1 feature / +24 labels**
  - canonical target `simulated_pyramid_win`：**0.5797**
  - 240m labels：**21883 rows / target_rows 12961 / lag_vs_raw 約 3.0h**
  - 1440m labels：**12552 rows / target_rows 12552 / lag_vs_raw 約 23.1h**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**27/30 pass**
- Regime IC：**Bear 5/8 / Bull 6/8 / Chop 5/8**
- drift primary window：**recent 250**
  - alerts：`label_imbalance`, `regime_concentration`, `regime_shift`
  - interpretation：**distribution_pathology**
  - dominant_regime：**bull 100.0%**
  - win_rate：**0.8960**
  - avg_quality：**0.5887**
  - avg_pnl：**+0.0187**
  - avg_drawdown_penalty：**0.0604**
- 判讀：近期 bull pocket 仍極度集中；訊號強，但 runtime deployment 要依 exact live lane 證據，而不是把 bull pocket 直接泛化。

### Live contract / q35 / q15 現況
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - current live structure bucket：**CAUTION|structure_quality_caution|q35**
  - `entry_quality = 0.4196`
  - `entry_quality_label = D`
  - `allowed_layers = 0 -> 0`
  - `decision_quality_calibration_scope = regime_label+regime_gate+entry_quality_label`
  - `expected_win_rate = 0.7059`, `expected_pyramid_quality = 0.3988`
- `data/q35_scaling_audit.json`
  - `scope_applicability.status = current_live_q35_lane_active`
  - `deployment_grade_component_experiment.verdict = runtime_patch_improves_but_still_below_floor`
  - `deployment_grade_component_experiment.runtime_entry_quality = 0.4196`
  - `deployment_grade_component_experiment.runtime_remaining_gap_to_floor = 0.1304`
  - `deployment_grade_component_experiment.q35_discriminative_redesign_applied = false`
  - `base_stack_redesign_experiment.verdict = base_stack_redesign_discriminative_reweight_crosses_trade_floor`
  - `base_stack_redesign_experiment.best_discriminative_candidate.current_entry_quality_after = 0.5505`
  - `base_stack_redesign_experiment.best_discriminative_candidate.allowed_layers_after = 1`
  - `base_stack_redesign_experiment.machine_read_answer = {entry_quality_ge_0_55=true, allowed_layers_gt_0=true, positive_discriminative_gap=true}`
  - 判讀：**safe discriminative q35 redesign 已存在，但 runtime 尚未真正套用；這是目前最接近 deployment 的主路徑。**
- `data/q15_support_audit.json`
  - `scope_applicability.status = current_live_not_q15_lane`
  - `scope_applicability.active_for_current_live_row = false`
  - `support_route.verdict = exact_bucket_supported`
  - `component_experiment.verdict = exact_supported_component_experiment_ready_but_current_live_not_q15`
  - `component_experiment.machine_read_answer.preserves_positive_discrimination_status = not_applicable_current_live_not_q15_lane`
  - 判讀：**q15 support 已達標，但目前只是 standby route readiness，不是 current-live deployment closure。**
- `data/q15_bucket_root_cause.json`
  - `verdict = current_row_already_above_q35_boundary`
  - `candidate_patch_type = support_accumulation`
  - `candidate_patch_feature = feat_4h_dist_swing_low`
  - 判讀：**當前 live row 已不在 q15 邊界修補情境；q15 主題已退為背景治理。**

### Profile split / governance / blockers
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard：`core_plus_macro`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - global recommended：`core_plus_4h`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
  - `live_current_structure_bucket_rows = 51`
  - `support_governance_route = exact_live_bucket_supported`
- sparse-source blockers
  - `fin_netflow`：**auth_missing / coverage 0.0% / archive_window_coverage 0.0% (0/1897)**
  - 其餘 blocked sparse sources：仍以 **history gap / snapshot archive** 為主

---

## 目前有效問題

### P1. q35 discriminative redesign 已證明可跨 floor，但 runtime 尚未套用到 current live row
**現象**
- `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active`
- `deployment_grade_component_experiment.runtime_entry_quality = 0.4196`
- `base_stack_redesign_experiment.best_discriminative_candidate.current_entry_quality_after = 0.5505`
- `base_stack_redesign_experiment.best_discriminative_candidate.allowed_layers_after = 1`
- `base_stack_redesign_experiment.machine_read_answer.positive_discriminative_gap = true`
- `live_predict_probe.q35_discriminative_redesign_applied = false`

**判讀**
- root cause 已不是「找不到可保留 discrimination 的候選」；
- 真 blocker 變成：**runtime contract 尚未把已驗證的 q35 discriminative candidate 真正套到 live path**；
- 下一輪要驗證的是：套用後是否能讓 `live_predict_probe` / `q35_scaling_audit` / `heartbeat summary` 一致 machine-read 成 `entry_quality >= 0.55`、`allowed_layers > 0`，且不引入新的 guardrail regression。

---

### P1. q15 exact-supported route 現在只是一條 standby route，不能再佔據 current-live 主焦點
**現象**
- `q15_support_audit.scope_applicability.status = current_live_not_q15_lane`
- `q15_support_audit.component_experiment.verdict = exact_supported_component_experiment_ready_but_current_live_not_q15`
- `q15_bucket_root_cause.verdict = current_row_already_above_q35_boundary`

**判讀**
- q15 support ready 仍是有價值的備援證據；
- 但它不再是當前 live row 的 active deployment 路徑；
- 下一輪若 live row 仍停在 q35，禁止再把 q15 standby artifact 當成主 closure 目標。

---

### P1. post-threshold profile governance 仍未收斂
**現象**
- leaderboard：`core_plus_macro`
- train：`core_plus_macro_plus_4h_structure_shift`
- global shrinkage winner：`core_plus_4h`
- `dual_profile_state = post_threshold_profile_governance_stalled`

**判讀**
- exact support 已恢復，問題已不是 support shortage；
- 但在 q35 current-live runtime verify 完成前，它仍低於 q35 runtime 套用優先級。

---

### P1. sparse-source blocker 仍存在，`fin_netflow` 仍是 auth blocker
**現象**
- `fin_netflow`：`auth_missing`, `coverage=0.0%`, `archive_window_coverage_pct=0.0%`

**判讀**
- 仍是 source blocker；
- 但本輪主路徑不是 sparse-source，而是 q35 discriminative runtime verify。

---

## 本輪已清掉的問題

### RESOLVED. q15 support audit 誤把 inactive q15 lane 包裝成 current-live deployment closure
**修前**
- 當 current live row 已回到 q35 lane 時，`q15_support_audit` 仍可能輸出 `exact_supported_component_experiment_ready`；
- 文件與 heartbeat 容易被誤導成「下一輪主焦點仍是 q15 deployment verify」。

**本輪 patch + 證據**
- `scripts/hb_q15_support_audit.py`：新增 `scope_applicability`，inactive q15 lane 會改成 `exact_supported_component_experiment_ready_but_current_live_not_q15`
- `scripts/hb_parallel_runner.py`：summary 直接打印 `scope=current_live_not_q15_lane active=False`
- `python -m pytest tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py -q` → **37 passed**
- `python scripts/hb_parallel_runner.py --fast --hb 1024` → **通過**

**狀態**
- **已修復**：本輪之後，q15 audit 不再能在 q35 current-live 情境下假裝自己是 deployment closure。

---

## 本輪決策（收斂版）

### 策略後果表
| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 繼續把主焦點放在 q15 exact-supported component verify | 延續上輪題目，文件改動最少 | 會被 inactive q15 lane 誤導，對 current-live row 沒有直接 closure | 治標 | 只有 current live row 仍在 q15 lane 時 | ❌ 不建議 |
| 先修正 q15 audit 語義，明確標示 standby vs active lane，再把主焦點轉回 q35 current-live verify | 先消除治理假訊號，再讓下一輪直接吃到 live blocker | 需要同步 patch script / runner / docs | 治本 | current live row 已是 q35，且 q15 audit 仍在誤導焦點 | ✅ 推薦 |
| 直接跳去處理 sparse-source / profile governance | 可提前清理其他噪音 | 會錯過最接近 deployment 的 q35 live path | 治標 | q35 runtime path 尚未有明確 candidate 時 | ❌ 不建議 |

### 效益前提驗證
| 情境 | 效益 |
|---|---|
| current live row 仍是 `CAUTION|structure_quality_caution|q35`，且 q35 audit 已給出 `best_discriminative_candidate.entry_quality_after >= 0.55` | ✅ 直接把下一輪聚焦到 q35 discriminative runtime apply / verify |
| current live row 回到 q15 lane | ⚠️ q15 standby route 重新變成 active，可再開啟 q15 deployment verify |
| q35 candidate 套用後產生新的 guardrail / discrimination regression | ❌ 需退回 audit-only，不可直接部署 |

### 本輪要推進的 3 件事
1. 修掉 q15 audit 把 standby route 誤寫成 current-live closure。 ✅
2. 重新 machine-read current live 到底是 q35 還是 q15 active lane。 ✅
3. 把下一輪主路徑從 q15 verify 轉回 q35 discriminative runtime verify。 ✅

### 本輪不做
- 不把 q15 standby route 直接合併進 predictor runtime；
- 不搶先做 sparse-source auth blocker；
- 不先收斂 profile split 大重構。

---

## Next gate

- **Next focus:**
  1. 以 `q35_scaling_audit.base_stack_redesign_experiment.best_discriminative_candidate` 為主，實作 / 驗證 **current bull q35 discriminative runtime apply**；
  2. 驗證套用後 `live_predict_probe` / `q35_scaling_audit` / heartbeat summary 是否一致 machine-read 成 `entry_quality >= 0.55`、`allowed_layers > 0`、`positive_discriminative_gap = true`；
  3. q35 runtime verify 完成後，再收斂 leaderboard / train / global 的 post-threshold profile governance。

- **Success gate:**
  1. 下一輪至少留下 1 個與 **q35 discriminative runtime apply / verify** 直接相關的 code patch / artifact / verify；
  2. 必須 machine-read 回答：
     - `q35_scaling_audit.scope_applicability.active_for_current_live_row = true`
     - `q35_scaling_audit.base_stack_redesign_experiment.machine_read_answer = {entry_quality_ge_0_55=true, allowed_layers_gt_0=true, positive_discriminative_gap=true}`
     - `live_predict_probe.q35_discriminative_redesign_applied = true`
     - `live_predict_probe.allowed_layers > 0`
  3. `q15_support_audit.scope_applicability.active_for_current_live_row` 若仍為 `false`，文件不得再把 q15 standby route 寫成 current-live 主 closure。

- **Fallback if fail:**
  - 若 q35 discriminative candidate 套用後出現 guardrail / discrimination regression，下一輪降回 audit-only，不可直接部署；
  - 若 current live row 離開 q35，重新依 `scope_applicability` 收斂 active lane；
  - 若沒有新 patch、只剩報告，視為 `HEARTBEAT FAILED: NO FORWARD PROGRESS`。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 q35 runtime apply 契約正式升級）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1024_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若同時成立：
     - `q35_scaling_audit.scope_applicability.active_for_current_live_row = true`
     - `q35_scaling_audit.base_stack_redesign_experiment.machine_read_answer.entry_quality_ge_0_55 = true`
     - `q35_scaling_audit.base_stack_redesign_experiment.machine_read_answer.allowed_layers_gt_0 = true`
     - `q15_support_audit.scope_applicability.active_for_current_live_row = false`
     則下一輪**不得再把主焦點放回 q15 standby route**；必須直接做 **q35 discriminative runtime apply + verify**。
