# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 17:49 UTC — Heartbeat #738（bull q35 blocker 已不再是「不知道哪裡壞」：現在已 machine-read 到 exact lane 的主 toxic pocket 是 `CAUTION|structure_quality_caution|q15`；下一步是把它升級成可執行 veto / rejection rule，而不是繼續把整條 lane 當黑盒）_

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
  - numbered summary：`data/heartbeat_738_summary.json`

### 本輪新完成：bull exact lane 子 bucket machine-readable diagnostics
- `scripts/bull_4h_pocket_ablation.py` 已升級：
  - 新增 `exact_lane_bucket_diagnostics`，固定輸出：
    - `buckets`
    - `toxic_bucket`
    - `verdict`
    - `reason`
  - `support_pathology_summary` 已同步帶出：
    - `exact_lane_bucket_verdict`
    - `exact_lane_bucket_reason`
    - `exact_lane_toxic_bucket`
  - markdown artifact 新增 `Exact lane sub-bucket diagnostics` 區塊。
- `scripts/hb_parallel_runner.py` 已同步：
  - heartbeat summary 直接帶出 exact-lane toxic 子 bucket diagnostics。
- regression tests 已補：
  - `tests/test_bull_4h_pocket_ablation.py`
  - `tests/test_hb_parallel_runner.py`
- `ARCHITECTURE.md` 已同步 #738 contract。

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_parallel_runner.py -q` → **15 passed**
- `source venv/bin/activate && python scripts/bull_4h_pocket_ablation.py` → **通過**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 738` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#738）：
  - Raw / Features / Labels = **21421 / 12850 / 42954**
  - simulated_pyramid_win = **0.5755**
- label freshness 正常：
  - 240m lag 約 **3.2h**
  - 1440m lag 約 **23.2h**

### IC / drift / live contract
- Global IC：**19/30**
- TW-IC：**27/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- drift primary window：**250**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**chop 94.8%**
- live predictor：
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**D**
  - allowed layers：**0**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=13**
  - execution guardrail：**`decision_quality_below_trade_floor`**
  - exact live lane：**30 rows / win_rate 0.5667 / quality 0.2694**
  - current exact bucket：**13 rows / win_rate 1.0000 / quality 0.7036**
  - broader same bucket：**15 rows / win_rate 0.9333 / quality 0.6231 / dominant regime chop 96.6%**
  - historical exact-bucket proxy：**56 rows / win_rate 0.9464**
  - `proxy_boundary_verdict`：**`proxy_boundary_inconclusive`**
  - `exact_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
  - `exact_lane_toxic_bucket`：**`CAUTION|structure_quality_caution|q15` rows=4 / win_rate 0.0000**

### 模型 / shrinkage / support-aware ranking
- global recommended profile：**`core_only`**
- bull collapse-pocket best：**`core_plus_macro`**
- train selected profile：**`core_plus_macro`**
- leaderboard selected profile：**`core_only`**
- dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
- blocked candidate：**`core_plus_macro` → `under_minimum_exact_live_structure_bucket`**
- bull pocket artifact（當前 live bucket）
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35`**
  - exact rows：**13**
  - exact bucket gap to minimum：**37**
  - exact-bucket proxy rows：**56**
  - exact-lane proxy rows：**319**
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

### 目標 A：把 q15 toxic pocket 從「已找出」推進到「可執行 veto / rejection rule」
本輪已確認：
- current q35 bucket：**13 rows / win_rate 1.0000 / quality 0.7036**；
- exact live lane：**30 rows / win_rate 0.5667 / quality 0.2694**；
- 最差子 bucket：**`CAUTION|structure_quality_caution|q15` 4 rows / win_rate 0.0000**。

下一步主目標是：
- **把 q15 toxic pocket 升級成 machine-readable veto / rejection rule 候選**；
- 驗證它只擋 q15，不誤傷 q35 current bucket；
- 若成立，就把 bull exact lane 的 blocker 從「黑盒 lane 不好」收斂成「特定子 bucket 不可部署」。

