# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 15:03 UTC — Heartbeat #732（bull exact bucket blocker 已轉成 machine-readable support/pathology summary；下一步直攻 q65 exact bucket root cause）_

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
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `issues.json`
  - numbered summary：`data/heartbeat_732_summary.json`

### 本輪新完成：bull blocker machine-readable support / pathology artifact
- `scripts/bull_4h_pocket_ablation.py` 已升級：
  - `live_context` 現在會攜帶 decision-quality scope / label / pathology scope / shared shifts；
  - 新增 `support_pathology_summary`，直接輸出：
    - `blocker_state`
    - `preferred_support_cohort`
    - `current_live_structure_bucket_gap_to_minimum`
    - `exact_live_bucket_proxy_gap_to_minimum`
    - `exact_live_lane_proxy_gap_to_minimum`
    - `dominant_neighbor_bucket`
    - `bucket_gap_vs_dominant_neighbor`
    - `pathology_worst_scope`
    - `recommended_action`
- `docs/analysis/bull_4h_pocket_ablation.md` 同步新增 **Support / pathology summary** 區塊。
- 這讓 bull blocker 不再只存在於口頭描述，而是可供下一輪直接讀取的 machine-readable root-cause artifact。

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_leaderboard_candidate_probe.py tests/test_train_target_metrics.py -q` → **13 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 732` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**。
- 最新 DB 狀態（#732）：
  - Raw / Features / Labels = **21414 / 12843 / 42937**
  - simulated_pyramid_win = **0.5753**
- label freshness 正常：
  - 240m lag 約 **3.4h**
  - 1440m lag 約 **23.3h**

### 模型 / shrinkage / support-aware training
- global recommended profile：**`core_only`**
- train selected profile：**`core_plus_macro`**
- `support_governance_route = exact_live_bucket_proxy_available`
- bull pocket artifacts 目前 machine-readable：
  - `bull_exact_live_lane_proxy_rows = 50`
  - `bull_live_exact_lane_bucket_proxy_rows = 38`
  - `bull_supported_neighbor_buckets_proxy_rows = 12`
- **新增 machine-readable blocker summary**：
  - `blocker_state = exact_lane_proxy_fallback_only`
  - `current_live_structure_bucket_gap_to_minimum = 50`
  - `exact_live_bucket_proxy_gap_to_minimum = 12`
  - `exact_live_lane_proxy_gap_to_minimum = 0`
  - `dominant_neighbor_bucket = ALLOW|base_allow|q85`
  - `pathology_worst_scope = regime_label+entry_quality_label`

### Live guardrail / bull blocker
- live predictor 仍正確保守：
  - regime = **bull**
  - gate = **ALLOW**
  - entry quality = **D**
  - allowed layers = **0**
  - guardrail reason = `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade`
- `live_current_structure_bucket_rows` 仍是 **0**。
- 這代表：
  - 治理 artifact 已進步；
  - 但部署 blocker **尚未解除**。

### Source blocker
- `fin_netflow` 仍是 **auth_missing**。
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵。

---

## 當前主目標

### 目標 A：直接找出 `ALLOW|base_allow|q65` exact bucket 為何仍是 0-support
本輪已完成的是：
- exact bucket blocker 已有 machine-readable summary；
- 下一輪不必再花時間整理 artifact 欄位。

下一步主目標是：
- **直接對 q65 exact bucket 0-support 做 root-cause patch / artifact**；
- 釐清是樣本尚未累積、structure bucket 規則過嚴，還是真有壞 pocket 導致 exact bucket 不應被部署。

### 目標 B：把 bull same-regime 4H pocket pathology 當成主戰場
目前 evidence 一致指向：
- worst pathology scope = **`regime_label+entry_quality_label`**
- shared shifts = **`feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`**

下一步主目標：
- 不再把 global calibration 或 retrain 當主題；
- 直接驗證 q65 vs q85 的結構差異與 gate contract 是否合理。

