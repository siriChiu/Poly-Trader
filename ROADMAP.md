# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 21:56 UTC — Heartbeat #fast（本輪已把 q35 exact support 的 `support_progress` 歷史承接修正為可比較前一輪 fast summary，且可從 legacy `governance_contract` 回填 comparability；current-live blocker 已明確收斂成 **11/50、較上一輪 13/50 回落**。）_

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
  - `data/heartbeat_fast_summary.json`

### 本輪新完成：support_progress 歷史承接已可 machine-read 真 regression
- `scripts/hb_leaderboard_candidate_probe.py`
  - 同 label=`fast` 的前一輪 summary 不再被誤去重
  - legacy summary 若只把 `support_governance_route / minimum_support_rows` 放在 `governance_contract`，現在也能回填成 comparability
- `tests/test_hb_leaderboard_candidate_probe.py`
  - 新增前一輪 fast summary reuse regression test
- `ARCHITECTURE.md`
  - 已同步補上 support-progress 歷史承接約束

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **42 passed**
- `source venv/bin/activate && HB_RUN_LABEL=fast python scripts/hb_leaderboard_candidate_probe.py` → **通過**
- `/home/kazuha/Poly-Trader/venv/bin/python scripts/hb_parallel_runner.py --fast` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#fast）：
  - Raw / Features / Labels = **21788 / 13217 / 43581**
  - simulated_pyramid_win = **0.5806**
- label freshness 正常：
  - 240m = **21934 rows / target_rows 13012 / expected_horizon_lag**
  - 1440m = **12562 rows / target_rows 12562 / expected_horizon_lag**
- raw freshness：**約 0.5 分鐘**
- continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / drift / live runtime
- Global IC：**18/30**
- TW-IC：**26/30**
- drift primary window：**250**
  - interpretation：**distribution_pathology**
  - dominant regime：**bull 100.0%**
  - window win_rate：**0.8920**
- fast heartbeat current live q35 path：
  - lane：**bull / CAUTION / q35**
  - `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`
  - `deployment_grade_component_experiment = runtime_patch_crosses_trade_floor`
  - `runtime_entry_quality = 0.5588`
  - `runtime_allowed_layers_raw = 1`
  - `q35_discriminative_redesign_applied = true`
  - `live_predict_probe.allowed_layers = 1`

### q35 / q15 / governance 現況
- `leaderboard_feature_profile_probe`
  - `leaderboard = core_plus_4h`
  - `train = core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `governance_contract.verdict = dual_role_governance_active`
  - `governance_contract.treat_as_parity_blocker = false`
  - `support_governance_route = exact_live_bucket_present_but_below_minimum`
  - current q35 exact live bucket rows：**11 / 50**
  - `support_progress.status = regressed_under_minimum`
  - `support_progress.previous_rows = 13`
  - `support_progress.delta_vs_previous = -2`
- `q15_support_audit`
  - `scope_applicability.status = current_live_not_q15_lane`
  - `support_route.verdict = exact_bucket_present_but_below_minimum`
  - `floor_cross_legality.verdict = floor_crossed_but_support_not_ready`

### Source blockers
- `fin_netflow`：**auth_missing / coverage 0.0%**
- 其他 sparse features 仍以 `archive_required / snapshot_only` 為主

---

## 當前主目標

### 目標 A：把 q35 exact support governance 從「假的不可比」推進到「真的可追責」
目前已確認：
- q35 runtime path 仍維持 `entry_quality=0.5588 / allowed_layers=1`
- exact support 由 **13 / 50 回落到 11 / 50**
- `support_progress` 已能 machine-read 輸出 `previous_rows / delta_vs_previous / status=regressed_under_minimum`

下一步主目標：
- **把 q35 exact support regression 的 root cause 查明，不再容許它被包裝成 history gap 或 parity drift。**

### 目標 B：維持 dual-role governance 正確，但不再讓它吃掉 q35 regression 訊號
目前已確認：
- `governance_contract` 仍明確指出這是 **雙角色治理，不是 parity drift**
- 真正卡住的是 current live q35 exact support 回落，不是 profile 語義

下一步主目標：
- **在 support 未翻轉前，維持 `treat_as_parity_blocker=false`，把治理焦點放在 q35 regression / accumulation。**

### 目標 C：維持 q15 standby route 的 truthful governance
目前已確認：
- current live row 不在 q15 lane
- q15 support route 仍是 `exact_bucket_present_but_below_minimum`
- floor 雖跨過，但 support 尚未 ready

下一步主目標：
- **維持 q15 standby route 語義正確；只有 current live row 回到 q15 lane 且 exact support 達標時，才重新升級成 active verify。**

---

## 接下來要做

### 1. 追 q35 current-live exact support regression
要做：
- 監控 `live_current_structure_bucket_rows` 是否從 **11** 回升到 `minimum_support_rows=50`
- 每輪直接讀 `support_progress.status / previous_rows / delta_vs_previous / stagnant_run_count`
- 若下一輪繼續回落，或轉成長期停滯，升級成 `#PROFILE_GOVERNANCE_STALLED`
- 驗證：
  - `data/leaderboard_feature_profile_probe.json`
  - `data/heartbeat_fast_summary.json`
  - `data/live_predict_probe.json`

