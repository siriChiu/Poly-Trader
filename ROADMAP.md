# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 15:53 UTC — Heartbeat #734（bull live bucket 從 q35 under-supported 轉回 q65 exact=0；治理重心改成 q65 absent exact bucket + neutral spillover，而不是繼續把「曾經出現少量 exact rows」當主題）_

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
  - numbered summary：`data/heartbeat_734_summary.json`

### 本輪新完成：leaderboard probe under-minimum exact-bucket governance
- `scripts/hb_leaderboard_candidate_probe.py` 已升級：
  - 當 exact live bucket **有 rows 但仍低於 minimum support** 時，不再誤標 `exact_live_bucket_supported`
  - 現在會明確輸出：
    - `support_governance_route=exact_live_bucket_present_but_below_minimum`
    - `minimum_support_rows`
    - `live_current_structure_bucket_gap_to_minimum`
    - `exact_bucket_root_cause`
    - `support_blocker_state`
- `tests/test_hb_leaderboard_candidate_probe.py` 已新增 under-minimum regression
- `ARCHITECTURE.md` 已同步 #734 contract

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_bull_4h_pocket_ablation.py tests/test_train_target_metrics.py -q` → **15 passed**
- `source venv/bin/activate && python scripts/hb_leaderboard_candidate_probe.py` → **通過**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 734` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#734）：
  - Raw / Features / Labels = **21416 / 12845 / 42942**
  - simulated_pyramid_win = **0.5754**
- label freshness 正常：
  - 240m lag 約 **3.2h**
  - 1440m lag 約 **23.1h**

### IC / drift / live contract
- Global IC：**18/30**
- TW-IC：**27/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- drift primary window：**250**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**chop 97.6%**
- live predictor：
  - regime：**bull**
  - gate：**ALLOW**
  - entry quality：**D**
  - allowed layers：**0**
  - exact live bucket：**`ALLOW|base_allow|q65` rows=0**
  - execution guardrail：**`decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade`**

### 模型 / shrinkage / support-aware training
- global recommended profile：**`core_only`**
- train selected profile：**`core_plus_macro`**
- leaderboard selected profile：**`core_only`**
- dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
- bull pocket artifact（當前 live bucket）
  - current live structure bucket：**`ALLOW|base_allow|q65`**
  - exact rows：**0**
  - exact-bucket proxy rows：**38**
  - exact-lane proxy rows：**50**
  - supported neighbors rows：**12**
  - `exact_bucket_root_cause = cross_regime_spillover_dominates_q65`
  - `support_governance_route = exact_live_bucket_proxy_available`

### Source blocker
- `fin_netflow` 仍是 **auth_missing**
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵

---

## 當前主目標

### 目標 A：把 bull live blocker 從「proxy 還能不能用」收斂成 q65 absent exact-bucket root cause
本輪已確認：
- live bull bucket 已不再是 q35 under-supported；
- 現在的主 blocker 是 **q65 exact bucket = 0**，且 broader q65 evidence 被 **neutral spillover** 主導。

下一步主目標是：
- **直接追 `ALLOW|base_allow|q65` exact bucket 為何歸零**；
- 明確判定它是 bucket threshold 問題，還是 broader lane 已不應再當 bull calibration 代理。

### 目標 B：把 bull ALLOW lane 的 same-lane / broader-lane 證據切乾淨
目前 evidence 一致指向：
- exact bull ALLOW lane：**14 rows / q85 only / quality +0.2412**
- broader ALLOW+D lane：**115 rows / quality -0.0575 / neutral spillover 87.8%**
- broader q65 pocket：**66 rows / quality -0.0380**

下一步主目標：
- 不再把 broader ALLOW lane average 當成 bull exact lane 代理；
- 直接做 q85 exact lane / q65 proxy / broader q65 的 4H 結構差異與 path quality 對照。

### 目標 C：維持 support-aware training 與 blocker-aware leaderboard 的雙軌語義
目前雙軌語義是：
- global shrinkage winner = **`core_only`**
- train support-aware fallback = **`core_plus_macro`**（因 exact-lane proxy 可用）
- leaderboard visible winner = **`core_only`**（因 exact bucket 仍 0）
- runtime deployment = **blocked (`allowed_layers=0`)**

