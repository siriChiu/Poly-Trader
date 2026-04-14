# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 18:20 UTC — Heartbeat #739（bull exact-lane q15 toxic pocket 已正式接進 live predictor contract；現在系統已能在「current bucket 本身就是 toxic bucket」時直接 veto，同時保護 q35 current bucket 不被誤傷。接下來主軸從「找病灶」轉成「定稿 proxy / blocker contract」。）_

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
  - numbered summary：`data/heartbeat_739_summary.json`

### 本輪新完成：exact-lane toxic sub-bucket 已接進 live predictor runtime contract
- `model/predictor.py` 已升級：
  - exact live lane 現在會固定輸出 `exact_lane_bucket_diagnostics`；
  - decision-quality contract 現在固定輸出：
    - `decision_quality_exact_live_lane_bucket_verdict`
    - `decision_quality_exact_live_lane_bucket_reason`
    - `decision_quality_exact_live_lane_toxic_bucket`
    - `decision_quality_exact_live_lane_bucket_diagnostics`
  - 若 current live structure bucket 本身就是 exact-lane toxic bucket，現在會升級成 **`toxic_sub_bucket_current_bucket`** runtime veto，直接把 `allowed_layers` 壓到 0；
  - 若 current bucket 不是 toxic bucket，則只保留 diagnostics，不連坐誤傷 healthy current bucket。
- `scripts/hb_predict_probe.py` 已同步：
  - probe JSON 直接攜帶 exact-lane toxic bucket diagnostics。
- `scripts/hb_parallel_runner.py` 已同步：
  - fast heartbeat summary 直接攜帶 live predictor toxic-bucket diagnostics。
- regression tests 已補：
  - `tests/test_api_feature_history_and_predictor.py`
  - `tests/test_hb_parallel_runner.py`
- `ARCHITECTURE.md` 已同步 #739 contract。

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q` → **39 passed**
- `source venv/bin/activate && python scripts/hb_predict_probe.py` → **通過**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 739` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#739）：
  - Raw / Features / Labels = **21422 / 12851 / 42960**
  - simulated_pyramid_win = **0.5755**
- label freshness 正常：
  - 240m lag 約 **3.3h**
  - 1440m lag 約 **23.0h**

### IC / drift / live contract
- Global IC：**19/30**
- TW-IC：**25/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- drift primary window：**250**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**chop 92.8%**
- live predictor：
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**D**
  - allowed layers：**0**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=18**
  - exact live lane：**35 rows / win_rate 0.6286 / quality 0.3328**
  - `decision_quality_exact_live_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
  - `decision_quality_exact_live_lane_toxic_bucket`：**`CAUTION|structure_quality_caution|q15` rows=4 / win_rate 0.0000 / quality -0.3096**
  - `decision_quality_exact_live_lane_toxicity_applied`：**false**（current bucket 不是 toxic q15）
  - execution guardrail：**`decision_quality_below_trade_floor`**

### 模型 / shrinkage / support-aware ranking
- global recommended profile：**`core_only`**
- bull collapse-pocket / train selected：**`core_plus_macro`**
- leaderboard selected profile：**`core_only`**
- dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
- blocked candidate：**`core_plus_macro` → `under_minimum_exact_live_structure_bucket`**
- bull pocket artifact（當前 live bucket）
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35`**
  - exact rows：**18**
  - exact bucket gap to minimum：**32**
  - exact-bucket proxy rows：**67**
  - exact-lane proxy rows：**330**
  - supported neighbor rows：**84**
  - `blocker_state = exact_lane_proxy_fallback_only`
  - `exact_bucket_root_cause = exact_bucket_present_but_below_minimum`
  - `support_governance_route = exact_live_bucket_present_but_below_minimum`
  - `proxy_boundary_verdict = proxy_boundary_inconclusive`
  - `exact_lane_bucket_verdict = toxic_sub_bucket_identified`
  - `bucket_comparison_takeaway = prefer_same_bucket_proxy_over_cross_regime_spillover`

### Source blocker
- `fin_netflow` 仍是 **auth_missing**
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵

---

## 當前主目標

### 目標 A：把 q15 toxic pocket 從「可被 runtime 識別」推進到「跨 surface 定稿的治理規則」
本輪已確認：
- current q35 bucket：**18 rows / win_rate 1.0000 / quality 0.7064**；
- toxic q15 bucket：**4 rows / win_rate 0.0000 / quality -0.3096**；
- predictor contract 已知道：
  - 什麼 bucket 是 toxic；
  - 何時應該 block；
  - 何時不該誤傷 q35。

下一步主目標是：
- **把 q15 toxic pocket 的 runtime veto contract 和 bull governance / docs / summary 完全對齊**；
- 確保所有 surface 都說同一句話：
  - q15 = toxic，應 veto；
  - q35 = health 不錯，但 support 還不足；
  - exact lane = 不可再視為單一黑盒。

