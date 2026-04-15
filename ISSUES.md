# ISSUES.md — Current State Only

_最後更新：2026-04-15 17:42 UTC — Heartbeat #1023（本輪已把 **q35 audit / runner baseline-vs-runtime drift** 真正收斂成 machine-read contract：`hb_parallel_runner.py` 先刷新 `live_predict_probe` 再跑 `hb_q35_scaling_audit.py`，而 q35 audit 現在會明確分開 **baseline_current_live / calibration_runtime_current / deployed_runtime_current**，並輸出 `runtime_source` 與 `q35_discriminative_redesign_applied`。目前主 blocker 已不再是 surface drift，而是：**current bull q35 live lane 仍只有 `entry_quality=0.4115 / allowed_layers=0`，同時 q15 exact bucket 剛達 50 rows、component experiment 已轉成 deployable-ready 但還缺正向 discrimination 驗證。**）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 修正 `q35_scaling_audit` / `hb_parallel_runner` 的 baseline-runtime drift；
  2. 維持 q15 `reference_only_until_exact_support_ready` 契約；
  3. 維持 profile governance / source blockers 零漂移治理。
- **Success gate**
  1. 至少留下 1 個與 q35 audit/runtime 對齊直接相關的 patch；
  2. `live_predict_probe`、`live_decision_quality_drilldown`、`q35_scaling_audit`、heartbeat summary 必須能 machine-read 區分 baseline current row / deployed runtime current row / `q35_discriminative_redesign_applied`；
  3. q15 support 未達標前不得把 component experiment 寫成可部署語義。
- **Fallback if fail**
  - 若沒有新 patch、只剩報告，視為 `HEARTBEAT FAILED: NO FORWARD PROGRESS`；
  - 若 current live row 離開 q35，下一輪改由 q15/support blocker 接手。

### 本輪承接結果
- **已處理**
  - `scripts/hb_parallel_runner.py`
    - 將執行順序改為：**先 `hb_predict_probe.py`，再 `hb_q35_scaling_audit.py`**，確保 q35 audit 讀到本輪最新 live runtime，而不是上一輪殘留 probe。
    - q35 summary 現在會 machine-read 持久化：`baseline_current_live`、`calibration_runtime_current`、`current_live`（deployed runtime）、`deployment_grade_component_experiment.runtime_source`、`q35_discriminative_redesign_applied`。
  - `scripts/hb_q35_scaling_audit.py`
    - 新增 `baseline_current_live / calibration_runtime_current / deployed_runtime_current` 三軌輸出；
    - `deployment_grade_component_experiment` 現在明確區分 `calibration_runtime_entry_quality` 與 `runtime_entry_quality`，並攜帶 `runtime_source` / `probe_alignment` / `q35_discriminative_redesign_applied`；
    - 若 live probe 與 current row 對齊，deployment-grade runtime 直接吃 `live_predict_probe.json`，不再把 calibration preview 假裝成 live runtime。
  - `tests/test_hb_parallel_runner.py`
    - 補上 q35 summary 新欄位與 runner 執行順序 regression tests。
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py tests/test_live_decision_quality_drilldown.py -q` → **75 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1023` → **通過**
- **本輪 machine-read 結論**
  - `q35_scaling_audit.deployment_grade_component_experiment.runtime_source = live_predict_probe`
  - `q35_scaling_audit.current_live.entry_quality = 0.4115`
  - `q35_scaling_audit.baseline_current_live.entry_quality = 0.3411`
  - `q35_scaling_audit.calibration_runtime_current.entry_quality = 0.4115`
  - `q35_scaling_audit.deployment_grade_component_experiment.q35_discriminative_redesign_applied = false`
  - **結論：q35 audit/runtime drift 已修掉；本輪不再存在「runtime 已跨 floor、audit 還說 0.31」的語義打架。**
