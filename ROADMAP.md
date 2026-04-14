# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 18:45 UTC — Heartbeat #740（bull q35 proxy contract 已正式定稿：proxy 只可治理參考、不可解除 deployment blocker；當前主路線從「定義 blocker」進入「追蹤 q35 exact support 是否跨過 50 rows」。）_

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
  - numbered summary：`data/heartbeat_740_summary.json`

### 本輪新完成：proxy governance contract 已正式定稿
- `scripts/bull_4h_pocket_ablation.py` 已升級：
  - 讀不到 `recent_broader_same_bucket.dominant_regime` 時，會回退到 `broad_recent500_dominant_regime`；
  - 當 `exact_bucket_present_but_below_minimum` 且 historical same-bucket proxy 仍可作治理參考時，summary 現在固定輸出：
    - `proxy_boundary_verdict = proxy_governance_reference_only_exact_support_blocked`
    - `proxy_boundary_reason = historical same-bucket proxy 可保留作 governance 參考，但 current exact support 未滿，proxy 不得作 deployment 放行依據`
- `scripts/hb_leaderboard_candidate_probe.py` 已同步：
  - alignment payload 現在直接攜帶：
    - `proxy_boundary_verdict`
    - `proxy_boundary_reason`
    - `exact_lane_bucket_verdict`
    - `exact_lane_toxic_bucket`
- regression tests 已補：
  - `tests/test_bull_4h_pocket_ablation.py`
  - `tests/test_hb_leaderboard_candidate_probe.py`
  - `tests/test_hb_parallel_runner.py`
- `ARCHITECTURE.md` 已同步 #740 contract。

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **18 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 740` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#740）：
  - Raw / Features / Labels = **21423 / 12852 / 42985**
  - simulated_pyramid_win = **0.5759**
- label freshness 正常：
  - 240m lag 約 **3.3h**
  - 1440m lag 約 **23.0h**

### IC / drift / live contract
- Global IC：**19/30**
- TW-IC：**25/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- drift primary window：**250**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**chop 83.2%**
- live predictor：
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**D**
  - decision-quality label：**C**
  - allowed layers：**0**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=42**
  - exact live lane：**59 rows / win_rate 0.7797 / quality 0.4908**
  - `decision_quality_exact_live_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
  - `decision_quality_exact_live_lane_toxic_bucket`：**`CAUTION|structure_quality_caution|q15` rows=4 / win_rate 0.0000**
  - execution guardrail：**未額外觸發**（`allowed_layers_raw` 已是 0）

