# ISSUES.md — Current State Only

_最後更新：2026-04-15 06:09 UTC — Heartbeat #1007（本輪把 live `CIRCUIT_BREAKER` 正式升級成 machine-readable runtime blocker：`hb_predict_probe.py` 會保留 `reason/streak/win_rate`，`live_decision_quality_drilldown` 不再把沒有 entry-quality contract 的 live row 假裝成 `trade_floor_gap=0.55`。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪（#1006）要求本輪處理
- **Next focus**：
  1. 針對 `CAUTION|structure_quality_caution|q15` 做 bias50 calibration 候選分析；
  2. 明確決定 q15 support route（proxy / neighbor / blocker）；
  3. 維持 `profile_split / support_blocker_state / proxy_boundary_verdict / fin_netflow auth blocker` 零漂移治理。
- **Success gate**：
  1. 至少留下 1 個與 q15 calibration / support route 直接相關的 patch / artifact / verify；
  2. 若 current bucket 仍 rows=0，必須回答治理路徑；
  3. 不得破壞 `allowed_layers=0` guardrail。
- **Fallback if fail**：
  - 不得回到 generic gap attribution；
  - 不得無 support 證據就 relax runtime gate；
  - 語義若再漂移要升級 blocker。

### 本輪承接結果
- **已處理**：
  - 發現上輪前提已失效：current live path 這一輪不是「q15 / q35 lane 正在等待校準」，而是 **predictor 先被 circuit breaker 擋下**。
  - `scripts/hb_predict_probe.py`
    - 新增保留 `reason / streak / win_rate`，讓 live probe 不再把 `CIRCUIT_BREAKER` 只顯示成空 scope。
  - `scripts/live_decision_quality_drilldown.py`
    - 新增 `runtime_blocker`；
    - 若 live row 被 `CIRCUIT_BREAKER` 擋下，`component_gap_attribution` 會輸出 `unavailable_reason`，不再偽造 `trade_floor_gap=0.55`。
  - `scripts/hb_parallel_runner.py`
    - `live_predictor_diagnostics` 現在會同步保留 `model_type / reason / streak / win_rate / runtime_blocker`。
  - `ARCHITECTURE.md`
    - 補上 probe / drilldown 的 circuit-breaker propagation contract。
- **驗證已完成**：
  - `source venv/bin/activate && python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q` → **20 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1007` → **通過**
- **本輪明確答案**：
  - 本輪 live path 主 blocker 不是 q15 support route，而是 **`CIRCUIT_BREAKER`**；
  - `live_decision_quality_drilldown.json.runtime_blocker.type = circuit_breaker`
  - `runtime_blocker.reason = Consecutive loss streak: 59 >= 50`
  - 因此 q15 / q35 calibration 只能視為 **background research**，不是當前 live runtime root cause。
- **本輪明確不做**：
  - 不在 circuit breaker 仍啟動時直接 relax q15/q35 runtime gate；
  - 不把 q35 audit 的研究結果誤包裝成當前 live deployment 建議；
  - 不把 `fin_netflow` auth blocker 混入 circuit breaker 根因。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_predict_probe.py`
  - `scripts/live_decision_quality_drilldown.py`
  - `scripts/hb_parallel_runner.py`
  - `tests/test_live_decision_quality_drilldown.py`
  - `tests/test_hb_parallel_runner.py`
  - `ARCHITECTURE.md`
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q` → **20 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1007`
- **已刷新 artifacts**
  - `data/heartbeat_1007_summary.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `docs/analysis/live_decision_quality_drilldown.md`
  - `data/q35_scaling_audit.json`
  - `docs/analysis/q35_scaling_audit.md`
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`
  - `model/ic_signs.json`

