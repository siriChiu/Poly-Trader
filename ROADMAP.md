# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 08:27 UTC — Heartbeat #1012（本輪新增 q15 exact-bucket root-cause artifact，讓 heartbeat 能 machine-read 判斷 boundary review 是否值得進入下一輪 patch。）_

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
  - `data/circuit_breaker_audit.json`
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `issues.json`
  - numbered summary：`data/heartbeat_1012_summary.json`

### 本輪新完成：q15 root-cause artifact 正式進入 fast heartbeat
- `scripts/hb_q15_bucket_root_cause.py`
  - 新增 q15 exact-bucket root-cause artifact
  - machine-read：`verdict / candidate_patch_type / candidate_patch_feature / gap_to_q35_boundary / near_boundary_rows / verify_next / carry_forward`
- `scripts/hb_parallel_runner.py`
  - fast heartbeat 自動刷新 q15 root-cause artifact，並寫入 summary
- `tests/test_q15_bucket_root_cause.py`
  - 鎖住 boundary vs projection 的基本判讀
- `tests/test_hb_parallel_runner.py`
  - 鎖住 root-cause diagnostics 與 runner order：`leaderboard -> q15 support -> q15 root-cause`
- `ARCHITECTURE.md`
  - 新增 q15 exact-bucket root-cause contract

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_q15_bucket_root_cause.py tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py -q` → **26 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1012` → **通過**

### 資料與 canonical target
- 最新 DB 狀態（#1012）：
  - Raw / Features / Labels = **21588 / 13017 / 43345**
  - simulated_pyramid_win = **0.5756**
- label freshness 正常：
  - 240m lag 約 **3.4h**
  - 1440m lag 約 **23.1h**

### IC / drift / live runtime
- Global IC：**19/30**
- TW-IC：**18/30**
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

### q15 / support / root-cause 現況
- current live structure bucket：**`CAUTION|structure_quality_caution|q15`**
- q15 support audit：
  - `support_governance_route = exact_live_bucket_proxy_available`
  - `preferred_support_cohort = bull_live_exact_bucket_proxy`
  - `exact_live_bucket_proxy_rows = 4`
  - `exact_live_lane_proxy_rows = 421`
  - `supported_neighbor_rows = 158`
  - `support_route.verdict = exact_bucket_missing_proxy_reference_only`
  - `floor_cross_legality = math_cross_possible_but_illegal_without_exact_support`
  - `best_single_component = feat_4h_bias50`
  - `remaining_gap_to_floor = 0.1148`
- q15 root-cause artifact：
  - `verdict = boundary_sensitivity_candidate`
  - `candidate_patch_type = bucket_boundary_review`
  - `candidate_patch_feature = feat_4h_bb_pct_b`
  - `current_live.structure_quality = 0.3384`
  - `gap_to_q35_boundary = 0.0116`
  - `exact_live_lane.near_boundary_rows = 2`
  - `dominant_neighbor_bucket = CAUTION|structure_quality_caution|q35`
- 治理結論：
  - **已完成**：q15 blocker 現在不再只是籠統文字，而是可 machine-read 的 boundary candidate artifact；
  - **未完成**：exact support 仍未達 deployment 門檻，runtime 仍不可 deployment；
  - **下一步**：不能直接改 boundary，必須先做 replay / counterfactual 驗證。

### Q35 / profile split / breaker / source blocker 現況
- q35 scaling：
  - `overall_verdict = broader_bull_cohort_recalibration_candidate`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`
- profile split：
  - global shrinkage winner：`core_only`
  - production profile：`core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
- circuit breaker audit：
  - `verdict = mixed_horizon_false_positive`
  - aligned 1440m live horizon：`release_ready = true`
- `fin_netflow`：**auth_missing** / coverage **0.0%**

---

## 當前主目標

### 目標 A：驗證 q15 boundary sensitivity 是否真能產生 exact-lane current bucket rows
目前已確認：
- q15 root-cause artifact 顯示 `boundary_sensitivity_candidate`；
- `gap_to_q35_boundary = 0.0116`，且 `near_boundary_rows = 2`；
- 這足以把 boundary review 升級成**候選研究路徑**，但還不是 deployment patch。

下一步主目標：
- **做 q15↔q35 boundary replay / counterfactual，回答 boundary review 是否真的增加 exact-lane current bucket rows，而不是把 0-row blocker 假裝成已解。**

### 目標 B：把 candidate patch feature 轉成可驗證的最小反事實
目前已確認：
- `candidate_patch_feature = feat_4h_bb_pct_b`
- `needed_raw_delta_to_cross_q35 = 0.0341`
- 同時 `feat_4h_bias50` 仍是 floor gap 最佳單點 component，但 legality 仍被 support blocker 擋住

