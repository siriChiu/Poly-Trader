# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 19:12 UTC — Heartbeat #741（bull q35 exact support 已跨過 minimum support；support blocker 已解除，proxy contract 也已同步升級為 `exact_bucket_supported_proxy_not_required`。主路線正式從「補 support」切到「exact-bucket post-threshold verification」。）_

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
  - numbered summary：`data/heartbeat_741_summary.json`

### 本輪新完成：bull exact support 已跨過 minimum，proxy blocker 語義同步退場
- `scripts/bull_4h_pocket_ablation.py` 已升級：
  - 當 `exact_bucket_root_cause=exact_bucket_supported` 時，summary 現在固定輸出：
    - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
    - `proxy_boundary_reason = current live structure bucket 已達 minimum support；後續治理與驗證應直接以 exact bucket 為主，proxy 只保留輔助比較，不再作 blocker 判讀。`
- `tests/test_bull_4h_pocket_ablation.py`
  - 已鎖住 exact-supported regression。
- `tests/test_hb_leaderboard_candidate_probe.py`
  - 已鎖住 leaderboard alignment 在 exact-supported 狀態下也輸出同一個 verdict。
- `python scripts/hb_parallel_runner.py --fast --hb 741`
  - 已刷新 bull artifact / leaderboard probe / heartbeat summary，確認 exact-supported contract 已零漂移。

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **19 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 741` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#741）：
  - Raw / Features / Labels = **21425 / 12854 / 43005**
  - simulated_pyramid_win = **0.5762**
- label freshness 正常：
  - 240m lag 約 **3.3h**
  - 1440m lag 約 **23.0h**

### IC / drift / live contract
- Global IC：**19/30**
- TW-IC：**25/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- drift primary window：**100**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**bull 61.0%**
- live predictor：
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**D**
  - decision-quality label：**C**
  - allowed layers：**0**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=61**
  - exact live lane：**78 rows / win_rate 0.8333 / quality 0.5429**
  - `decision_quality_exact_live_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
  - `decision_quality_exact_live_lane_toxic_bucket`：**`CAUTION|structure_quality_caution|q15` rows=4 / win_rate 0.0**

