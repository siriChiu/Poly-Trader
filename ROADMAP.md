# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 16:29 UTC — Heartbeat #735（live bull blocker 已切換到 `CAUTION|q35` under-minimum exact bucket；本輪新增 bucket-evidence comparison contract，並把 leaderboard 對 under-minimum exact bucket 的語義漂移修正成明確 blocker）_

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
  - numbered summary：`data/heartbeat_735_summary.json`

### 本輪新完成：bucket-evidence comparison + under-minimum exact-bucket blocker alignment
- `scripts/bull_4h_pocket_ablation.py` 已升級：
  - `support_pathology_summary` 現在不只輸出 gap / blocker_state；
  - 還會 machine-read：
    - `bucket_evidence_comparison.exact_live_lane`
    - `bucket_evidence_comparison.exact_bucket_proxy`
    - `bucket_evidence_comparison.broader_same_bucket`
    - `bucket_comparison_takeaway`
- `backtesting/model_leaderboard.py` 已升級：
  - 若 `0 < exact_live_bucket_rows < minimum_support_rows`，現在會標成 **`under_minimum_exact_live_structure_bucket`**；
  - support-aware candidate 不再因為「已出現少量 exact rows」就被誤當成可部署候選。
- `scripts/hb_parallel_runner.py` 已同步：
  - heartbeat summary 會持久化新的 bucket comparison 摘要，下一輪可直接承接。
- `ARCHITECTURE.md` 已同步 #735 contract。

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_parallel_runner.py tests/test_model_leaderboard.py tests/test_hb_leaderboard_candidate_probe.py -q` → **35 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 735` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#735）：
  - Raw / Features / Labels = **21418 / 12847 / 42946**
  - simulated_pyramid_win = **0.5754**
- label freshness 正常：
  - 240m lag 約 **3.4h**
  - 1440m lag 約 **23.1h**

### IC / drift / live contract
- Global IC：**18/30**
- TW-IC：**27/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- drift primary window：**250**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**chop 96.4%**
- live predictor：
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**D**
  - allowed layers：**0**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=9**
  - execution guardrail：**`decision_quality_below_trade_floor`**
  - exact live lane：**26 rows / win_rate 0.50 / quality 0.1985**