### 2. 守住 governance contract 與 support_progress comparability 不回退
要做：
- 每輪 heartbeat 確認 `leaderboard_candidate_diagnostics.governance_contract` 與 `support_progress` 仍存在且與 probe 一致
- 確認 fast label 仍可比較前一輪 fast summary，legacy governance fallback 仍可回填 comparability
- 若 contract 消失、漏寫、或重新把 dual-role 誤標成 parity blocker，視為 regression
- 驗證：
  - `python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q`
  - `python scripts/hb_parallel_runner.py --fast`

### 3. 維持 q15 standby route truthful governance
要做：
- 持續使用 `q15_support_audit.scope_applicability` 作單一真相來源
- 若 current live row 仍是 q35，文件 / heartbeat 不得再把 q15 standby route 寫成主 closure
- 只在 q15 exact rows 達標後，才重新升級 q15 component path

---

## 暫不優先

以下本輪後仍不排最前面：
- 把 profile split 本身重新當作 parity drift 主 blocker
- 把 q15 standby route 拉回主 closure
- sparse-source auth / archive blocker 主修

原因：
> 本輪已把 q35 support progression 修成可比較歷史；目前最近的治理缺口是 **q35 exact support 11/50 regression**，其次才是 **support 是否再回落或轉停滯**。

---

## 成功標準

接下來幾輪工作的成功標準：
1. 下一輪至少留下 1 個與 **q35 exact support regression** 或 **support_progress blocker governance** 直接相關的 patch / artifact / verify。
2. `leaderboard_feature_profile_probe.alignment.governance_contract` 必須持續存在，且在 support 未翻轉前維持 `treat_as_parity_blocker=false`。
3. `support_progress` 必須持續存在，並能 machine-read 表達 current rows / previous rows / delta / status。
4. `python scripts/hb_parallel_runner.py --fast` 內仍必須 machine-read 顯示：
   - `q35_scaling_audit.deployment_grade_component_experiment.entry_quality_ge_0_55 = true`
   - `q35_scaling_audit.deployment_grade_component_experiment.allowed_layers_gt_0 = true`
   - `live_predict_probe.allowed_layers = 1`
5. q15 audit 若仍 inactive，必須維持 `current_live_not_q15_lane`，不能再被寫成 current-live closure。

---

## Next gate

- **Next focus:**
  1. 追 q35 exact support regression（11/50，上一輪為 13/50）；
  2. 觀察 `support_progress` 是否再回落、轉成停滯、或恢復累積；
  3. 維持 q15 standby route truthfulness。

- **Success gate:**
  1. next run 必須留下至少一個與 **q35 exact support regression** 或 **support_progress blocker governance** 直接相關的 patch / artifact / verify；
  2. `governance_contract` 與 `support_progress` 必須仍存在且語義正確；
  3. `support_progress` 必須 machine-read 顯示 `previous_rows / delta_vs_previous / status`；
  4. `q35_scaling_audit.deployment_grade_component_experiment.entry_quality_ge_0_55` 與 `allowed_layers_gt_0` 必須持續為 `true`；
  5. `live_predict_probe.allowed_layers = 1` 且 `q35_discriminative_redesign_applied = true`。

- **Fallback if fail:**
  - 若 governance contract 或 support_progress 又消失，回查 probe / summary persistence；
  - 若 q35 exact support 再連續回落或連續停在 `<50`，升級成 `#PROFILE_GOVERNANCE_STALLED` blocker；
  - 若 current live row 離開 q35，下一輪依 `scope_applicability` 重新選 active lane。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 support-progress comparability contract 再擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_fast_summary.json` 的 `leaderboard_candidate_diagnostics.support_progress`，確認是否仍為 `regressed_under_minimum / stalled_under_minimum / accumulating`
  2. 再讀：
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
  3. 若 `support_governance_route = exact_live_bucket_present_but_below_minimum`：
     - `support_progress.status = accumulating` → 繼續追 exact support 累積；
     - `support_progress.status = stalled_under_minimum` → 升級 `#PROFILE_GOVERNANCE_STALLED` 評估；
     - `support_progress.status = regressed_under_minimum` → 先查 current bucket / route / exact rows 為何回落；
     - `support_progress.status = no_recent_comparable_history` → 視為 regression，先回查 probe 歷史承接 contract。
