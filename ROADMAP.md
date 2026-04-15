# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 18:10 UTC — Heartbeat #1024（本輪已把 **q15 exact-supported standby route 與 current-live q35 lane** 正式拆開：q15 audit 現在會明確標示 `scope_applicability`，不再把 inactive q15 lane 誤寫成 current-live deployment closure。新的主路徑已收斂為：**current bull q35 live lane 的 discriminative redesign runtime verify**——因為 q35 audit 已證明存在保留正向 discrimination 的候選可把 current row 推到 `entry_quality=0.5505 / allowed_layers=1`，但 live predictor 目前仍停在 `0.4196 / 0 layers`。_)

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
  - `data/leaderboard_feature_profile_probe.json`
  - numbered summary：`data/heartbeat_1024_summary.json`

### 本輪新完成：q15 support audit active-vs-standby lane 契約化
- `scripts/hb_q15_support_audit.py`
  - 新增 `scope_applicability`；
  - 當 current live row 不在 q15 lane 時，artifact 會輸出 `current_live_not_q15_lane`；
  - `component_experiment` 會改成 `exact_supported_component_experiment_ready_but_current_live_not_q15`，避免誤判為 current-live closure。
- `scripts/hb_parallel_runner.py`
  - q15 summary 現在會打印 `scope=<status> active=<bool>`；
  - fast heartbeat summary 可直接分辨 q15 standby route 與 active q15 lane。
- `tests/test_q15_support_audit.py`
  - 已補 q15-active / q35-current-live standby 的 regression tests。
- `ARCHITECTURE.md`
  - 已同步 q15 support audit 的 `scope_applicability` / standby-route contract。

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py -q` → **37 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1024` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#1024）：
  - Raw / Features / Labels = **21776 / 13205 / 43520**
  - simulated_pyramid_win = **0.5797**
- label freshness 正常：
  - 240m lag 約 **3.0h**
  - 1440m lag 約 **23.1h**
- raw freshness：**約 0.5 分鐘**

### IC / drift / live runtime
- Global IC：**19/30**
- TW-IC：**27/30**
- Regime IC：**Bear 5/8 / Bull 6/8 / Chop 5/8**
- drift primary window：**250**
  - interpretation：**distribution_pathology**
  - dominant regime：**bull 100.0%**
- live predictor：
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - structure_bucket：**CAUTION|structure_quality_caution|q35**
  - entry_quality：**0.4196**
  - entry_quality_label：**D**
  - allowed layers：**0 → 0**
  - decision-quality scope：**regime_label+regime_gate+entry_quality_label**
  - expected_win_rate：**0.7059**
  - expected_quality：**0.3988**

### q35 / q15 / governance 現況
- `q35_scaling_audit`
  - `scope_applicability.status = current_live_q35_lane_active`
  - `deployment_grade_component_experiment.runtime_entry_quality = 0.4196`
  - `deployment_grade_component_experiment.runtime_remaining_gap_to_floor = 0.1304`
  - `deployment_grade_component_experiment.q35_discriminative_redesign_applied = false`
  - `base_stack_redesign_experiment.verdict = base_stack_redesign_discriminative_reweight_crosses_trade_floor`
  - `base_stack_redesign_experiment.best_discriminative_candidate.current_entry_quality_after = 0.5505`
  - `base_stack_redesign_experiment.best_discriminative_candidate.allowed_layers_after = 1`
  - **治理結論**：主問題已從「找 safe candidate」轉成「讓 runtime 真正吃到 safe candidate」。
- `q15_support_audit`
  - `scope_applicability.status = current_live_not_q15_lane`
  - `scope_applicability.active_for_current_live_row = false`
  - `support_route.verdict = exact_bucket_supported`
  - `component_experiment.verdict = exact_supported_component_experiment_ready_but_current_live_not_q15`
  - `preserves_positive_discrimination_status = not_applicable_current_live_not_q15_lane`
  - **治理結論**：q15 support 已 ready，但目前只是 standby route readiness，不是當輪 current-live 主 closure。
- `leaderboard_feature_profile_probe`
  - `leaderboard_selected_profile = core_plus_macro`
  - `train_selected_profile = core_plus_macro_plus_4h_structure_shift`
  - `global_recommended_profile = core_plus_4h`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
  - `live_current_structure_bucket_rows = 51`
  - **治理結論**：support 已過 threshold；profile split 仍待收斂，但排在 q35 runtime verify 之後。

### Source blockers
- `fin_netflow`：**auth_missing / coverage 0.0%**
- 其餘 sparse sources：**history gap / archive blocker**

---

## 當前主目標

### 目標 A：把 q35 discriminative redesign 從 audit candidate 推到 live runtime verify
目前已確認：
- current live row 仍是 **bull / CAUTION / q35**；
- q35 audit 的 safe candidate 已可讓 current row 到 **0.5505 / 1 layer**；
- 但 live predictor 目前仍停在 **0.4196 / 0 layers**。