### 資料 / 新鮮度 / canonical target
- Heartbeat #1007：
  - Raw / Features / Labels：**21582 / 13011 / 43256**
  - 本輪增量：**+1 raw / +1 feature / +15 labels**
  - canonical target `simulated_pyramid_win`：**0.5776**
  - 240m labels：**21652 rows / target_rows 12730 / lag_vs_raw 約 3.0h**
  - 1440m labels：**12519 rows / target_rows 12519 / lag_vs_raw 約 23.3h**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**20/30 pass**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 6/8**
- drift primary window：**recent 100**
  - alerts：`constant_target`, `regime_concentration`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 100%**
  - win_rate：**1.0000**
  - avg_quality：**0.6810**
  - avg_pnl：**+0.0215**
  - avg_drawdown_penalty：**0.0337**
- 判讀：資料與 canonical labels 健康；當前 live runtime 被 circuit breaker 擋下，漂移不是首要 blocker。

### Live contract / runtime blocker / calibration research
- `data/live_predict_probe.json`
  - signal：**CIRCUIT_BREAKER**
  - regime：**bull**
  - `reason = Consecutive loss streak: 59 >= 50`
  - `streak = 59`
  - `allowed_layers = 0`
  - `decision_quality_calibration_scope = null`
  - `expected_win_rate / quality = null`
- `data/live_decision_quality_drilldown.json`
  - `runtime_blocker.type = circuit_breaker`
  - `component_gap_attribution.unavailable_reason = Consecutive loss streak: 59 >= 50`
  - `remaining_gap_to_floor = null`
  - `best_single_component = null`
- `data/q35_scaling_audit.json`
  - `overall_verdict = broader_bull_cohort_recalibration_candidate`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`
- 判讀：q35/q15 calibration artifact 仍可作研究，但**不是當前 live blocker**；本輪真正阻塞部署的是 circuit breaker。

### Support / profile / leaderboard
- `data/bull_4h_pocket_ablation.json`
  - `bull_recommended_profile = core_plus_macro_plus_4h_structure_shift`
  - `bull_collapse_recommended_profile = core_plus_macro`
  - `bull_exact_live_lane_proxy_rows = 0`
  - `bull_live_exact_lane_bucket_proxy_rows = 0`
  - `bull_supported_neighbor_buckets_proxy_rows = 0`
- `data/feature_group_ablation.json`
  - `recommended_profile = core_only`
- `data/leaderboard_feature_profile_probe.json`
  - `leaderboard_selected_profile = core_only`
  - `train_selected_profile = core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `support_governance_route = no_support_proxy`
- 判讀：live bucket support 仍未恢復；但在 circuit breaker 清除前，這條 lane 仍屬次要研究問題。

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. live predictor 已被 circuit breaker 先擋下，當前沒有可部署的 decision-quality scope
**現象**
- `signal = CIRCUIT_BREAKER`
- `reason = Consecutive loss streak: 59 >= 50`
- `allowed_layers = 0`
- `decision_quality_calibration_scope = null`
- `expected_win_rate / expected_pyramid_quality = null`

**判讀**
- 本輪 live blocker 是 **runtime risk governance**，不是 q15/q35 lane 細節；
- 若不先處理 breaker 根因，任何 calibration/support 討論都只會停在 research，不會變成 deployable live rule。

---

### P1. bull 4H support route 仍然是 `no_support_proxy`
**現象**
- `bull_exact_live_lane_proxy_rows = 0`
- `bull_live_exact_lane_bucket_proxy_rows = 0`
- `bull_supported_neighbor_buckets_proxy_rows = 0`
- `support_governance_route = no_support_proxy`

**判讀**
- 這表示就算 breaker 沒開，bull live lane 也還沒有足夠支撐；
- 但目前優先序次於 circuit breaker，因為 live runtime 根本先被 breaker 擋下。

---

### P1. production / leaderboard profile split 仍存在
**現象**
- global shrinkage winner：`core_only`
- production train profile：`core_plus_macro_plus_4h_structure_shift`
- `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`

**判讀**
- split 還是治理事實，不是 artifact 漂移；
- 但要先等 breaker 與 support route恢復可用，才有意義繼續追 profile 收斂。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1709)**

