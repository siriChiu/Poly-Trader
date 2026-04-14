# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 14:40 UTC — Heartbeat #731（train artifact 已刷新；主瓶頸轉向 bull exact bucket 支持樣本與 live-path pathology）_

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
  - numbered summary：`data/heartbeat_731_summary.json`

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**。
- 最新 DB 狀態（#731）：
  - Raw / Features / Labels = **21413 / 12842 / 42933**
  - simulated_pyramid_win = **0.5752**
- label freshness 正常：
  - 240m lag 約 **3.3h**
  - 1440m lag 約 **23.1h**

### 模型 / shrinkage / support-aware training
- global feature ablation 仍指向：
  - global winner = **`core_only`**
- bull pocket artifacts 目前 machine-readable：
  - `bull_exact_live_lane_proxy_rows = 50`
  - `bull_live_exact_lane_bucket_proxy_rows = 38`
  - `bull_supported_neighbor_buckets_proxy_rows = 12`
  - `support_governance_route = exact_live_bucket_proxy_available`
- **本輪新完成**：train artifact 已正式刷新到新的 support-aware contract
  - `model/last_metrics.json.feature_profile = core_plus_macro`
  - `model/last_metrics.json.feature_profile_meta.support_cohort = bull_exact_live_lane_proxy`
  - `support_rows = 50`
  - `exact_live_bucket_rows = 0`
- **本輪新完成**：`model/train.py` 可直接重跑
  - `python model/train.py` 現在可直接執行，不再要求手動補 `PYTHONPATH`
  - 這讓 retrain / artifact refresh 成為真正可重跑的 heartbeat 動作，而不是隱含 shell 魔法

### Live guardrail / bull blocker
- live predictor 仍正確保守：
  - regime = **bull**
  - gate = **ALLOW**
  - entry quality = **D**
  - allowed layers = **0**
  - guardrail reason = `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade`
- `live_current_structure_bucket_rows` 仍是 **0**。
- 這代表 **train artifact refresh 已完成，但部署 blocker 仍在**。

### Source blocker
- `fin_netflow` 仍是 **auth_missing**。
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵。

---

## 當前主目標

### 目標 A：把 bull blocker 從「train artifact refresh」推進到「exact bucket 真支持樣本 / pathology root cause」
目前已完成的是：
- train artifact 不再停留在舊的 `bull_supported_neighbor_buckets_proxy`。
- retrain 入口也已補成可直接重跑。

下一步主目標不是再證明 train meta 已更新，而是：
- **確認 exact live bucket 為什麼仍是 0-support**；
- **確認 bull live path 的 narrowed pathology 是 support 不足、lane selection 問題，還是真正的壞 pocket**。

### 目標 B：維持 `core_only`（global winner）與 `core_plus_macro`（train support fallback）雙軌語義清楚
目前雙軌仍成立：
- global winner = **`core_only`**
- train support-aware fallback = **`core_plus_macro`**
- train support cohort = **`bull_exact_live_lane_proxy`**

下一步主目標：
- probe / metrics / docs 對下列欄位持續零漂移：
  - `selected_feature_profile`
  - `global_recommended_profile`
  - `train_selected_profile`
  - `train_support_cohort`
  - `support_governance_route`
  - `live_current_structure_bucket_rows`

### 目標 C：維持 bull live blocker 的 deployment discipline
- exact live bucket rows 仍是 **0**。
- 即使 proxy rows > 0，也**不代表 runtime 可放寬層數**。

下一步主目標：
- 讓治理與部署語義嚴格分離；
- 任何下一輪修補都必須明講：**治理可前進，部署仍 blocked，直到 exact bucket 有真支持**。

### 目標 D：維持 source auth blocker 與模型 blocker 分離治理
- `fin_netflow` 仍是 **auth_missing**。
- 這是外部 source blocker，不可混進 bull exact bucket / live-path pathology 成功敘事。

---

## 接下來要做

### 1. 直接做 bull exact bucket 支持樣本 / pathology drill-down
要做：
- 檢查 `ALLOW|base_allow|q65` 為何 exact rows 仍 0；
- 對比 exact live lane、exact-bucket proxy、same-regime narrowed lane 的 target / quality / 4H shift；
- 若仍無法補 exact bucket，至少留下更明確的 machine-readable root cause。

### 2. 維持 governance-route 與 deployment guardrail 同步
要做：
- 持續檢查：
  - `support_governance_route`
  - `bull_exact_live_lane_proxy_rows`
  - `bull_live_exact_bucket_proxy_rows`
  - `live_current_structure_bucket_rows`
- 若 exact bucket 仍 0，持續維持 `0 layers`。

### 3. 維持 dual-profile 與 train artifact 語義一致
要做：
- heartbeat summary / probe / docs 必須能 machine-read：
  - `selected_feature_profile`
  - `global_recommended_profile`
  - `train_selected_profile`
  - `train_support_cohort`
  - `dual_profile_state`
  - `support_governance_route`
- 下一輪不應再出現「probe 已是 exact proxy，train artifact 還是舊 neighbor proxy」的漂移。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 calibration 或 bull pocket 問題。

---

## 暫不優先

以下本輪後仍不排最前面：
- 放寬 bull live guardrail
- 把 proxy bucket 視為 exact bucket 已修好
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸已從「train artifact 尚未刷新」轉成「exact bucket 本身仍 0-support，且 bull live narrowed lane 仍有明顯 pathology」。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **bull exact bucket 真支持樣本或 live-path pathology root cause** 直接相關的 patch / run / verify。
2. `model/last_metrics.json` 必須持續維持新的 exact-proxy support cohort，不回退到舊 neighbor proxy。
3. bull exact live bucket 若仍 0-support，runtime / docs / probe 都明確維持 blocker 語義。
4. `core_only` 與 `core_plus_macro` 的雙軌語義零漂移。
5. `support_governance_route` 持續可 machine-read。
6. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 直接推進 bull exact live structure bucket 的 support / pathology 治理；
  2. 持續維持 bull exact bucket 0-support 時的 `0 layers` runtime discipline；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下 exact bucket / live-path pathology 的真 patch / artifact / verify，不能只重報 train meta 已刷新；
  2. `leaderboard_feature_profile_probe.json`、`live_predict_probe.json`、`bull_4h_pocket_ablation.json`、`model/last_metrics.json` 對 support governance 的敘述零漂移；
  3. 若 exact bucket rows 有變化，四條路徑能同輪同步更新結論。

- **Fallback if fail:**
  - 若 exact bucket 仍 0 support，維持 `0 layers`；
  - 若仍無法找到 exact bucket root cause，下一輪至少要留下更窄的 same-bucket / proxy-bucket / pathology artifact；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull blocker 契約再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_731_summary.json`。
  2. 再讀：
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `model/last_metrics.json`
  3. 若 `train_support_cohort` 仍是 `bull_exact_live_lane_proxy`、`support_governance_route` 仍是 `exact_live_bucket_proxy_available`、`live_current_structure_bucket_rows` 仍是 0、`allowed_layers` 仍是 0，下一輪不得再把「train artifact refresh」當主題；必須直接推進 **exact bucket support / live-path pathology**。