### 目標 B：把 `proxy_boundary_inconclusive` 收斂成定稿，而不是反覆重講
本輪已確認：
- proxy vs current q35 的差距不大（win_rate Δ **-0.0536**）；
- broader same-bucket 仍有 cross-regime spillover（dominant regime **chop 96.6%**）；
- 因此 `proxy_boundary_verdict` 仍是 **`proxy_boundary_inconclusive`**。

下一步主目標是：
- **在 q15 veto 成立與否的前提下重新判讀 proxy contract**；
- 若 q15 才是主要病灶，就把 proxy 結論定稿為：
  - proxy 可保留作治理參考；
  - 但 exact support 未滿前，runtime 仍 blocked。

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
  - `exact_lane_bucket_verdict`
  - `live_current_structure_bucket_rows`
  - `allowed_layers`

### 目標 D：維持 source auth blocker 與 bull pathology 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 bull q35 / q15 pocket 成功敘事

---

## 接下來要做

### 1. 把 q15 toxic pocket 變成可執行規則
要做：
- 根據 `exact_lane_bucket_diagnostics`，為 `CAUTION|structure_quality_caution|q15` 建立 veto / rejection 規則；
- 驗證該規則不會誤傷 `CAUTION|structure_quality_caution|q35`；
- 若規則生效，將 blocker 敘事從「整條 lane 爛」改成「特定子 bucket 不可部署」。

### 2. 在 q15 已拆清後，正式定稿 proxy contract
要做：
- 檢查 q15 veto 生效後，proxy 是否仍需要縮窄；
- 若不需要，再把 `proxy_boundary_inconclusive` 收斂成正式結論：
  - proxy 可保留作治理參考；
  - 但 q35 exact rows < 50 前仍不得部署。

### 3. 維持 runtime blocker 與 bull pocket pathology 同步治理
要做：
- 持續檢查：
  - `support_blocker_state`
  - `support_governance_route`
  - `exact_bucket_root_cause`
  - `proxy_boundary_verdict`
  - `exact_lane_bucket_verdict`
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
> 現在真正的瓶頸已收斂成 **q35 exact bucket support 不足 + q15 toxic sub-bucket + proxy contract 尚未定稿**；不是 blocker 語義問題，也不是模型容量問題。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **q15 toxic pocket veto / proxy boundary 定稿** 直接相關的 patch / run / verify。
2. `data/bull_4h_pocket_ablation.json.support_pathology_summary`、`data/leaderboard_feature_profile_probe.json`、`data/live_predict_probe.json` 的 blocker 語義持續零漂移。
3. q35 exact bucket 若仍 < 50，runtime / docs / probe 都明確維持 blocker 語義。
4. `core_only` 與 `core_plus_macro` 的雙軌語義零漂移。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 把 `CAUTION|structure_quality_caution|q15` toxic pocket 升級成 machine-readable veto / rejection rule 候選；
  2. 在 q15 問題拆清後，將 `proxy_boundary_inconclusive` 收斂成正式 contract；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下 q15 veto 或 proxy 定稿的真 patch / artifact / verify，不能只重報目前摘要；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`exact_lane_bucket_verdict`、`allowed_layers` 對 blocker 的敘述零漂移；
  3. 若 q35 exact rows 仍 < 50，所有路徑同輪同步維持 blocker 結論。

- **Fallback if fail:**
  - 若 q15 veto 還不能穩定區分壞 pocket，下一輪至少把 `q15 / q35` 差異轉成更窄 proxy contract；
  - 若 q35 exact rows 持續卡住，繼續維持 `allowed_layers=0`，不要因 current q35 短期漂亮而放寬；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull veto / proxy contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_738_summary.json`
  2. 再讀：
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/live_predict_probe.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若 `support_pathology_summary.current_live_structure_bucket` 仍是 `CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_gap_to_minimum > 0`、`support_blocker_state = exact_lane_proxy_fallback_only`、`support_governance_route = exact_live_bucket_present_but_below_minimum`、`proxy_boundary_verdict = proxy_boundary_inconclusive`、`exact_lane_bucket_verdict = toxic_sub_bucket_identified`、`exact_lane_toxic_bucket.bucket = CAUTION|structure_quality_caution|q15`、`allowed_layers = 0`，下一輪不得再把「已找到 toxic pocket」當成功；必須直接推進 **q15 veto / proxy 定稿 / runtime guardrail 對齊**。