### 模型 / shrinkage / support-aware ranking
- global recommended profile：**`core_only`**
- bull support-aware / train selected：**`core_plus_macro`**
- leaderboard selected profile：**`core_only`**
- dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
- blocked candidate：**`core_plus_macro` → `under_minimum_exact_live_structure_bucket`**
- bull pocket artifact（當前 live bucket）
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35`**
  - exact rows：**42**
  - exact bucket gap to minimum：**8**
  - exact-bucket proxy rows：**91**
  - exact-lane proxy rows：**354**
  - supported neighbor rows：**84**
  - `blocker_state = exact_lane_proxy_fallback_only`
  - `exact_bucket_root_cause = exact_bucket_present_but_below_minimum`
  - `support_governance_route = exact_live_bucket_present_but_below_minimum`
  - `proxy_boundary_verdict = proxy_governance_reference_only_exact_support_blocked`
  - `exact_lane_bucket_verdict = toxic_sub_bucket_identified`
  - `bucket_comparison_takeaway = support_gap_unresolved`

### Source blocker
- `fin_netflow` 仍是 **auth_missing**
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵

---

## 當前主目標

### 目標 A：把 bull q35 blocker 從「接近達標」推進到「跨過 50 rows 後的正式驗證」
本輪已確認：
- current q35 bucket：**42 rows / win_rate 1.0000 / quality 0.7148**；
- exact live lane：**59 rows / win_rate 0.7797 / quality 0.4908**；
- gap 已從 **32 → 8**，support accumulation 正在發生。

下一步主目標是：
- **先確認 q35 exact support 是否跨過 50**；
- 一旦跨過 50，不能直接放行，必須做「解除 blocker 後是否仍與 q15 toxic pocket / live DQ / leaderboard contract 一致」的驗證。

### 目標 B：把 proxy contract 從「本輪剛定稿」變成「後續零漂移治理契約」
本輪已確認：
- bull artifact、leaderboard probe、heartbeat summary、markdown docs 都已使用：
  - `proxy_governance_reference_only_exact_support_blocked`
- 這代表 proxy 已從模糊觀察，升級成正式治理語義。

下一步主目標是：
- **不要再討論 proxy 是否可用，而是持續驗證所有 surface 是否維持同一句 contract**；
- 只要 q35 exact support 未滿 50，proxy 就只能治理參考、不能 deployment。

### 目標 C：維持 q15 toxic pocket 與 q35 support blocker 的雙重語義
目前已明確：
- q15 = **toxic lane-internal pathology**
- q35 = **目前不是 toxic，但 exact support 仍不足**
- runtime deployment = **blocked (`allowed_layers=0`)**

下一步主目標：
- 保持所有 surface 都明講：
  - q15 壞，是 veto 候選；
  - q35 健康但未達 minimum support；
  - blocked 的主因是 support，不是 q35 自身表現失敗。

### 目標 D：維持 shrinkage winner 與 support-aware candidate 的雙軌治理
目前雙軌語義仍是：
- global shrinkage winner = **`core_only`**
- train support-aware fallback = **`core_plus_macro`**
- leaderboard visible winner = **`core_only`**
- runtime deployment = **blocked (`allowed_layers=0`)**

下一步主目標：
- 若 q35 exact rows 仍 < 50，繼續維持 `core_plus_macro` 為 blocked candidate；
- 若 q35 exact rows ≥ 50，再重新驗證 support-aware profile 是否仍成立。

### 目標 E：維持 source auth blocker 與 bull pathology 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 bull q35 / q15 pocket 成功敘事

---

## 接下來要做

### 1. 追蹤 q35 exact support 是否跨過 minimum support
要做：
- 每輪檢查 `current_live_structure_bucket_rows` 是否從 **42** 成長到 **≥50**；
- 若跨過 50，立即切換到「解除 blocker 驗證」；
- 若仍 < 50，維持 `allowed_layers=0`。

### 2. 鎖住 proxy governance-only contract
要做：
- 持續檢查 artifact / leaderboard probe / heartbeat summary / markdown docs 的：
  - `proxy_boundary_verdict`
  - `proxy_boundary_reason`
- 任何一條路徑回退成 `proxy_boundary_inconclusive` 都視為 regression。

### 3. 維持 q15 toxic pocket 與 q35 support blocker 的分工
要做：
- 持續檢查：
  - `exact_lane_bucket_verdict`
  - `decision_quality_exact_live_lane_toxic_bucket`
  - `support_blocker_state`
  - `support_governance_route`
  - `allowed_layers`
- 若 current bucket 落入 q15，runtime 必須直接 veto；
- 若 current bucket 仍是 q35，blocked 原因必須維持為 support。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 bull lane 問題

---

## 暫不優先

以下本輪後仍不排最前面：
- 放寬 live execution guardrail
- 重新把 retrain 當主題
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸已收斂成 **q35 exact support 還差 8 rows + proxy contract 要持續零漂移 + q15 toxic pocket 要持續保留 veto 語義**；不是模型容量問題，也不是還看不懂 bull lane 病灶。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **q35 exact support 達標驗證** 或 **proxy / toxic contract 零漂移** 直接相關的 patch / run / verify。
2. `data/bull_4h_pocket_ablation.json.support_pathology_summary`、`data/live_predict_probe.json`、`data/leaderboard_feature_profile_probe.json`、`data/heartbeat_740_summary.json` 的 blocker 語義持續零漂移。
3. q35 exact bucket 若仍 < 50，runtime / docs / probe 都明確維持 blocker 語義。
4. q35 exact bucket 若跨過 50，下一輪必須轉成「解除 blocker 驗證」，不能直接部署。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 追蹤 `CAUTION|structure_quality_caution|q35` exact rows 是否從 **42 → ≥50**；
  2. 若仍 < 50，持續驗證 `proxy_governance_reference_only_exact_support_blocked` 與 q15 toxic contract 是否在所有 surface 零漂移；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下 q35 support 驗證或 proxy/t toxic contract 對齊的真 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`exact_lane_bucket_verdict`、`decision_quality_exact_live_lane_toxic_bucket`、`allowed_layers` 對 blocker 的敘述零漂移；
  3. 若 q35 exact rows 仍 < 50，所有路徑同輪同步維持 blocker 結論；若 q35 exact rows ≥ 50，必須改做解除 blocker 驗證。

- **Fallback if fail:**
  - 若 q35 exact rows 持續卡在 42 左右，下一輪升級為 support accumulation stalled 調查；
  - 若 proxy contract 任一路徑回退成 `proxy_boundary_inconclusive`，視為 governance regression；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull governance contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_740_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若 `current_live_structure_bucket = CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_rows < 50`、`support_blocker_state = exact_lane_proxy_fallback_only`、`support_governance_route = exact_live_bucket_present_but_below_minimum`、`proxy_boundary_verdict = proxy_governance_reference_only_exact_support_blocked`、`decision_quality_exact_live_lane_bucket_verdict = toxic_sub_bucket_identified`、`decision_quality_exact_live_lane_toxic_bucket.bucket = CAUTION|structure_quality_caution|q15`、`allowed_layers = 0` 仍同時成立，下一輪不得再把「proxy contract 已定稿」當成功；必須直接推進 **q35 exact support 達標驗證 / stalled root-cause / blocker 持續治理**。
