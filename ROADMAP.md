# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 16:56 UTC — Heartbeat #1022（本輪已把 **q35 discriminative redesign** 從 audit candidate 升級成 live predictor runtime patch。current bull q35 lane 現在 machine-read 為 **`entry_quality=0.5667 / allowed_layers=1 / q35_discriminative_redesign_applied=true`**。下一輪主路徑不再是「要不要部署 q35 redesign」，而是：**把 q35 audit / runner / docs 的 baseline-runtime surface 對齊**，避免同輪 artifact 互相打架。）_

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
  - numbered summary：`data/heartbeat_1022_summary.json`

### 本輪新完成：q35 discriminative redesign 已進入 live predictor runtime
- `model/predictor.py`
  - 新增 `_maybe_apply_q35_discriminative_redesign()`
  - 只有在 **audit row 與 current live row 完全對齊**、且 machine-read 仍為 `entry_quality_ge_0_55=true / allowed_layers_gt_0=true / positive_discriminative_gap=true` 時，才會套用 audited weights
  - stale artifact / row mismatch 會自動退回 baseline 權重
- `tests/test_api_feature_history_and_predictor.py`
  - 新增 q35 redesign apply / stale-skip regression
- `ARCHITECTURE.md`
  - 已同步 Heartbeat #1022 runtime deploy contract

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q` → **75 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1022` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#1022）：
  - Raw / Features / Labels = **21772 / 13201 / 43480**
  - simulated_pyramid_win = **0.5796**
- label freshness 正常：
  - 240m lag 約 **3.5h**
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
  - entry_quality_label：**C**
  - allowed layers：**1 → 1**
  - entry_quality：**0.5667**
  - `q35_discriminative_redesign_applied = true`
  - calibration scope：**regime_label**
  - expected win rate：**0.875**
  - expected quality：**0.565**

### q35 / q15 / governance 現況
- `q35_scaling_audit`
  - `scope_applicability.status = current_live_q35_lane_active`
  - `base_stack_redesign_experiment.verdict = base_stack_redesign_discriminative_reweight_crosses_trade_floor`
  - `best_discriminative_candidate.current_entry_quality_after = 0.5667`
  - `best_discriminative_candidate.allowed_layers_after = 1`
  - `best_discriminative_candidate.positive_discriminative_gap = true`
  - **但** `deployment_grade_component_experiment.runtime_entry_quality = 0.3142`
  - **治理結論**：deployment patch 已前進，但 q35 audit / runner 仍需把 baseline 與 deployed runtime 分開表達
- `q15_support_audit`
  - `support_route.verdict = exact_bucket_present_but_below_minimum`
  - `current_live_structure_bucket_gap_to_minimum = 1`
  - `component_experiment.verdict = reference_only_until_exact_support_ready`
  - **治理結論**：q15 仍未達 deployment 門檻

### Profile split / source blocker 現況
- profile governance：
  - leaderboard：`core_plus_4h`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
- source blockers：
  - `fin_netflow`：**auth_missing** / coverage **0.0%**
  - 其餘 sparse sources：**history gap / archive blocker**

---

## 當前主目標

### 目標 A：對齊 q35 audit / runner / docs 的 baseline-runtime 雙軌語義
目前已確認：
- live predictor runtime 已吃到 q35 discriminative redesign；
- q35 audit 仍保留 baseline current row，導致同輪出現 `0.5667` vs `0.3142` 的雙軌訊號；
- heartbeat summary 雖然已能看出 runtime 前進，但治理 surface 還沒有明確把這兩條語義拆開。

下一步主目標：
- **讓 q35 audit / summary 顯式區分 baseline current row 與 deployed runtime current row，避免 machine-read surface 自相矛盾。**

### 目標 B：維持 q15 component experiment 為 reference-only，直到 support 達標
目前已確認：
- q15 exact bucket 仍差 **1 row**；
- q15 audit 已能 machine-read 回答 `support_ready=false`。

下一步主目標：
- **在 support 達標前，嚴格維持 `reference_only_until_exact_support_ready` 契約。**