- **本輪明確不做**
  - 不把 q35 drift 已解的問題繼續當成主戰場；
  - 不在尚未驗證 `preserves_positive_discrimination_status` 前，直接把 q15 exact-supported component experiment 寫進 runtime；
  - 不先做 sparse-source auth 修復，避免搶走 current live gate 主頻寬。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_parallel_runner.py`：q35 audit 依賴的 live probe 先刷新、後消費；summary 顯式區分 baseline/calibration/deployed runtime。
  - `scripts/hb_q35_scaling_audit.py`：新增三軌 current row contract 與 deployment-grade runtime source 對齊。
  - `tests/test_hb_parallel_runner.py`：鎖住 runner 順序與 q35 summary schema。
- **Tests（已通過）**
  - `python -m pytest tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py tests/test_live_decision_quality_drilldown.py -q` → **75 passed**
- **Runtime verify（已通過）**
  - `python scripts/hb_parallel_runner.py --fast --hb 1023`
- **已刷新 artifacts**
  - `data/heartbeat_1023_summary.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/q35_scaling_audit.json`
  - `data/q15_support_audit.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`

### 資料 / 新鮮度 / canonical target
- Heartbeat #1023：
  - Raw / Features / Labels：**21775 / 13204 / 43496**
  - 本輪增量：**+1 raw / +1 feature / +10 labels**
  - canonical target `simulated_pyramid_win`：**0.5793**
  - 240m labels：**21861 rows / target_rows 12939 / lag_vs_raw 約 3.0h**
  - 1440m labels：**12550 rows / target_rows 12550 / lag_vs_raw 約 23.3h**
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
  - avg_quality：**0.5915**
  - avg_pnl：**+0.0188**
  - avg_drawdown_penalty：**0.0593**
- 判讀：近期 bull pocket 仍極度集中；signal 強，但不能把這個 pocket 直接泛化成全域 runtime 放行理由。

### Live contract / q35 / q15 現況
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - regime：**bull**
  - regime_gate：**CAUTION**
  - current live structure bucket：**CAUTION|structure_quality_caution|q35**
  - `entry_quality = 0.4115`
  - `entry_quality_label = D`
  - `allowed_layers = 0 -> 0`
  - `decision_quality_calibration_scope = regime_label+regime_gate+entry_quality_label`
  - `expected_win_rate = 0.7000`, `expected_pyramid_quality = 0.4041`
- `data/q35_scaling_audit.json`
  - `baseline_current_live.entry_quality = 0.3411`
  - `calibration_runtime_current.entry_quality = 0.4115`
  - `deployment_grade_component_experiment.runtime_entry_quality = 0.4115`
  - `deployment_grade_component_experiment.runtime_source = live_predict_probe`
  - `deployment_grade_component_experiment.q35_discriminative_redesign_applied = false`
  - `base_stack_redesign_experiment.best_discriminative_entry_quality = 0.5645`
  - 判讀：**surface drift 已修復；現在看到的是同一條 live row 的真實結果：公式 review 後有改善，但 current q35 row 仍未跨 floor。**
- `data/q15_support_audit.json`
  - `support_route.verdict = exact_bucket_supported`
  - `floor_cross_legality.verdict = legal_component_experiment_after_support_ready`
  - `component_experiment.verdict = exact_supported_component_experiment_ready`
  - `component_experiment.machine_read_answer = {support_ready=true, entry_quality_ge_0_55=true, allowed_layers_gt_0=true, preserves_positive_discrimination_status=not_measured_requires_followup_verify}`
  - 判讀：**q15 support gate 剛打開，但還缺 discrimination-preserving verify，不能直接當成 deployment closure。**

### Profile split / governance / blockers
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard：`core_plus_macro`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - global recommended：`core_plus_4h`
  - `dual_profile_state = post_threshold_profile_governance_stalled`
  - `live_current_structure_bucket_rows = 50`（已達 minimum support）
  - `support_governance_route = exact_live_bucket_supported`
- sparse-source blockers
  - `fin_netflow`：**auth_missing / coverage 0.0% / archive_window_coverage 0.0% (0/1896)**
  - 其餘 blocked sparse sources：仍以 **history gap / snapshot archive** 為主

---

## 目前有效問題

### P1. q35 audit/runtime drift 已修，但 current bull q35 live lane 仍低於 trade floor
**現象**
- `q35_scaling_audit.deployment_grade_component_experiment.runtime_source = live_predict_probe`
- `baseline_entry_quality = 0.3411 -> runtime_entry_quality = 0.4115`
- `allowed_layers_gt_0 = false`
- `base_stack_redesign_experiment.best_discriminative_entry_quality = 0.5645`

**判讀**
- 本輪已排除「artifact 說錯話」；
- 真 blocker 回到 live path 本身：current q35 row 雖比 baseline 改善，但仍是 D lane；
- 下一輪要驗證的是：q15 exact-supported component experiment 能否在**保留 discrimination** 的前提下，合法把 current live lane 推到可部署區。

---

### P1. q15 exact bucket 剛達 minimum support，component experiment 已轉成 deployable-ready，但還缺正向 discrimination 驗證
**現象**
- `support_route.verdict = exact_bucket_supported`
- `component_experiment.verdict = exact_supported_component_experiment_ready`
- `machine_read_answer.support_ready = true`
- `machine_read_answer.entry_quality_ge_0_55 = true`
- `machine_read_answer.allowed_layers_gt_0 = true`
- `machine_read_answer.preserves_positive_discrimination_status = not_measured_requires_followup_verify`

**判讀**
- support blocker 已解除；
- 下一輪不該再把 q15 寫成 reference-only；
- 但在 verify `preserves_positive_discrimination` 前，仍不能直接合併進 runtime。

---

### P1. post-threshold profile governance 仍未收斂
**現象**
- leaderboard：`core_plus_macro`
- train：`core_plus_macro_plus_4h_structure_shift`
- global shrinkage winner：`core_plus_4h`
- `dual_profile_state = post_threshold_profile_governance_stalled`

**判讀**
- exact support 已恢復，治理狀態從「under-minimum blocker」升級成「post-threshold profile selection 尚未收斂」；
- 但優先級仍低於 q15 exact-supported component verify。

---

### P1. sparse-source blocker 仍存在，`fin_netflow` 仍是 auth blocker
**現象**
- `fin_netflow`：`auth_missing`, `coverage=0.0%`, `archive_window_coverage_pct=0.0%`

**判讀**
- 仍是 source blocker；
- 但本輪主路徑不是 sparse-source，而是 current bull q35/q15 deployment path。

---

## 本輪已清掉的問題

### RESOLVED. q35 audit / runner 對 baseline vs deployed runtime 語義漂移
**修前**
- q35 audit 可能把 component-level calibration preview 當成「runtime」；
- runner 先跑 q35 audit、後跑 predict probe，導致 audit 有機會讀到舊 probe；
- heartbeat / docs 容易出現「同輪 surface 說兩套話」。

**本輪 patch + 證據**
- `scripts/hb_parallel_runner.py`：先 `predict_probe`，再 `q35_scaling_audit`
- `scripts/hb_q35_scaling_audit.py`：新增 `baseline_current_live / calibration_runtime_current / deployed_runtime_current`
- `deployment_grade_component_experiment.runtime_source = live_predict_probe`
- `python -m pytest tests/test_hb_parallel_runner.py tests/test_api_feature_history_and_predictor.py tests/test_live_decision_quality_drilldown.py -q` → **75 passed**
- `python scripts/hb_parallel_runner.py --fast --hb 1023` → **通過**

**狀態**
- **已修復**：本輪之後，q35 audit / runner / heartbeat summary 對「baseline / calibration / deployed runtime」已有明確 contract。

---

## 本輪決策（收斂版）

### 策略後果表
| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 繼續把主焦點放在 q35 audit/runtime drift | 風險最低，延續上輪題目 | 會重打已解問題，造成空轉 | 治標 | 只有在 machine-read 仍互相矛盾時 | ❌ 不建議 |
| 以 q15 exact-supported component experiment 為主，補上 discrimination verify 與 deployment-grade驗證 | 直接吃到新開啟的 support gate；最接近把 current live lane推向可部署 closure | 若 discrimination 驗證失敗，需回退成 research-only | 治本 | `support_ready=true` 且 `entry_quality_ge_0_55=true` 已成立 | ✅ 推薦 |
| 先收斂 leaderboard/train/global profile split | 可降低治理噪音 | 仍無法直接回答 current live lane 能否部署 | 治標（治本需做：先完成 q15 exact-supported verify） | q15 verify 完成後 | ⏳ 次優先 |

### 效益前提驗證
| 情境 | 效益 |
|---|---|
| `q15_support_audit.component_experiment.machine_read_answer.support_ready = true` 且只差 `preserves_positive_discrimination_status` | ✅ 可直接把下一輪焦點轉成 q15 exact-supported deployment verify |
| q15 support 再次掉回 `<50 rows` 或 current live row 離開 q35/q15 lane | ❌ 前提不成立；下一輪需退回 support accumulation / bucket governance |

### 本輪要推進的 3 件事
1. 修掉 q35 audit/runtime surface drift。 ✅
2. 重新 machine-read current live q35 / q15 / profile governance 狀態。 ✅
3. 把下一輪主路徑從「修 drift」轉成「驗證 q15 exact-supported component deployment」。 ✅

### 本輪不做
- 不重做 q35 discriminative redesign deployment patch；
- 不提前處理 sparse-source auth blocker；
- 不在 discrimination verify 之前宣稱 q15 component 已可直接部署。

---

## Next gate

- **Next focus:**
  1. 以 `q15_support_audit.component_experiment` 為主，實作 / 驗證 **exact-supported component deployment patch**，補齊 `preserves_positive_discrimination`；
  2. 驗證該 patch 是否能把 current bull q35/q15 live lane machine-read 成 `entry_quality >= 0.55`、`allowed_layers > 0`，且不破壞 discrimination；
  3. 若 q15 verify 完成，再收斂 leaderboard / train / global 的 post-threshold profile governance。

- **Success gate:**
  1. 下一輪至少留下 1 個與 **q15 exact-supported component deployment verify** 直接相關的 code patch / artifact / verify；
  2. 必須 machine-read 回答：
     - `support_ready = true`
     - `entry_quality_ge_0_55 = true`
     - `allowed_layers_gt_0 = true`
     - `preserves_positive_discrimination = true`（不能再是 `not_measured_requires_followup_verify`）
  3. `live_predict_probe`、`live_decision_quality_drilldown`、`q15_support_audit`、heartbeat summary 對同一條 current live row 的結論必須一致。

- **Fallback if fail:**
  - 若 q15 exact-supported verify 失去 discrimination，下一輪立刻降回 `reference_only_exact_support_verified_but_not_deployable`；
  - 若 current live row 離開 q35/q15 path，下一輪退回 support accumulation / bucket governance；
  - 若沒有新 patch、只剩報告，視為 `HEARTBEAT FAILED: NO FORWARD PROGRESS`。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 q15 exact-supported deployment contract 擴大）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1023_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若同時成立：
     - `q35_scaling_audit.deployment_grade_component_experiment.runtime_source = live_predict_probe`
     - `q35_scaling_audit.deployment_grade_component_experiment.q35_discriminative_redesign_applied = false`
     - `q15_support_audit.component_experiment.verdict = exact_supported_component_experiment_ready`
     - `q15_support_audit.component_experiment.machine_read_answer.support_ready = true`
     則下一輪**不得再把主焦點放回 q35 audit/runtime drift**；必須直接做 **q15 exact-supported component deployment verify + discrimination check**。
