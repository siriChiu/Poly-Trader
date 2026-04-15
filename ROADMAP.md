# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 06:09 UTC — Heartbeat #1007（本輪已把 live `CIRCUIT_BREAKER` 正式接進 probe / drilldown / heartbeat summary contract。現在 heartbeat 不會再把 breaker 擋下的 live row誤判成 q15/q35 gap；當前主治理目標已切到 breaker root cause / release condition，而 q15/q35 calibration 降級成 background research。）_

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
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `issues.json`
  - numbered summary：`data/heartbeat_1007_summary.json`

### 本輪新完成：circuit-breaker propagation contract 已落地
- `scripts/hb_predict_probe.py`
  - 新增輸出：`reason / streak / win_rate`
- `scripts/live_decision_quality_drilldown.py`
  - 新增 `runtime_blocker`
  - 新增 `component_gap_attribution.unavailable_reason`
  - breaker 情境下不再偽造 `trade_floor_gap=0.55`
- `scripts/hb_parallel_runner.py`
  - `live_predictor_diagnostics` 新增 `model_type / reason / streak / win_rate / runtime_blocker`
- `ARCHITECTURE.md`
  - 補上 probe / drilldown 的 circuit-breaker propagation contract

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q` → **20 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1007` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#1007）：
  - Raw / Features / Labels = **21582 / 13011 / 43256**
  - simulated_pyramid_win = **0.5776**
- label freshness 正常：
  - 240m lag 約 **3.0h**
  - 1440m lag 約 **23.3h**

### IC / drift / live runtime
- Global IC：**19/30**
- TW-IC：**20/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 6/8**
- drift primary window：**100**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**bull 100%**
- live predictor：
  - signal：**CIRCUIT_BREAKER**
  - regime：**bull**
  - reason：**Consecutive loss streak: 59 >= 50**
  - allowed layers：**0**
  - decision-quality scope：**None**
- live drilldown：
  - `runtime_blocker.type = circuit_breaker`
  - `component_gap_attribution.unavailable_reason = Consecutive loss streak: 59 >= 50`
  - `remaining_gap_to_floor = null`

### Calibration / support / profile 現況
- q35 audit 仍顯示：`broader_bull_cohort_recalibration_candidate`
- bull support route：`no_support_proxy`
- global shrinkage winner：`core_only`
- production train profile：`core_plus_macro_plus_4h_structure_shift`
- leaderboard state：`leaderboard_global_winner_vs_train_support_fallback`

### 治理結論
- **已完成**：heartbeat 現在能 machine-read 看出「當前沒有 live scope 是因為 circuit breaker」，不是 artifact 壞掉。
- **未完成**：circuit breaker 為何在 canonical target 仍 57.8% 時觸發、解除條件應如何定義，還沒有 root-cause artifact。
- **降級處理**：q15/q35 calibration 與 bull support route 先視為 background research；在 breaker 未解除前，不可當成當前 live deploy blocker。

---

## 當前主目標

### 目標 A：釐清 circuit breaker root cause / release condition
目前已確認：
- live predictor 在 decision-quality contract 之前就被 breaker 擋下；
- breaker 原因已可 machine-read（本輪為 `Consecutive loss streak: 59 >= 50`）；
- 但 heartbeat 還沒有 artifact 回答：
  - 這 59-streak 對應哪段 canonical target tail？
  - breaker 是否也同時被 recent win-rate floor 觸發？
  - 解除條件應看 streak、rolling win-rate、還是兩者並用？

下一步主目標：
- **把 breaker 從「一個警報」升級成可驗證的治理 contract**。

### 目標 B：breaker 未解除前，把 q15/q35 calibration 明確降級成研究層
目前已確認：
- q35 audit 仍有研究價值；
- 但 live probe / drilldown 都顯示當前沒有可部署的 decision-quality scope。

下一步主目標：
- **確保所有 heartbeat / docs / summaries 都把 q15/q35 表述為 research，不再當成當前 live root cause。**

### 目標 C：維持 profile split 與 bull support route 的治理語義
目前已確認：
- `core_only` 仍是 global shrinkage winner；
- `core_plus_macro_plus_4h_structure_shift` 仍是 production support-aware profile；
- bull lane `support_governance_route = no_support_proxy`。

下一步主目標：
- breaker 問題釐清前，持續把這些資訊當作**次級治理背景**，避免語義漂移。

### 目標 D：維持 source auth blocker 顯式治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 breaker / q15 / q35 敘事

---

## 接下來要做

### 1. 做 circuit-breaker 根因 artifact
要做：
- 明確對應最近 canonical labels：
  - 最長連敗段起訖時間
  - breaker trigger 類型（streak / win-rate / both）
  - release condition 候選
- 產出 machine-readable JSON + markdown
- 驗證該 artifact 能被 heartbeat summary 正確摘取

### 2. 把 q15/q35 研究與 live blocker 明確分層
要做：
- 在 breaker 仍啟動時，所有 summary 必須顯示：
  - live blocker = circuit breaker
  - q15/q35 = background research
- 不再讓 q35 audit 的研究結論誤導成當前 deploy 建議

### 3. 維持 blocker-aware profile governance
要做：
- 持續檢查：
  - `leaderboard_selected_profile`
  - `train_selected_profile`
  - `dual_profile_state`
  - `support_governance_route`
- 但在 breaker 未解除前，不把 profile 收斂當成第一優先

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 breaker 或 bull live lane 問題

---

## 暫不優先

以下本輪後仍不排最前面：
- 直接 relax circuit breaker
- 直接放寬 q15/q35 runtime gate
- 重新追 generic gap attribution
- 強行統一 leaderboard / production profile
- UI 美化與 fancy controls

原因：
> 當前真正的 live blocker 已經明確是 **circuit breaker**；在 release condition 沒釐清前，其他 calibration/support/profile 工作都只屬背景研究。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **circuit breaker root cause / release condition** 直接相關的真 patch / run / verify。
2. `live_predict_probe / live_decision_quality_drilldown / heartbeat summary` 對 breaker 的描述必須零漂移。
3. 若 breaker 仍啟動，q15/q35 surfaces 不得再被寫成當前 live blocker。
4. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 做 circuit breaker root-cause / release-condition artifact；
  2. breaker 未解除前，維持 q15/q35 為 background research 的治理分層；
  3. 維持 `profile_split / support_governance_route / fin_netflow auth blocker` 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **breaker root cause / release condition** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答 breaker 目前是由 `streak`、`recent win-rate`、還是兩者共同觸發；
  3. 若 breaker 仍在，live summary 不得再把 q15/q35 calibration 寫成當前 deploy blocker。

- **Fallback if fail:**
  - 若 heartbeat 又把焦點退回 generic q15 calibration，視為 regression；
  - 若無 release evidence 就直接 relax breaker，視為風控 regression；
  - 若 probe / drilldown 再次丟失 breaker reason，視為 blocker。

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
     - `reason/streak` 已持久化
     - `component_gap_attribution.unavailable_reason` 非空
     則下一輪不得再把主焦點放回 q15 generic gap；必須直接處理 **breaker root cause / release condition**。
