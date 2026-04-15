# ISSUES.md — Current State Only

_最後更新：2026-04-15 16:56 UTC — Heartbeat #1022（已把 **q35 discriminative redesign** 真正接進 live predictor runtime；current bull q35 lane 已從 `entry_quality=0.3219 / allowed_layers=0` 推進到 **`entry_quality=0.5667 / allowed_layers=1`**，並留下 regression tests + fast heartbeat 驗證。仍待處理的是：q35 audit 與 live runtime 的 baseline/runtime 雙軌漂移、q15 support 未達標、以及 profile/source governance。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 以 `q35_scaling_audit.base_stack_redesign_experiment.best_discriminative_candidate` 為藍本，做 **q35 discriminative redesign deployment patch**；
  2. 用 pytest + fast heartbeat 驗證該 patch 是否真的讓 current q35 live lane machine-read 成 `entry_quality >= 0.55`、`allowed_layers > 0`，且 `positive_discriminative_gap` 不退化；
  3. 維持 q15 component experiment 的 reference-only 契約，直到 exact bucket rows ≥ 50。
- **Success gate**
  1. 下一輪必須留下至少一個與 **q35 discriminative redesign deployment** 直接相關的 code patch / artifact / verify；
  2. 必須 machine-read 回答：
     - `entry_quality_ge_0_55 = true`
     - `allowed_layers_gt_0 = true`
     - `positive_discriminative_gap = true`
     - live predictor / drilldown / heartbeat summary 已對齊新 runtime 行為；
  3. `q15_support_audit.component_experiment.verdict` 在 support 未達標前不得漂移成可部署語義。
- **Fallback if fail**
  - 若 q35 redesign patch 一實作就失去 `positive_discriminative_gap`，下一輪直接降回 research-only；
  - 若 current live row 離開 q35，下一輪改由 q15/support blocker 接手；
  - 若沒有新 patch、只剩報告，視為 `HEARTBEAT FAILED: NO FORWARD PROGRESS`。

### 本輪承接結果
- **已處理**
  - `model/predictor.py`
    - 新增 `_maybe_apply_q35_discriminative_redesign()`：當 **current bull q35 row** 與 `data/q35_scaling_audit.json` 的 current live row 完全對齊，且 `best_discriminative_candidate` 仍 machine-read 通過時，runtime 直接套用 support-aware discriminative weights。
    - 新增 stale/row-mismatch 保護：若 timestamp 或 base features 不符，會自動退回 baseline 權重，避免舊 audit 誤放行新 row。
    - live contract 現在顯式輸出 `q35_discriminative_redesign_applied` / `q35_discriminative_redesign`。
  - `tests/test_api_feature_history_and_predictor.py`
    - 新增 q35 redesign **apply / stale-skip** regression tests。
  - `ARCHITECTURE.md`
    - 已同步 Heartbeat #1022 q35 discriminative deployment contract。
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q` → **75 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1022` → **通過**
- **本輪 machine-read 結論**
  - `live_predict_probe.entry_quality = 0.5667`
  - `live_predict_probe.allowed_layers = 1`
  - `live_predict_probe.allowed_layers_reason = entry_quality_C_single_layer`
  - `live_predict_probe.entry_quality_components.q35_discriminative_redesign.applied = true`
  - `live_predict_probe.entry_quality_components.q35_discriminative_redesign.machine_read_answer = {entry_quality_ge_0_55=true, allowed_layers_gt_0=true, positive_discriminative_gap=true}`
  - `live_decision_quality_drilldown.remaining_gap_to_floor = 0.0`
  - `q15_support_audit.component_experiment.verdict = reference_only_until_exact_support_ready`
- **本輪明確不做**
  - 不把 q15 proxy / boundary replay 誤寫成可部署 patch；
  - 不先處理 `fin_netflow` auth blocker，避免搶走 q35 runtime 對齊主頻寬；
  - 不把 q35 audit baseline 直接改寫成 runtime 結論而不做明確契約說明。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `model/predictor.py`
    - q35 discriminative redesign runtime patch 已落地。
  - `tests/test_api_feature_history_and_predictor.py`
    - regression tests 已鎖住「matching row 會套用 / stale row 不套用」。
  - `ARCHITECTURE.md`
    - 已補 runtime deploy contract。
- **Tests（已通過）**
  - `python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q` → **75 passed**
- **Runtime verify（已通過）**
  - `python scripts/hb_parallel_runner.py --fast --hb 1022`
- **已刷新 artifacts**
  - `data/heartbeat_1022_summary.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/q35_scaling_audit.json`
  - `data/q15_support_audit.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`

