# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 17:22 UTC — Heartbeat #737（bull q35 blocker 已有 machine-readable proxy-boundary diagnostics；現在主問題是把 `proxy_boundary_inconclusive` 收斂成可執行 contract，而不是再重講 blocker 語義）_

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
  - numbered summary：`data/heartbeat_737_summary.json`

### 本輪新完成：q35 exact/proxy/broader 邊界 machine-readable diagnostics
- `scripts/bull_4h_pocket_ablation.py` 已升級：
  - 新增 `proxy_boundary_diagnostics`，固定輸出：
    - `recent_exact_current_bucket`
    - `recent_exact_live_lane`
    - `historical_exact_bucket_proxy`
    - `recent_broader_same_bucket`
    - `proxy_vs_current_live_bucket`
    - `exact_live_lane_vs_current_live_bucket`
    - `broader_same_bucket_vs_current_live_bucket`
    - `proxy_boundary_verdict / proxy_boundary_reason`
  - 這讓 heartbeat 能直接 machine-read：「proxy 是過寬，還是其實跟 exact bucket 接近但只是 support 還不足」。
- `scripts/hb_parallel_runner.py` 已同步：
  - heartbeat summary 現在直接帶出 `proxy_boundary_verdict / reason / diagnostics`。
- regression tests 已補：
  - `tests/test_bull_4h_pocket_ablation.py`
  - `tests/test_hb_parallel_runner.py`
- `ARCHITECTURE.md` 已同步 #737 contract。

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_parallel_runner.py tests/test_hb_leaderboard_candidate_probe.py -q` → **17 passed**
- `source venv/bin/activate && python scripts/bull_4h_pocket_ablation.py` → **通過**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 737` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#737）：
  - Raw / Features / Labels = **21420 / 12849 / 42951**
  - simulated_pyramid_win = **0.5754**
- label freshness 正常：
  - 240m lag 約 **3.2h**
  - 1440m lag 約 **23.4h**

### IC / drift / live contract
- Global IC：**19/30**
- TW-IC：**27/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- drift primary window：**250**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**chop 95.6%**
- live predictor：
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**D**
  - allowed layers：**0**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=11**
  - execution guardrail：**`decision_quality_below_trade_floor`**
  - exact live lane：**28 rows / win_rate 0.5357 / quality 0.2363**
  - current exact bucket：**11 rows / win_rate 1.0000 / quality 0.6983**
  - broader same bucket：**13 rows / win_rate 0.9231 / quality 0.6062**
  - historical exact-bucket proxy：**54 rows / win_rate 0.9444**
  - `proxy_boundary_verdict`：**`proxy_boundary_inconclusive`**
  - `bucket_comparison_takeaway`：**`prefer_same_bucket_proxy_over_cross_regime_spillover`**