下一步主目標：
- **把 q35 discriminative base-stack candidate 做成真正的 runtime apply / verify，並確認不破壞 positive discrimination。**

### 目標 B：維持 q15 standby route 的真實語義，不讓它再 hijack current-live 主焦點
目前已確認：
- q15 support 已達標；
- 但 current live row 已不在 q15 lane；
- q15 artifact 現在只能描述 standby route readiness。

下一步主目標：
- **保持 q15 artifact 的 truthful governance，只有在 current live row 回到 q15 lane 時才重新升級成 active verify。**

### 目標 C：收斂 post-threshold profile governance
目前已確認：
- leaderboard / train / global 三條 profile 語義仍分裂；
- 但 exact support 已恢復，這已不再是「support 未達標」問題。

下一步主目標：
- **等 q35 runtime verify 完成後，再把 post-threshold profile governance 收斂成單一可解讀 contract。**

---

## 接下來要做

### 1. 套用並驗證 q35 discriminative runtime candidate
要做：
- 讓 live predictor 真正消費 `q35_scaling_audit.base_stack_redesign_experiment.best_discriminative_candidate`；
- machine-read 補齊：
  - `q35_discriminative_redesign_applied = true`
  - `entry_quality >= 0.55`
  - `allowed_layers > 0`
  - `positive_discriminative_gap = true`
- 驗證：
  - `live_predict_probe`
  - `live_decision_quality_drilldown`
  - `q35_scaling_audit`
  - fast heartbeat summary

### 2. 維持 q15 standby route 語義正確
要做：
- 保持 `q15_support_audit.scope_applicability` 為單一真相來源；
- 若 current live row 仍是 q35，文件 / heartbeat 不得再把 q15 standby route 寫成主 closure；
- 若 current live row 回到 q15，再重新開啟 q15 deployment verify。

### 3. 收斂 post-threshold profile governance
要做：
- 等 q35 runtime verify 完成後，再處理：
  - leaderboard selected profile
  - train selected profile
  - global shrinkage winner
- 目標是把 `post_threshold_profile_governance_stalled` 收斂成 machine-read 可執行結論。

---

## 暫不優先

以下本輪後仍不排最前面：
- 再回頭把 q15 standby route 當主題重做一遍
- 稀疏來源 auth / archive blocker 主修
- 先做 profile governance 大重構

原因：
> 本輪已確認 current-live 主路徑是 **q35 discriminative runtime apply / verify**；其他議題都比這條路徑更遠離 deployment closure。

---

## 成功標準

接下來幾輪工作的成功標準：
1. 下一輪至少留下 1 個與 **q35 discriminative runtime apply / verify** 直接相關的 patch / run / verify。
2. machine-read surface 必須清楚回答：
   - `q35_scaling_audit.scope_applicability.active_for_current_live_row = true`
   - `q35_scaling_audit.base_stack_redesign_experiment.machine_read_answer.entry_quality_ge_0_55 = true`
   - `q35_scaling_audit.base_stack_redesign_experiment.machine_read_answer.allowed_layers_gt_0 = true`
   - `q35_scaling_audit.base_stack_redesign_experiment.machine_read_answer.positive_discriminative_gap = true`
   - `live_predict_probe.q35_discriminative_redesign_applied = true`
3. q35 audit / live predictor / heartbeat summary 對同一條 current live row 必須給出一致可解讀的 deployment 結論。
4. q15 audit 若仍 inactive，必須維持 `current_live_not_q15_lane`，不能再被寫成 current-live closure。
5. 若 q35 runtime verify 成功，下一輪再收斂 profile governance；若失敗，必須明確降級成 audit-only / no-deploy。

---

## Next gate

- **Next focus:**
  1. 驗證 q35 discriminative runtime apply；
  2. 保持 q15 standby route truthfulness，不讓它再搶走主焦點；
  3. 之後再收斂 post-threshold profile governance。

- **Success gate:**
  1. next run 必須留下至少一個與 **q35 discriminative runtime apply / verify** 直接相關的 patch / artifact / verify；
  2. `live_predict_probe.q35_discriminative_redesign_applied` 必須變成 `true`，且 `allowed_layers > 0`；
  3. `live_predict_probe` / `q35_scaling_audit` / `heartbeat summary` 必須對同一條 q35 live row 給出一致結論；
  4. `q15_support_audit.scope_applicability.active_for_current_live_row` 若仍為 `false`，docs 不得再把 q15 standby route 寫成主 closure。

- **Fallback if fail:**
  - 若 q35 redesign 套用後喪失 discrimination 或引發 guardrail regression，下一輪降回 audit-only / no-deploy；
  - 若 current live row 離開 q35，下一輪依 `scope_applicability` 重新選 active lane；
  - 若 next run 沒有新 patch，只剩報告，升級成 governance blocker。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 q35 runtime contract 再擴大）

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
     則下一輪不得再把主焦點放回 q15 standby route；必須直接做 **q35 discriminative runtime apply + verify**。