### 目標 C：維持 dual-profile 與 deployment blocker 的語義分離
目前雙軌仍成立：
- global winner = **`core_only`**
- train support fallback = **`core_plus_macro`**
- runtime deployment = **blocked (`allowed_layers=0`)**

下一步主目標：
- probe / metrics / docs 對下列欄位持續零漂移：
  - `selected_feature_profile`
  - `train_selected_profile`
  - `support_governance_route`
  - `support_pathology_summary.blocker_state`
  - `live_current_structure_bucket_rows`
  - `allowed_layers`

### 目標 D：維持 source auth blocker 與模型 blocker 分離治理
- `fin_netflow` 仍是 **auth_missing**。
- 這是外部 source blocker，不可混進 bull exact bucket 成功敘事。

---

## 接下來要做

### 1. 直接做 q65 exact bucket root-cause drill-down
要做：
- 比對 `ALLOW|base_allow|q65`、`ALLOW|base_allow|q85`、`bull_exact_live_lane_proxy` 三者的結構條件差異；
- 若 q65 仍 0 rows，至少留下更窄的 same-bucket artifact 或 patch；
- 若 bucket 規則過嚴，修 contract；若是真壞 pocket，保留 blocker 並把原因寫死。

### 2. 維持 governance-route 與 deployment guardrail 同步
要做：
- 持續檢查：
  - `support_governance_route`
  - `support_pathology_summary.blocker_state`
  - `support_pathology_summary.current_live_structure_bucket_gap_to_minimum`
  - `live_current_structure_bucket_rows`
  - `allowed_layers`
- 若 exact bucket 仍 0，持續維持 `0 layers`。

### 3. 維持 dual-profile 與 support-pathology 語義一致
要做：
- heartbeat summary / probe / docs 必須能 machine-read：
  - `selected_feature_profile`
  - `global_recommended_profile`
  - `train_selected_profile`
  - `train_support_cohort`
  - `support_governance_route`
  - `support_pathology_summary.blocker_state`
  - `pathology_worst_scope`
- 下一輪不應再出現「artifact 有欄位，但文件仍只用口語描述」的漂移。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 calibration 或 bull pocket 問題。

---

## 暫不優先

以下本輪後仍不排最前面：
- 放寬 bull live guardrail
- 重新把 retrain 當主題
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸已收斂成 **q65 exact bucket 0-support + same-regime 4H pathology**，不是 artifact 缺失，也不是 retrain 入口。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **q65 exact bucket 0-support root cause** 直接相關的 patch / run / verify。
2. `data/bull_4h_pocket_ablation.json.support_pathology_summary`、`data/live_predict_probe.json`、`data/leaderboard_feature_profile_probe.json` 的 blocker 語義持續零漂移。
3. bull exact bucket 若仍 0-support，runtime / docs / probe 都明確維持 blocker 語義。
4. `core_only` 與 `core_plus_macro` 的雙軌語義零漂移。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 直接推進 `ALLOW|base_allow|q65` exact bucket 的 root-cause 治理；
  2. 釐清 bull same-regime 4H pocket 到底是規則過嚴、樣本不足，還是真壞 pocket；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下 q65 exact bucket 的真 patch / artifact / verify，不能只重報目前摘要；
  2. `support_pathology_summary`、`live_predict_probe`、`leaderboard_feature_profile_probe` 對 blocker 的敘述零漂移；
  3. 若 exact bucket rows 有變化，三條路徑能同輪同步更新結論。

- **Fallback if fail:**
  - 若 q65 exact bucket 仍 0 support，維持 `0 layers`；
  - 若仍無法找到 root cause，下一輪至少要留下更窄的 exact-bucket / q85 proxy 對照 artifact；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull support/pathology contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_732_summary.json`。
  2. 再讀：
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/live_predict_probe.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若 `support_pathology_summary.blocker_state` 仍是 `exact_lane_proxy_fallback_only`、`current_live_structure_bucket_gap_to_minimum` 仍是 50、`allowed_layers` 仍是 0，下一輪不得再把「artifact 已齊」當主題；必須直接推進 **q65 exact bucket root cause**。