### 資料 / 新鮮度 / canonical target
- Heartbeat #1022：
  - Raw / Features / Labels：**21772 / 13201 / 43480**
  - 本輪增量：**+1 raw / +1 feature / +2 labels**
  - canonical target `simulated_pyramid_win`：**0.5796**
  - 240m labels：**21846 rows / target_rows 12924 / lag_vs_raw 約 3.5h**
  - 1440m labels：**12549 rows / target_rows 12549 / lag_vs_raw 約 23.1h**
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
  - win_rate：**0.9000**
  - avg_quality：**0.5953**
  - avg_pnl：**+0.0189**
  - avg_drawdown_penalty：**0.0582**
- 判讀：近期 bull canonical pocket 仍極端集中；IC 很強，但 calibration 不能直接把這個 pocket 全域泛化。

### Live contract / q35 / q15 現況
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - structure_bucket：**CAUTION|structure_quality_caution|q35**
  - entry_quality_label：**C**
  - decision_quality_label：**C**
  - `entry_quality = 0.5667`
  - `allowed_layers = 1 -> 1`
  - `allowed_layers_reason = entry_quality_C_single_layer`
  - `q35_discriminative_redesign_applied = true`
  - `decision_quality_calibration_scope = regime_label`
  - `expected_win_rate = 0.875`, `expected_pyramid_quality = 0.565`
- `data/live_decision_quality_drilldown.json`
  - `remaining_gap_to_floor = 0.0`
  - `deployment_blocker = null`
  - `runtime_blocker = null`
- `data/q35_scaling_audit.json`
  - `scope_applicability.status = current_live_q35_lane_active`
  - `base_stack_redesign_experiment.verdict = base_stack_redesign_discriminative_reweight_crosses_trade_floor`
  - `best_discriminative_candidate.current_entry_quality_after = 0.5667`
  - `best_discriminative_candidate.allowed_layers_after = 1`
  - `best_discriminative_candidate.positive_discriminative_gap = true`
  - **但** `deployment_grade_component_experiment.runtime_entry_quality = 0.3142`
  - 判讀：**audit 仍保留 baseline research 視角，live predictor 已吃到 redesign；兩者已出現 baseline/runtime 雙軌漂移。**
- `data/q15_support_audit.json`
  - `support_route.verdict = exact_bucket_present_but_below_minimum`
  - `current_live_structure_bucket_gap_to_minimum = 1`
  - `component_experiment.verdict = reference_only_until_exact_support_ready`
  - 判讀：**q15 仍只差 1 row，但在 support 未滿前仍不得放行。**

### Profile split / governance / blockers
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard：`core_plus_4h`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `live_current_structure_bucket_rows = 23`
  - `minimum_support_rows = 50`
- sparse-source blockers
  - `fin_netflow`：**auth_missing / coverage 0.0% / archive_window_coverage 0.0% (0/1894)**
  - 其餘 blocked sparse sources：仍以 **history gap / snapshot archive** 為主

---

## 目前有效問題

### P1. q35 runtime 已成功跨過 trade floor，但 q35 audit / runner 仍存在 baseline vs runtime 雙軌漂移
**現象**
- live predictor：`entry_quality = 0.5667`, `allowed_layers = 1`, `q35_discriminative_redesign_applied = true`
- q35 audit：`deployment_grade_component_experiment.runtime_entry_quality = 0.3142`
- 同一輪 `base_stack_redesign_experiment.best_discriminative_candidate.current_entry_quality_after = 0.5667`

**判讀**
- 真正的 deployment patch 已落地；
- 但 q35 audit 仍用 baseline/research lane 呈現「runtime」，容易讓文件與 runner 誤以為 live 還沒跨 floor；
- 下一輪應把 audit/summary 的 **baseline 與 deployed runtime** 顯式拆開，避免治理訊息漂移。

---

### P1. q15 exact bucket 仍差 1 row，component experiment 只能維持 reference-only
**現象**
- `q15_support_audit.support_route.verdict = exact_bucket_present_but_below_minimum`
- `current_live_structure_bucket_gap_to_minimum = 1`
- `component_experiment.verdict = reference_only_until_exact_support_ready`

**判讀**
- q15 blocker 已逼近解除，但還沒滿 50 rows 前，仍不得把 component experiment 寫進 runtime。

---

### P1. post-threshold profile governance 仍未收斂
**現象**
- leaderboard：`core_plus_4h`
- train：`core_plus_macro_plus_4h_structure_shift`
- `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`

**判讀**
- q35 runtime 已先前進；接下來應避免 profile governance 重新把 live deployment 語義沖掉。

---

