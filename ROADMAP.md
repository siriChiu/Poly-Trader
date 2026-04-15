# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 07:57 UTC — Heartbeat #1011（本輪把 q15 support audit 與最新 leaderboard candidate probe 對齊，避免 stale governance input 讓 q15 support route / preferred cohort 漂移。）_

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
  - `data/circuit_breaker_audit.json`
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `issues.json`
  - numbered summary：`data/heartbeat_1011_summary.json`

### 本輪新完成：q15 support audit 與 leaderboard governance input 對齊
- `scripts/hb_parallel_runner.py`
  - `hb_q15_support_audit.py` 改為在 `hb_leaderboard_candidate_probe.py` **之後**執行
  - 避免 q15 audit 吃到前一輪 leaderboard probe，造成 support route / proxy rows 漂移
- `scripts/hb_q15_support_audit.py`
  - 當 `support_governance_route = exact_live_bucket_proxy_available` 時，`preferred_support_cohort` 明確落成 `bull_live_exact_bucket_proxy`
- `tests/test_hb_parallel_runner.py`
  - 新增 runner 執行順序 regression test：`leaderboard -> q15 audit`
- `tests/test_q15_support_audit.py`
  - 鎖住 `preferred_support_cohort = bull_live_exact_bucket_proxy`

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py -q` → **23 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1011` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#1011）：
  - Raw / Features / Labels = **21587 / 13016 / 43343**
  - simulated_pyramid_win = **0.5756**
- label freshness 正常：
  - 240m lag 約 **3.0h**
  - 1440m lag 約 **23.2h**

### IC / drift / live runtime
- Global IC：**19/30**
- TW-IC：**17/30**
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
  - reason：**entry_quality_below_trade_floor + unsupported_exact_live_structure_bucket_blocks_trade**

### q15 / q35 / support route 現況
- current live structure bucket：**`CAUTION|structure_quality_caution|q15`**
- q15 component gap：
  - `remaining_gap_to_floor = 0.1071`
  - `best_single_component = feat_4h_bias50`
  - `required_score_delta_to_cross_floor = 0.357`
- q15 support audit：
  - `support_governance_route = exact_live_bucket_proxy_available`
  - `preferred_support_cohort = bull_live_exact_bucket_proxy`
  - `exact_live_bucket_proxy_rows = 4`
  - `exact_live_lane_proxy_rows = 420`
  - `supported_neighbor_rows = 157`
  - `floor_cross_legality = math_cross_possible_but_illegal_without_exact_support`