**判讀**
- 仍是外部憑證 blocker；
- 不可混入 circuit breaker 或 bull live lane 的根因。

---

## 本輪已清掉的問題

### RESOLVED. drilldown 在 live path 被 circuit breaker 擋下時，仍輸出假的 gap attribution
**修前**
- `live_decision_quality_drilldown` 在 `entry_quality_components` 為空時，會把當前 live row 假裝成 `trade_floor_gap=0.55`；
- `hb_predict_probe.py` 沒保留 breaker `reason/streak/win_rate`，heartbeat 無法 machine-read 區分「沒有 scope」是 blocker 還是 artifact 壞掉。

**本輪 patch + 證據**
- `scripts/hb_predict_probe.py`
  - 新增輸出 `reason / streak / win_rate`
- `scripts/live_decision_quality_drilldown.py`
  - 新增 `runtime_blocker`
  - 新增 `component_gap_attribution.unavailable_reason`
  - breaker 情境下不再偽造 `remaining_gap_to_floor`
- `scripts/hb_parallel_runner.py`
  - `live_predictor_diagnostics` 新增 `reason / streak / win_rate / runtime_blocker`
- `python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q`
  - **20 passed**
- `python scripts/hb_parallel_runner.py --fast --hb 1007`
  - `data/live_predict_probe.json.reason = Consecutive loss streak: 59 >= 50`
  - `data/live_decision_quality_drilldown.json.runtime_blocker.type = circuit_breaker`
  - `remaining_gap_to_floor = null`

**狀態**
- **已修復**：heartbeat 現在能 machine-read 看出「當前 live runtime 被 circuit breaker 先擋下」，不再把空 decision-quality contract 誤判成 q15/q35 gap。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 circuit breaker 變成可機器讀取的 live blocker。** ✅
2. **重新界定 q15/q35 calibration 的角色：目前只屬 research，不是 live runtime root cause。** ✅
3. **重跑 fast heartbeat，確認 canonical diagnostics / IC / blocker / profile state 沒有口徑漂移。** ✅

### 本輪不做
- 不直接 relax circuit breaker；
- 不在 breaker 開啟時放寬 q15/q35 gate；
- 不把 q35 audit 當成 live 可部署建議；
- 不把 `fin_netflow` auth blocker 混進當前 live breaker 根因。

---

## Next gate

- **Next focus:**
  1. 對 `CIRCUIT_BREAKER` 做 root-cause artifact：明確回答 59-streak 是由哪一段 canonical 標籤尾端造成、何時才允許解除；
  2. breaker 未解除前，只把 q15/q35 與 bull support route 當成 background research，避免誤下 deploy 結論；
  3. 維持 `profile_split / support_governance_route / fin_netflow auth blocker` 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **circuit breaker root cause / release condition** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答：breaker 是 `streak`、`recent win_rate`、還是兩者同時在卡；
  3. 若 breaker 仍在，所有 live summary 都不得再把 q15/q35 calibration 誤寫成當前 deploy blocker。

- **Fallback if fail:**
  - 若下一輪又把主焦點放回 q15 generic calibration，而沒有先處理 breaker，視為 regression；
  - 若在沒有 release evidence 的情況下直接 relax breaker，視為風控 regression；
  - 若 probe / drilldown 再次丟失 breaker reason，升級為 blocker。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 breaker release contract 再擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1007_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `docs/analysis/live_decision_quality_drilldown.md`
     - `data/q35_scaling_audit.json`
     - `data/bull_4h_pocket_ablation.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若同時成立：
     - `signal = CIRCUIT_BREAKER`
     - `runtime_blocker.type = circuit_breaker`
     - `reason`/`streak` 已存在於 probe
     - `component_gap_attribution.unavailable_reason` 非空
     則下一輪不得再把主焦點放回 q15 generic gap attribution；必須直接處理 **circuit breaker root cause / release condition**。