下一步主目標：
- **先驗 `feat_4h_bb_pct_b` 是否只是 boundary proxy，還是實際最小可修補 component；未驗前不得改 runtime gate。**

### 目標 C：維持 q35 / profile split / breaker 的次級治理定位
目前已確認：
- q35 不是當前 root blocker；
- `core_only` vs `core_plus_macro_plus_4h_structure_shift` 仍是 dual-role governance；
- breaker 仍明確是 mixed-horizon false positive。

下一步主目標：
- 只做零漂移維護，不讓背景問題重新搶走 q15 boundary replay 的主焦點。

### 目標 D：維持 source auth blocker 顯式治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 q15 / boundary / profile / breaker 敘事

---

## 接下來要做

### 1. 做 q15 boundary replay artifact
要做：
- 對 current live `q15` bucket 明確回答：
  - 若把 q15↔q35 邊界做最小調整，是否真的會產生 exact-lane current bucket rows？
  - 這些新 rows 是否仍不足 `minimum_support_rows`？
  - boundary review 會不會只是把 blocker 從 `q15` 改標成 `q35`，而沒有補到 exact support？
- 產出 machine-readable JSON + markdown
- 驗證 heartbeat summary 能直接摘取 `verdict / candidate_patch / verify`

### 2. 做 `feat_4h_bb_pct_b` counterfactual
要做：
- 用當前 live row 驗證：
  - `feat_4h_bb_pct_b` 往上調到 crossing threshold 後，structure bucket 是否真的跨到 q35？
  - 這種變動是否仍符合 q15 support legality，不會繞過 exact support blocker？
  - 若 `feat_4h_bb_pct_b` 不是真 root cause，下一個應該檢查的是 boundary 公式、`feat_4h_dist_bb_lower`，還是 support accumulation
- 產出 machine-readable JSON + markdown
- 驗證 summary 能直接回答「boundary 值得 patch 嗎？」

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
> 當前真正的 live blocker 已經更精確地收斂成 **q15 exact support 未達標 + boundary sensitivity candidate 尚未驗證**；本輪已把 root-cause artifact 建好，下一輪必須直接驗 replay / counterfactual，而不是再回 generic q35 / breaker 敘事。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **q15 boundary replay / exact-lane row generation** 直接相關的真 patch / run / verify。
2. `q15_support_audit / q15_bucket_root_cause / heartbeat summary` 對 q15 support route、boundary candidate、runtime blocker 的描述必須零漂移。
3. mixed-horizon circuit breaker 不得回歸。
4. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 做 q15 boundary replay / counterfactual artifact；
  2. 驗 `feat_4h_bb_pct_b` 是否真為 candidate patch feature；
  3. 維持 `profile_split / fin_netflow auth blocker / breaker false-positive` 零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q15 boundary replay 或 exact-lane row generation** 直接相關的 patch / artifact / verify；
  2. 必須 machine-read 回答 boundary review 是否真的增加 exact-lane current bucket rows；
  3. `q15_support_audit`、`q15_bucket_root_cause`、`leaderboard_feature_profile_probe` 對 `support_governance_route / exact_bucket_proxy_rows / runtime blocker` 不得再漂移。

- **Fallback if fail:**
  - 若 boundary replay 無法增加 exact-lane current bucket rows，視為 boundary candidate 被否決，下一輪改查 structure component scoring / support accumulation；
  - 若 heartbeat 沒有 replay / counterfactual 證據就直接 relax runtime gate，視為風控 regression；
  - 若 next run 仍沒有 q15 boundary / component artifact，升級為 q15 exact-bucket blocker。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 q15 boundary contract 被正式採納）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1012_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q15_support_audit.json`
     - `data/q15_bucket_root_cause.json`
     - `data/leaderboard_feature_profile_probe.json`
     - `data/bull_4h_pocket_ablation.json`
  3. 若同時成立：
     - `q15_support_audit.support_route.verdict = exact_bucket_missing_proxy_reference_only`
     - `q15_bucket_root_cause.verdict = boundary_sensitivity_candidate`
     - `q15_bucket_root_cause.current_live.gap_to_q35_boundary <= 0.02`
     - `q15_bucket_root_cause.exact_live_lane.near_boundary_rows > 0`
     - `live_predict_probe.allowed_layers = 0`
     則下一輪不得再回 generic q35 / breaker；必須直接處理 **q15 boundary replay / feat_4h_bb_pct_b counterfactual / exact-lane row generation**。