### 目標 C：維持 profile governance / source blockers 的零漂移
目前已確認：
- leaderboard / train profile 仍分裂；
- `fin_netflow` 仍是 auth blocker。

下一步主目標：
- **持續顯式治理，但不搶走 q35 audit/runtime 對齊主頻寬。**

---

## 接下來要做

### 1. 修正 q35 audit surface 的 baseline/runtime 對齊
要做：
- 在 `scripts/hb_q35_scaling_audit.py` / runner diagnostics 中明確區分：
  - baseline current row
  - deployed runtime current row
  - whether `q35_discriminative_redesign_applied`
- 驗證：
  - q35 audit JSON / markdown / heartbeat summary / probe 不再互相矛盾
  - machine-read 能直接回答 runtime 是否已套用 redesign

### 2. 鎖住 q15 component experiment 為 support-gated research
要做：
- 持續檢查：
  - `q15_support_audit.support_route.verdict`
  - `q15_support_audit.component_experiment.verdict`
  - `q15_support_audit.component_experiment.machine_read_answer.support_ready`
- 若 exact bucket 還沒滿 50，禁止把 q15 component patch 升級成 runtime 放行

### 3. 維持 blocker-aware governance
要做：
- 持續顯式標記 `fin_netflow` auth blocker；
- profile split 先維持，不搶主焦點；
- 若 q35 audit/runtime surface 對齊後，再回來收斂 profile governance

---

## 暫不優先

以下本輪後仍不排最前面：
- 重做 q35 discriminative redesign runtime patch
- 直接做 q15 runtime patch
- 先做 profile split 收斂
- 稀疏來源 UI / 報告美化

原因：
> q35 deployment patch 已經落地；現在最大的風險不是「還沒 patch」，而是 **governance surfaces 對同一件事說了兩套話**。

---

## 成功標準

接下來幾輪工作的成功標準：
1. 下一輪至少留下 1 個與 **q35 audit/runtime surface 對齊** 直接相關的 patch / run / verify。
2. machine-read surface 必須清楚區分或對齊：
   - baseline current row
   - deployed runtime current row
   - `q35_discriminative_redesign_applied`
3. live predictor / drilldown / q35 audit / heartbeat summary 必須對同一條 q35 live row 給出一致可解讀的結論。
4. `q15_support_audit.component_experiment.verdict` 在 support 未滿前不得漂移為可部署語義。
5. `fin_netflow` 需持續被正確標成 auth blocker。

---

## Next gate

- **Next focus:**
  1. 修正 q35 audit / runner 的 baseline-runtime drift；
  2. 維持 q15 `reference_only_until_exact_support_ready` 契約；
  3. 維持 profile governance / source blockers 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q35 audit/runtime 對齊** 直接相關的 patch / artifact / verify；
  2. `live_predict_probe.entry_quality_components.q35_discriminative_redesign.applied` 與 q35 audit / summary 必須能被同時 machine-read 解釋，不再出現同輪「runtime 已跨 floor、audit 卻仍像未部署」的歧義；
  3. `q15_support_audit.component_experiment.machine_read_answer.support_ready` 在 support 未滿前不得被誤寫成 `true`。

- **Fallback if fail:**
  - 若 q35 audit/runtime surface 仍雙軌漂移，下一輪升級成 `governance_surface_drift` blocker；
  - 若 current live row 離開 q35，下一輪切回 q15/support blocker；
  - 若 next run 沒有新 patch，只剩報告，升級成 governance blocker。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 q35 audit/runtime contract 再擴大）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1022_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若同時成立：
     - `live_predict_probe.entry_quality >= 0.55`
     - `live_predict_probe.allowed_layers > 0`
     - `live_predict_probe.entry_quality_components.q35_discriminative_redesign.applied = true`
     - `q35_scaling_audit.deployment_grade_component_experiment.runtime_entry_quality < 0.55`
     則下一輪不得再把主焦點放在「是否部署 q35 redesign」；必須直接修 **q35 audit / summary baseline-runtime drift**。