### 模型 / shrinkage / support-aware ranking
- global recommended profile：**`core_only`**
- bull collapse-pocket best：**`core_plus_macro`**
- train selected profile：**`core_plus_macro`**
- leaderboard selected profile：**`core_only`**
- dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
- blocked candidate：**`core_plus_macro` → `under_minimum_exact_live_structure_bucket`**
- bull pocket artifact（當前 live bucket）
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35`**
  - exact rows：**9**
  - exact bucket gap to minimum：**41**
  - exact-bucket proxy rows：**52**
  - exact-lane proxy rows：**315**
  - supported neighbor rows：**84**
  - `exact_bucket_root_cause = exact_bucket_present_but_below_minimum`
  - `bucket_comparison_takeaway = prefer_same_bucket_proxy_over_cross_regime_spillover`

### Source blocker
- `fin_netflow` 仍是 **auth_missing**
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵

---

## 當前主目標

### 目標 A：把 bull live blocker 收斂成 q35 under-minimum exact-bucket 根因，而不是再沿用舊 q65 敘事
本輪已確認：
- live bull path 已從 `ALLOW|q65 exact=0` 變成 **`CAUTION|q35 exact=9/50`**；
- 根因已切成 **`exact_bucket_present_but_below_minimum`**。

下一步主目標是：
- **直接追 `CAUTION|q35` exact bucket 9 → 50 的 support 累積與 bucket contract**；
- 不再把舊 q65 exact=0 當主題。

### 目標 B：把 exact / proxy / broader same-bucket 證據切乾淨
目前 evidence 一致指向：
- exact live lane：**26 rows / win_rate 0.50 / quality 0.1985**
- current exact bucket：**9 rows / 仍不足 minimum support**
- exact bucket proxy：**52 rows / win_rate 0.9423**
- broader same bucket：**10 rows / dominant regime=chop / win_rate 0.90 / quality 0.5732**

下一步主目標：
- 判定 proxy 52 rows 是否過寬；
- 判定 broader same-bucket 是否仍受 cross-regime spillover 汙染；
- 讓下一輪不必再手工比對 q35 exact / proxy / broader。

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
  - `bucket_comparison_takeaway`
  - `live_current_structure_bucket_rows`
  - `allowed_layers`

### 目標 D：維持 source auth blocker 與模型 blocker 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 bull q35 bucket 成功敘事

---

## 接下來要做

### 1. 直接做 q35 under-minimum exact bucket drill-down
要做：
- 比對 **exact 9 rows、exact live lane 26 rows、proxy 52 rows、broader same-bucket 10 rows**；
- 檢查 proxy cohort 是否把太多非 exact 結構混進來；
- 若 exact bucket 仍明顯不足，直接把 q35 under-minimum root cause 持久化成更細的 machine-readable artifact。

### 2. 維持 runtime blocker 與 bull pocket pathology 同步治理
要做：
- 持續檢查：
  - `exact_bucket_root_cause`
  - `current_live_structure_bucket_gap_to_minimum`
  - `bucket_comparison_takeaway`
  - `blocked_candidate_profiles[*].blocker_reason`
  - `allowed_layers`
- 若 exact bucket 仍 < 50，持續維持 `0 layers`

### 3. 維持 support-aware profile 與 blocker-aware leaderboard 一致
要做：
- heartbeat summary / probe / docs 必須能 machine-read：
  - `leaderboard_selected_profile`
  - `train_selected_profile`
  - `blocked_candidate_profiles`
  - `bucket_evidence_comparison`
  - `bucket_comparison_takeaway`
  - `allowed_layers`
- 下一輪不應再出現「exact bucket 有少量 rows = support-aware candidate 可上榜」的語義漂移

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
> 現在真正的瓶頸已從「q65 exact=0」切換成 **q35 exact bucket 已出現但仍 under-minimum + bull-only D pocket pathology**；不是模型容量問題，也不是 artifact 缺失問題。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **q35 under-minimum exact bucket** 直接相關的 patch / run / verify。
2. `data/bull_4h_pocket_ablation.json.support_pathology_summary`、`data/leaderboard_feature_profile_probe.json`、`data/live_predict_probe.json` 的 blocker 語義持續零漂移。
3. bull exact bucket 若仍 < 50，runtime / docs / probe 都明確維持 blocker 語義。
4. `core_only` 與 `core_plus_macro` 的雙軌語義零漂移。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 直接推進 `CAUTION|structure_quality_caution|q35` exact bucket 9 → 50 的 support 根因；
  2. 釐清 exact 9 / exact lane 26 / proxy 52 / broader same-bucket 10 之間到底是 proxy cohort 過寬，還是 bull D pocket 本身不適合部署；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下 q35 under-minimum exact bucket 的真 patch / artifact / verify，不能只重報目前摘要；
  2. `bucket_comparison_takeaway`、`blocked_candidate_profiles[*].blocker_reason`、`allowed_layers` 對 blocker 的敘述零漂移；
  3. 若 exact rows 仍 < 50，三條路徑能同輪同步維持 blocker 結論。

- **Fallback if fail:**
  - 若 q35 exact rows 持續卡住，維持 `0 layers`；
  - 若仍無法判定 proxy 邊界，下一輪至少要留下更窄的 exact 9 vs proxy 52 feature / gate-path 對照 artifact；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull support / bucket contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_735_summary.json`
  2. 再讀：
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/live_predict_probe.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若 `support_pathology_summary.current_live_structure_bucket` 仍是 `CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_gap_to_minimum > 0`、`bucket_comparison_takeaway = prefer_same_bucket_proxy_over_cross_regime_spillover`、`blocked_candidate_profiles[*].blocker_reason = under_minimum_exact_live_structure_bucket`、`allowed_layers = 0`，下一輪不得再把「exact rows 已出現」當成功；必須直接推進 **q35 under-minimum exact bucket / proxy cohort 邊界 / bull-only pathology**。