### 目標 B：把 `proxy_boundary_inconclusive` 收斂成正式 contract
本輪已確認：
- proxy 與 exact current q35 的表現依然接近；
- broader same-bucket 仍被 chop spillover 主導；
- exact rows 雖增加到 18，但仍未滿 50。

下一步主目標是：
- **把 proxy contract 正式寫成：proxy 可用於治理參考，但 exact support 未滿前不得作 deployment 放行依據。**
- 也就是說，下一輪應收斂「為何 blocked」的語義，而不是再收集更多同類敘述。

### 目標 C：維持 shrinkage winner 與 support-aware candidate 的雙軌語義
目前雙軌語義仍是：
- global shrinkage winner = **`core_only`**
- train support-aware fallback = **`core_plus_macro`**
- leaderboard visible winner = **`core_only`**
- runtime deployment = **blocked (`allowed_layers=0`)**

下一步主目標：
- probe / summary / docs 對下列欄位持續零漂移：
  - `selected_feature_profile`
  - `train_selected_profile`
  - `blocked_candidate_profiles[*].blocker_reason`
  - `support_blocker_state`
  - `support_governance_route`
  - `proxy_boundary_verdict`
  - `exact_lane_bucket_verdict`
  - `decision_quality_exact_live_lane_toxic_bucket`
  - `live_current_structure_bucket_rows`
  - `allowed_layers`

### 目標 D：維持 source auth blocker 與 bull pathology 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 bull q35 / q15 pocket 成功敘事

---

## 接下來要做

### 1. 把 proxy contract 定稿
要做：
- 針對 `proxy_boundary_inconclusive` 產出正式治理結論；
- 明確寫出：proxy 只可治理參考、不得視為 exact bucket 已支持；
- 讓 artifact / probe / summary / docs 同步採用同一句 contract。

### 2. 把 q15 veto candidate 對齊所有 bull governance surface
要做：
- 確保 fast heartbeat、bull artifact、live probe、文件都用同一個 toxic bucket 定義；
- 若未來 current bucket 落到 q15，必須能在所有 surface 同步顯示它已被 veto；
- 若 current bucket 仍是 q35，必須同輪同步顯示「blocked 的原因是 support，不是 toxic」。

### 3. 維持 runtime blocker 與 bull pocket pathology 同步治理
要做：
- 持續檢查：
  - `support_blocker_state`
  - `support_governance_route`
  - `exact_bucket_root_cause`
  - `proxy_boundary_verdict`
  - `exact_lane_bucket_verdict`
  - `decision_quality_exact_live_lane_toxic_bucket`
  - `current_live_structure_bucket_gap_to_minimum`
  - `allowed_layers`
- 若 q35 exact rows 仍 < 50，持續維持 `0 layers`

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
> 現在真正的瓶頸已收斂成 **q35 exact support 未滿 + q15 toxic sub-bucket 已知但尚未完成跨 surface contract 定稿 + proxy contract 尚未收斂**；不是模型容量問題，也不是還看不懂 bull lane 病灶。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **proxy contract 定稿 / q15 veto 跨 surface 對齊** 直接相關的 patch / run / verify。
2. `data/bull_4h_pocket_ablation.json.support_pathology_summary`、`data/live_predict_probe.json`、`data/leaderboard_feature_profile_probe.json`、`data/heartbeat_739_summary.json` 的 blocker 語義持續零漂移。
3. q35 exact bucket 若仍 < 50，runtime / docs / probe 都明確維持 blocker 語義。
4. `core_only` 與 `core_plus_macro` 的雙軌語義零漂移。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 把 `proxy_boundary_inconclusive` 收斂成正式 contract；
  2. 把 q15 toxic-sub-bucket veto 對齊到所有 bull governance surface；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下 proxy contract 定稿或 q15 veto 跨 surface 對齊的真 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`exact_lane_bucket_verdict`、`decision_quality_exact_live_lane_toxic_bucket`、`allowed_layers` 對 blocker 的敘述零漂移；
  3. 若 q35 exact rows 仍 < 50，所有路徑同輪同步維持 blocker 結論。

- **Fallback if fail:**
  - 若 proxy contract 仍無法完全定稿，下一輪至少要把 `inconclusive` 改寫成明確 fallback 語義；
  - 若 q35 exact rows 持續卡住，繼續維持 `allowed_layers=0`，不要因 current q35 短期漂亮而放寬；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 proxy / veto contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_739_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若 `current_live_structure_bucket = CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_rows < 50`、`support_blocker_state = exact_lane_proxy_fallback_only`、`support_governance_route = exact_live_bucket_present_but_below_minimum`、`proxy_boundary_verdict = proxy_boundary_inconclusive`、`decision_quality_exact_live_lane_bucket_verdict = toxic_sub_bucket_identified`、`decision_quality_exact_live_lane_toxic_bucket.bucket = CAUTION|structure_quality_caution|q15`、`allowed_layers = 0` 仍同時成立，下一輪不得再把「已接進 runtime」當成功；必須直接推進 **proxy contract 定稿 / veto 跨 surface 對齊 / blocker 語義收斂**。