### 模型 / shrinkage / support-aware ranking
- global recommended profile：**`core_only`**
- bull collapse-pocket best：**`core_plus_macro`**
- train selected profile：**`core_plus_macro`**
- leaderboard selected profile：**`core_only`**
- dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
- blocked candidate：**`core_plus_macro` → `under_minimum_exact_live_structure_bucket`**
- bull pocket artifact（當前 live bucket）
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35`**
  - exact rows：**11**
  - exact bucket gap to minimum：**39**
  - exact-bucket proxy rows：**54**
  - exact-lane proxy rows：**317**
  - supported neighbor rows：**84**
  - `blocker_state = exact_lane_proxy_fallback_only`
  - `exact_bucket_root_cause = exact_bucket_present_but_below_minimum`
  - `support_governance_route = exact_live_bucket_present_but_below_minimum`
  - `proxy_boundary_verdict = proxy_boundary_inconclusive`
  - `bucket_comparison_takeaway = prefer_same_bucket_proxy_over_cross_regime_spillover`

### Source blocker
- `fin_netflow` 仍是 **auth_missing**
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵

---

## 當前主目標

### 目標 A：把 q35 blocker 從「邊界可讀」推進到「可執行 proxy contract」
本輪已確認：
- q35 live bucket 仍是 **under-minimum support（11 / 50）**；
- `proxy_boundary_diagnostics` 已落地，下一步不該再停在人工解讀。

下一步主目標是：
- **把 `proxy_boundary_inconclusive` 收斂成明確 contract**；
- 要嘛縮窄 proxy cohort；
- 要嘛正式宣告「proxy 可保留，但 exact support 未滿前仍不得部署」。

### 目標 B：把 bull `CAUTION|D` exact lane 的 toxic 子 bucket 切出來
目前 evidence 一致指向：
- current q35 bucket：**11 rows / win_rate 1.0000 / quality 0.6983**
- exact live lane：**28 rows / win_rate 0.5357 / quality 0.2363**
- 這代表拖累 bull exact lane 的，不是只看 q35 一個 bucket 就能解釋。

下一步主目標：
- 直接拆解 **q35 / q15 / base_caution_q15 / base_caution_q85**；
- 找出真正 toxic 的 lane-internal bucket；
- 若證據足夠，升級成 machine-readable veto / rejection rule。

### 目標 C：維持 shrinkage winner 與 support-aware candidate 的雙軌語義
目前雙軌語義是：
- global shrinkage winner = **`core_only`**
- train support-aware fallback = **`core_plus_macro`**
- leaderboard visible winner = **`core_only`**
- blocked support-aware candidate = **`under_minimum_exact_live_structure_bucket`**
- runtime deployment = **blocked (`allowed_layers=0`)**

下一步主目標：
- probe / summary / docs 對下列欄位持續零漂移：
  - `selected_feature_profile`
  - `train_selected_profile`
  - `blocked_candidate_profiles[*].blocker_reason`
  - `support_blocker_state`
  - `support_governance_route`
  - `proxy_boundary_verdict`
  - `live_current_structure_bucket_rows`
  - `allowed_layers`

### 目標 D：維持 source auth blocker 與模型 blocker 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 bull q35 bucket 成功敘事

---

## 接下來要做

### 1. 直接把 `proxy_boundary_inconclusive` 變成可執行規則
要做：
- 比對 `proxy_vs_current_live_bucket.feature_mean_deltas` 與 `broader_same_bucket_vs_current_live_bucket.feature_mean_deltas`；
- 判定 `feat_4h_bias200 / feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b` 是否足以形成更窄 proxy 條件；
- 若差異不夠大，正式把 verdict 固定成「proxy 可保留、但 support 未滿仍 blocked」。

### 2. 切開 bull exact lane 內部子 bucket
要做：
- 對 **q35 / q15 / base_caution_q15 / base_caution_q85** 做 gate-path / target / 4H feature 對照；
- 找出真正拉低 bull `CAUTION|D` lane 的子 bucket；
- 若 toxic 子 bucket 穩定存在，升級為 lane-internal veto / rejection rule。

### 3. 維持 runtime blocker 與 bull pocket pathology 同步治理
要做：
- 持續檢查：
  - `support_blocker_state`
  - `support_governance_route`
  - `exact_bucket_root_cause`
  - `proxy_boundary_verdict`
  - `current_live_structure_bucket_gap_to_minimum`
  - `allowed_layers`
- 若 exact bucket 仍 < 50，持續維持 `0 layers`

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 q35 bucket 問題

---

## 暫不優先

以下本輪後仍不排最前面：
- 放寬 live execution guardrail
- 重新把 retrain 當主題
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸已收斂成 **q35 exact bucket support 不足 + proxy boundary 尚未收斂 + bull exact lane 內部 toxic 子 bucket**；不是 blocker 語義問題，也不是模型容量問題。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **proxy_boundary_inconclusive / bull exact-lane 子 bucket** 直接相關的 patch / run / verify。
2. `data/bull_4h_pocket_ablation.json.support_pathology_summary`、`data/leaderboard_feature_profile_probe.json`、`data/live_predict_probe.json` 的 blocker 語義持續零漂移。
3. bull exact bucket 若仍 < 50，runtime / docs / probe 都明確維持 blocker 語義。
4. `core_only` 與 `core_plus_macro` 的雙軌語義零漂移。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 把 `proxy_boundary_inconclusive` 收斂成明確決策：縮窄 proxy 或確認 proxy 可保留但仍 blocked；
  2. 拆解 exact lane 28 rows 的 q35 / q15 / base_caution_q15 / base_caution_q85，找出真正 toxic 子 bucket；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下 q35 proxy 收斂或 exact-lane toxic 子 bucket 的真 patch / artifact / verify，不能只重報目前摘要；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`allowed_layers` 對 blocker 的敘述零漂移；
  3. 若 exact rows 仍 < 50，所有路徑同輪同步維持 blocker 結論。

- **Fallback if fail:**
  - 若 q35 exact rows 持續卡住且 verdict 仍 inconclusive，下一輪直接升級成更窄 proxy contract；
  - 若 exact lane toxic 子 bucket 仍未切清，至少要留下 machine-readable 子 bucket 對照 artifact；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull support / proxy contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_737_summary.json`
  2. 再讀：
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/live_predict_probe.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若 `support_pathology_summary.current_live_structure_bucket` 仍是 `CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_gap_to_minimum > 0`、`support_blocker_state = exact_lane_proxy_fallback_only`、`support_governance_route = exact_live_bucket_present_but_below_minimum`、`proxy_boundary_verdict = proxy_boundary_inconclusive`、`allowed_layers = 0`，下一輪不得再把「邊界已可讀」當成功；必須直接推進 **proxy 收斂規則 / exact-lane toxic 子 bucket / bull-only pathology**。