- q35 scaling：
  - `overall_verdict = broader_bull_cohort_recalibration_candidate`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`

### Breaker / profile split / source blocker 現況
- circuit breaker audit：
  - `verdict = mixed_horizon_false_positive`
  - aligned 1440m live horizon：`release_ready = true`
- global shrinkage winner：`core_only`
- production train profile：`core_plus_macro_plus_4h_structure_shift`
- leaderboard state：`leaderboard_global_winner_vs_train_support_fallback`
- `fin_netflow`：**auth_missing** / coverage **0.0%**

### 治理結論
- **已完成**：q15 audit 現在會讀到本輪最新 leaderboard governance input，support route / preferred cohort 不再漂移。
- **未完成**：current q15 exact bucket 仍是 **0/50 rows**，runtime 仍不可 deployment。
- **降級處理**：q35 scaling、profile split、breaker 調查都維持背景治理，主問題仍是 q15 exact bucket support。

---

## 當前主目標

### 目標 A：把 q15 exact bucket 0-row blocker 轉成可修補的 root cause
目前已確認：
- breaker 已清掉；
- current live path 真 blocker 是 `q15 exact bucket rows=0`；
- q15 artifact 與 leaderboard probe 已對齊，現在可以信任這條治理訊號。

下一步主目標：
- **把 `same_lane_shifted_to_neighbor_bucket` 拆成具體可 patch 的邊界 / 結構 scoring / live projection 根因。**

### 目標 B：把 q15 bias50 gap 轉成 exact-bucket-aware counterfactual
目前已確認：
- `remaining_gap_to_floor = 0.1071`
- `feat_4h_bias50` 是唯一可單點跨 floor 的 component
- 但在 exact support 尚未達標前，這只能算 calibration research，不能 deployment

下一步主目標：
- **驗證要讓 q15 bucket 產生真樣本，應優先改哪個結構 component，而不是直接 relax bias50 score。**

### 目標 C：維持 q35 / profile split / breaker 的次級治理定位
目前已確認：
- q35 不是當前 root blocker；
- `core_only` vs `core_plus_macro_plus_4h_structure_shift` 仍是 dual-role governance；
- breaker 仍明確是 mixed-horizon false positive，不該回到主治理帶寬。

下一步主目標：
- 只做零漂移維護，不讓這些背景問題重新搶走 q15 exact bucket 的主焦點。

### 目標 D：維持 source auth blocker 顯式治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 q15 / profile / breaker 敘事

---

## 接下來要做

### 1. 做 q15 exact-bucket root-cause artifact
要做：
- 對 current live `q15` bucket 明確回答：
  - 為何 same lane 會落到 neighbor bucket？
  - 是 `structure_quality` 分位邊界、4H feature projection、還是 live row bucket 定義造成？
  - 哪個最小 patch 最可能讓 exact q15 bucket 出現真樣本？
- 產出 machine-readable JSON + markdown
- 驗證 heartbeat summary 能直接摘取 `root_cause / candidate_patch / verify`

### 2. 做 q15 component-to-bucket counterfactual
要做：
- 用當前 live row 的 `entry_quality_components` + `support_route` 驗證：
  - `feat_4h_bias50` 若調整，是否只是跨 floor，還是也能讓 row 進入有支持的 bucket？
  - 若 bias50 不足以改變 bucket，下一個該檢查的 structure component 是誰？
  - 所有 counterfactual 是否仍遵守 `exact support 未達標不得 deployment` 的 guardrail
- 產出 machine-readable JSON + markdown
- 驗證 summary 能直接回答「為何仍 0 層」與「為何仍不可 deployment」

### 3. 維持 blocker-aware profile governance
要做：
- 持續檢查：
  - `leaderboard_selected_profile`
  - `train_selected_profile`
  - `dual_profile_state`
  - `support_governance_route`
- 但在 q15 blocker 清除前，不把 profile 收斂當成第一優先

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 q15 或 leaderboard 問題

---

## 暫不優先

以下本輪後仍不排最前面：
- 再次調查 circuit breaker（除非 mixed-horizon regression 回來）
- 把 q35 scaling 當當前 deploy blocker
- 直接統一 leaderboard / production profile
- UI 美化與 fancy controls

原因：
> 當前真正的 live blocker 已經明確是 **q15 exact bucket 0-row support + exact-bucket root cause 未拆開**；本輪已把治理 artifact 漂移修好，下一輪必須直接追 root cause，而不是再回背景問題。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **q15 exact bucket row generation / boundary repair** 直接相關的真 patch / run / verify。
2. `q15_support_audit / leaderboard_feature_profile_probe / heartbeat summary` 對 q15 support route 的描述必須零漂移。
3. mixed-horizon circuit breaker 不得回歸。
4. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 做 q15 exact-bucket root-cause artifact；
  2. 做 q15 component-to-bucket counterfactual；
  3. 維持 `profile_split / fin_netflow auth blocker / breaker false-positive` 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q15 exact bucket row generation 或 boundary repair** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答 `same_lane_shifted_to_neighbor_bucket` 的最小可修補原因；
  3. `q15_support_audit` 與 `leaderboard_feature_profile_probe` 的 `support_governance_route / exact_bucket_proxy_rows` 不得再漂移。

- **Fallback if fail:**
  - 若 heartbeat 又把主焦點退回 breaker 或 generic q35，視為 regression；
  - 若沒有 exact support 證據就直接 relax runtime gate，視為風控 regression；
  - 若 next run 仍沒有 exact-bucket repair path，升級為 q15 exact-bucket blocker。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 q15 exact-bucket row generation contract 被正式擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1011_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q15_support_audit.json`
     - `data/leaderboard_feature_profile_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `data/circuit_breaker_audit.json`
  3. 若同時成立：
     - `q15_support_audit.support_route.verdict = exact_bucket_missing_proxy_reference_only`
     - `q15_support_audit.floor_cross_legality.legal_to_relax_runtime_gate = false`
     - `leaderboard_feature_profile_probe.alignment.support_governance_route = exact_live_bucket_proxy_available`
     - `live_predict_probe.current_live_structure_bucket = CAUTION|structure_quality_caution|q15`
     - `live_predict_probe.allowed_layers = 0`
     則下一輪不得再回 generic q35 / breaker；必須直接處理 **q15 exact bucket row generation / same-lane-to-neighbor shift root cause**。