下一步主目標：
- probe / metrics / docs 對下列欄位持續零漂移：
  - `selected_feature_profile`
  - `train_selected_profile`
  - `support_governance_route`
  - `exact_bucket_root_cause`
  - `live_current_structure_bucket_rows`
  - `allowed_layers`

### 目標 D：維持 source auth blocker 與模型 blocker 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 bull exact bucket / lane contract 成功敘事

---

## 接下來要做

### 1. 直接做 q65 absent exact bucket drill-down
要做：
- 比對 `ALLOW|base_allow|q65` exact bucket（0 rows）、same-lane `q85` 14 rows、exact-bucket proxy 38 rows、broader q65 66 rows；
- 檢查 q65 缺口是 bucket 門檻切太硬，還是 ALLOW lane calibration 已被 neutral spillover 汙染；
- 若 exact bucket 仍為 0，直接把 absent exact-bucket root cause 持久化成 machine-readable artifact。

### 2. 維持 runtime guardrail 與 ALLOW-lane pathology 同步治理
要做：
- 持續檢查：
  - `exact_bucket_root_cause`
  - `current_live_structure_bucket_rows`
  - `live_current_structure_bucket_gap_to_minimum`
  - `support_governance_route`
  - `allowed_layers`
  - `decision_quality_scope_diagnostics["regime_gate+entry_quality_label"]`
- 若 exact bucket 仍為 0，持續維持 `0 layers`

### 3. 維持 support-aware profile 與 blocker 語義一致
要做：
- heartbeat summary / probe / docs 必須能 machine-read：
  - `leaderboard_selected_profile`
  - `train_selected_profile`
  - `support_governance_route`
  - `exact_bucket_root_cause`
  - `live_current_structure_bucket_rows`
  - `allowed_layers`
- 下一輪不應再出現「train 可用 proxy = runtime 可部署」的語義漂移

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 calibration 或 bull pocket 問題

---

## 暫不優先

以下本輪後仍不排最前面：
- 放寬 live execution guardrail
- 重新把 retrain 當主題
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸已從「q35 有少量 exact rows」轉成 **q65 exact bucket 歸零 + broader q65 evidence 被 neutral spillover 汙染**；不是模型容量問題，也不是 artifacts 不足。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **q65 exact bucket absent / spillover-dominates** 直接相關的 patch / run / verify。
2. `data/bull_4h_pocket_ablation.json.support_pathology_summary`、`data/live_predict_probe.json`、`data/leaderboard_feature_profile_probe.json` 的 blocker 語義持續零漂移。
3. bull exact bucket 若仍為 0，runtime / docs / probe 都明確維持 blocker 語義。
4. `core_only` 與 `core_plus_macro` 的雙軌語義零漂移。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 直接推進 `ALLOW|base_allow|q65` exact bucket absent root cause；
  2. 釐清 q85 exact lane、q65 proxy、broader q65 之間到底是 bucket 門檻問題還是 neutral spillover 汙染；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下 q65 exact bucket 的真 patch / artifact / verify，不能只重報目前摘要；
  2. `support_pathology_summary.exact_bucket_root_cause`、`leaderboard_feature_profile_probe.support_governance_route`、`live_predict_probe.allowed_layers` 對 blocker 的敘述零漂移；
  3. 若 exact rows 仍為 0，三條路徑能同輪同步維持 blocker 結論。

- **Fallback if fail:**
  - 若 q65 exact rows 持續 0，維持 `0 layers`；
  - 若仍無法找到 root cause，下一輪至少要留下更窄的 q85 exact lane vs broader q65 spillover 對照 artifact；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull support / lane contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_734_summary.json`
  2. 再讀：
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/live_predict_probe.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若 `support_pathology_summary.current_live_structure_bucket` 仍是 `ALLOW|base_allow|q65`、`current_live_structure_bucket_rows = 0`、`exact_bucket_root_cause = cross_regime_spillover_dominates_q65`、`support_governance_route = exact_live_bucket_proxy_available`、`allowed_layers = 0`，下一輪不得再把「proxy 還在」當主題；必須直接推進 **q65 absent exact bucket / broader neutral spillover / lane contract**。