### P1. sparse-source blockers 仍存在，`fin_netflow` 仍是 live auth blocker
**現象**
- `fin_netflow`：`auth_missing`, `coverage=0.0%`, `archive_window_coverage_pct=0.0%`
- blocked sparse features：**8 個**

**判讀**
- 這仍是 source blocker，但優先級低於 q35 runtime / audit contract 對齊。

---

## 本輪已清掉的問題

### RESOLVED. q35 discriminative redesign 只停在 artifact，尚未真正進入 live predictor runtime
**修前**
- `q35_scaling_audit.best_discriminative_candidate` 已 machine-read 可跨 floor；
- 但 `live_predict_probe.entry_quality` 仍停在 **0.3219**，`allowed_layers=0`。

**本輪 patch + 證據**
- `model/predictor.py`：新增 `_maybe_apply_q35_discriminative_redesign()`，將 audited best discriminative candidate 變成 runtime patch。
- `tests/test_api_feature_history_and_predictor.py`：新增 apply/stale-skip regression。
- `python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q` → **75 passed**
- `python scripts/hb_parallel_runner.py --fast --hb 1022` → **通過**
- `data/live_predict_probe.json.entry_quality = 0.5667`
- `data/live_predict_probe.json.allowed_layers = 1`
- `data/live_predict_probe.json.entry_quality_components.q35_discriminative_redesign.applied = true`

**狀態**
- **已修復**：q35 discriminative redesign 已不再只是研究 artifact，而是 live predictor runtime contract 的一部分。

---

## 本輪決策（收斂版）

### 策略後果表
| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 直接把 q35 discriminative redesign 寫進 live predictor | 立刻驗證最接近 deployment 的候選，留下真正前進證據 | 若 audit stale 會誤放行新 row，需加 stale guard | 治本 | current live row 仍是 audited q35 row，且 machine-read 三條件都成立 | ✅ 推薦 |
| 先繼續只更新 q35/q15 artifacts | 風險最低 | 仍停在「有候選但沒 patch」，違反 HEARTBEAT | 無效 | 完全 blocked 時 | ❌ 不建議 |
| 先回頭收斂 q15 support / profile split | 可提前處理後續治理 | 會延後最直接的 q35 deployment 前進證據 | 治標 | q35 runtime patch 已完成後才適合 | ❌ 本輪不建議作主路徑 |

### 效益前提驗證
| 情境 | 效益 |
|---|---|
| `q35_scaling_audit.scope_applicability.status = current_live_q35_lane_active` 且 best discriminative candidate 仍 machine-read 全通過 | ✅ 可直接做 runtime patch |
| audit timestamp / raw features 與 current live row 不一致 | ❌ 不可放行，必須退回 baseline |

### 本輪要推進的 3 件事
1. 把 q35 discriminative redesign 真正接進 live predictor runtime。 ✅
2. 用 regression test + fast heartbeat 驗證 runtime 是否跨 floor。 ✅
3. 維持 q15 reference-only 契約，不讓 q15 research 漂成 runtime patch。 ✅

### 本輪不做
- 不把 q15 support 未達標的 component experiment 提前部署；
- 不先做 source blocker / profile split 主修；
- 不把 q35 audit baseline 值當成「runtime 尚未修好」的唯一結論。

---

## Next gate

- **Next focus:**
  1. 修正 `q35_scaling_audit` / `hb_parallel_runner` 對 **baseline vs deployed runtime** 的雙軌漂移，讓 machine-read surface 不再同輪自相矛盾；
  2. 維持 q15 `reference_only_until_exact_support_ready` 契約，直到 exact bucket rows ≥ 50；
  3. 維持 profile governance / source blockers 零漂移治理。

- **Success gate:**
  1. 下一輪至少留下 1 個與 **q35 audit/runtime 對齊** 直接相關的 patch / artifact / verify；
  2. `live_predict_probe`、`live_decision_quality_drilldown`、`heartbeat summary`、`q35_scaling_audit` 必須能清楚區分或對齊：
     - baseline current row
     - deployed runtime current row
     - `q35_discriminative_redesign_applied`
  3. `q15_support_audit.component_experiment.verdict` 在 support 未達標前仍必須保持 `reference_only_until_exact_support_ready`。

- **Fallback if fail:**
  - 若 q35 audit/runtime 對齊仍沒 patch，下一輪升級成 `governance_surface_drift` blocker；
  - 若 current live row 離開 q35，下一輪改回 q15/support blocker 主路徑；
  - 若沒有新 patch、只剩報告，視為 `HEARTBEAT FAILED: NO FORWARD PROGRESS`。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 q35 audit surface contract 再擴大）

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
     則下一輪不得再重做 q35 redesign patch；必須直接修 **q35 audit / summary baseline-runtime drift**。