### 模型 / shrinkage / support-aware ranking
- global recommended profile：**`core_only`**
- train selected：**`core_plus_macro`**
- bull artifact 最新 bull-all cohort 推薦：**`core_plus_macro_plus_4h_structure_shift`**
- leaderboard selected profile：**`core_only`**
- dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
- bull pocket artifact（當前 live bucket）
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35`**
  - exact rows：**61**
  - exact bucket gap to minimum：**0**
  - exact-bucket proxy rows：**114**
  - exact-lane proxy rows：**377**
  - `blocker_state = exact_live_bucket_supported`
  - `exact_bucket_root_cause = exact_bucket_supported`
  - `support_governance_route = exact_live_bucket_supported`
  - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
  - `exact_lane_bucket_verdict = toxic_sub_bucket_identified`
  - `bucket_comparison_takeaway = exact_bucket_supported`

### Source blocker
- `fin_netflow` 仍是 **auth_missing**
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵

---

## 當前主目標

### 目標 A：完成 exact-bucket-supported 之後的正式驗證，而不是停留在 support 達標訊息
本輪已確認：
- current q35 bucket：**61 rows / 已高於 minimum support 50**；
- support blocker 已解除，proxy 也已退回輔助比較角色；
- 但 train / leaderboard / live path 還沒有完成「support 達標後應採何 profile / 何治理語義」的正式驗證。

下一步主目標是：
- **直接把 current q35 exact-supported 當成主驗證母體**；
- 驗證 train path 是否要從 `core_plus_macro` 轉到新的 bull exact-supported profile；
- 驗證 leaderboard / docs / runtime 是否都明講「support 已解、但 q15 toxic pocket 與 CAUTION gate 仍保守存在」。

### 目標 B：把 proxy contract 固定成 exact-supported 後的非 blocker 輔助語義
本輪已確認：
- bull artifact、leaderboard probe、heartbeat summary 都已用：
  - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
- 這表示 proxy 不再是 support blocker 判讀核心。

下一步主目標是：
- **維持這條 contract 不漂移**；
- 只要 current exact bucket 仍 ≥50，就不得回退成 `proxy_boundary_inconclusive` 或 `proxy_governance_reference_only_exact_support_blocked`。

### 目標 C：維持 q15 toxic pocket 與 q35 exact-supported 的雙重語義
目前已明確：
- q35：**exact support 已足夠**
- q15：**lane-internal toxic sub-bucket**
- runtime deployment：**仍保守（allowed_layers=0）**，原因是 CAUTION + D quality，不是 support 不足

下一步主目標：
- 保持所有 surface 都明講：
  - q35 support 已到位；
  - q15 仍是 veto 候選；
  - blocked / hold 的原因來自 gate / quality，不是 q35 support deficit。

### 目標 D：把 train / leaderboard 的 dual-profile 狀態從 pre-threshold fallback 升級成 post-threshold governance
目前雙軌語義仍是：
- global shrinkage winner = **`core_only`**
- train selected = **`core_plus_macro`**
- bull artifact 最新推薦 = **`core_plus_macro_plus_4h_structure_shift`**
- leaderboard visible winner = **`core_only`**

下一步主目標：
- 以 exact-supported current bucket 重新驗證 profile governance；
- 判定 train path 是否仍合理停在 `core_plus_macro`，或應切換到新的 exact-supported bull profile；
- 若仍保留 dual-profile，文件必須能清楚說出原因與 verify 門檻。

### 目標 E：維持 source auth blocker 與 bull pathology 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 bull support 達標敘事

---

## 接下來要做

### 1. 做 exact-bucket post-threshold verification
要做：
- 以 **q35 exact-supported** 條件重跑 bull profile / governance 驗證；
- 明確比較：
  - `core_only`
  - `core_plus_macro`
  - `core_plus_macro_plus_4h_structure_shift`
- 決定 train / leaderboard / docs 的 exact-supported 收斂語義。

### 2. 鎖住 exact-supported proxy contract
要做：
- 持續檢查 artifact / leaderboard probe / heartbeat summary / docs 的：
  - `support_blocker_state = exact_live_bucket_supported`
  - `support_governance_route = exact_live_bucket_supported`
  - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
- 任何一條路徑回退成舊 blocker 文案都視為 regression。

### 3. 維持 q15 toxic pocket 與 q35 supported 的分工
要做：
- 持續檢查：
  - `exact_lane_bucket_verdict`
  - `decision_quality_exact_live_lane_toxic_bucket`
  - `allowed_layers`
- 若 current bucket 落入 q15，runtime 必須直接 veto；
- 若 current bucket 仍是 q35，blocked 原因必須明確寫成 gate / quality，而不是 support。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 bull exact-support 後的新問題。

---

## 暫不優先

以下本輪後仍不排最前面：
- 直接放寬 live execution guardrail
- 把 support 達標解讀成可立即部署
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸已從「q35 support 還差幾 rows」轉成 **exact-supported 後 train / leaderboard / runtime 的正式治理驗證**；不是資料量不夠，也不是 proxy 還講不清楚。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **exact-bucket post-threshold verification / train-path sync / leaderboard governance** 直接相關的真 patch / run / verify。
2. `data/bull_4h_pocket_ablation.json.support_pathology_summary`、`data/live_predict_probe.json`、`data/leaderboard_feature_profile_probe.json`、`data/heartbeat_741_summary.json` 的 exact-supported 語義持續零漂移。
3. 若 q35 exact bucket 仍 ≥50，所有 surface 都不得再把 support deficit 當 blocker。
4. 若 q35 exact bucket 跌回 <50，下一輪必須同輪恢復 under-minimum blocker contract。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 針對 **exact-bucket-supported** 狀態完成 bull post-threshold verification；
  2. 若 q35 rows 仍 ≥50，持續驗證 `exact_bucket_supported_proxy_not_required` 與 q15 toxic contract 在所有 surface 零漂移；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下至少一個與 **post-threshold verification / train-path sync / leaderboard governance** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`exact_lane_bucket_verdict`、`decision_quality_exact_live_lane_toxic_bucket`、`allowed_layers` 對 bull lane 的敘述零漂移；
  3. 若 q35 exact rows 仍 ≥50，所有路徑同輪同步維持 exact-supported 結論；若 rows 再跌回 <50，必須同輪恢復 support blocker 文案。

- **Fallback if fail:**
  - 若 train / leaderboard 仍停在 pre-threshold fallback，下一輪升級為 `post_threshold_profile_governance_stalled`；
  - 若 proxy contract 任一路徑回退成 `proxy_boundary_inconclusive`，視為 exact-supported governance regression；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 exact-supported contract 再擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_741_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若 `current_live_structure_bucket = CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_rows >= 50`、`support_blocker_state = exact_live_bucket_supported`、`support_governance_route = exact_live_bucket_supported`、`proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`、`decision_quality_exact_live_lane_bucket_verdict = toxic_sub_bucket_identified`、`decision_quality_exact_live_lane_toxic_bucket.bucket = CAUTION|structure_quality_caution|q15`、`allowed_layers = 0` 仍同時成立，下一輪不得再把「support 達標」當成功；必須直接推進 **exact-bucket post-threshold verification / train-path sync / q15 toxic pocket 保守治理**。
