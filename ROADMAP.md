# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 14:10 UTC — Heartbeat #730（bull exact bucket 治理路徑已顯式化，下一步轉向訓練工件重刷）_

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
  - numbered summary：`data/heartbeat_730_summary.json`

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**。
- 最新 DB 狀態（#730）：
  - Raw / Features / Labels = **21412 / 12841 / 42921**
  - simulated_pyramid_win = **0.5750**
- label freshness 正常：
  - 240m lag 約 **3.3h**
  - 1440m lag 約 **23.0h**

### 模型 / shrinkage / bull blocker governance
- global feature ablation 仍指向：
  - global winner = **`core_only`**
- bull pocket artifacts 目前 machine-readable：
  - `bull_exact_live_lane_proxy_rows = 50`
  - `bull_live_exact_lane_bucket_proxy_rows = 38`
  - `bull_supported_neighbor_buckets_proxy_rows = 12`
- **本輪新完成**：bull support governance route 已正式顯式化
  - `scripts/hb_leaderboard_candidate_probe.py` 現在輸出：
    - `support_governance_route`
    - `bull_exact_live_lane_proxy_profile/rows`
    - `bull_live_exact_bucket_proxy_profile/rows`
  - current state（#730）為：
    - `support_governance_route = exact_live_bucket_proxy_available`
    - leaderboard selected profile = **`core_only`**
    - blocked candidate = **`core_plus_macro` → unsupported_exact_live_structure_bucket`**
- **本輪新完成**：`model/train.py::select_feature_profile()` 現在優先選擇
  - `bull_live_exact_lane_bucket_proxy`
  - `bull_exact_live_lane_proxy`
  - 再退回 `bull_supported_neighbor_buckets_proxy`
  - 最後才是 `bull_collapse_q35`

### Live guardrail / bull blocker
- live predictor 仍正確保守：
  - regime = **bull**
  - gate = **ALLOW**
  - entry quality = **D**
  - allowed layers = **0**
  - guardrail reason = `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade`
- `live_current_structure_bucket_rows` 仍是 **0**。
- 這代表 exact bucket 仍未解鎖，**proxy rows 只能作治理，不是部署授權**。

### Source blocker
- `fin_netflow` 仍是 **auth_missing**。
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵。

---

## 當前主目標

### 目標 A：把 bull exact bucket 治理從「知道 blocker」推進到「刷新訓練工件」
目前已完成的是：
- 已 machine-read 目前可用治理路徑不是空白，而是 **exact live bucket proxy available**。
- 已在訓練程式中把 support-aware selection 順序改成先 exact proxy、後 broader cohort。

下一步主目標不是再重報 `0 support`，而是：
- **讓訓練工件 (`model/last_metrics.json`) 真正反映新順序**；
- 若 train meta 仍停在舊的 `bull_supported_neighbor_buckets_proxy`，就不算完成。

### 目標 B：維持 `core_only`（global winner）與 `core_plus_macro`（train fallback）雙軌語義清楚
目前雙軌仍成立：
- global winner = **`core_only`**
- train fallback = **`core_plus_macro`**

但本輪新增一層治理語義：
- **train fallback 應優先依附 exact proxy cohort，而不是先回退到 broader cohort**。

下一步主目標：
- probe / metrics / docs 對 support cohort 的敘述全部一致；
- 不允許 probe 已說 `exact_live_bucket_proxy_available`，但 train meta 還停在舊 neighbor proxy。

### 目標 C：維持 bull live blocker 的 deployment discipline
- exact live bucket rows 仍是 **0**。
- 即使 proxy rows > 0，也**不代表 runtime 可放寬層數**。

下一步主目標：
- 讓治理與部署語義嚴格分離；
- 任何 retrain / probe / docs 更新都必須明講：**治理可前進，部署仍 blocked**。

### 目標 D：維持 source auth blocker 與模型 blocker 分離治理
- `fin_netflow` 仍是 **auth_missing**。
- 這是外部 source blocker，不可混進 bull exact bucket 支持樣本治理成功敘事。

---

## 接下來要做

### 1. 刷新 train artifact，讓 support-aware 順序真正落到工件
要做：
- 重新跑能寫回 `model/last_metrics.json` 的 train / retrain 路徑；
- 驗證 `feature_profile_meta.support_cohort` 是否從舊的 `bull_supported_neighbor_buckets_proxy` 切到新的 exact proxy；
- 若沒有切換，留下 blocker 與原因。

### 2. 維持 governance-route 與 deployment guardrail 同步
要做：
- 持續檢查：
  - `support_governance_route`
  - `bull_exact_live_lane_proxy_rows`
  - `bull_live_exact_bucket_proxy_rows`
  - `live_current_structure_bucket_rows`
- 若 exact bucket 仍 0，持續維持 `0 layers`。

### 3. 維持 dual-profile 語義一致
要做：
- heartbeat summary / probe / docs 必須能 machine-read：
  - `selected_feature_profile`
  - `global_recommended_profile`
  - `train_selected_profile`
  - `train_support_cohort`
  - `dual_profile_state`
  - `support_governance_route`

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
> 現在真正的瓶頸已從「治理路徑不可見」轉成「訓練工件尚未重刷到新的治理順序」，而 exact bucket 本身仍是 0-support。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個**可重寫 train artifact** 的 run / patch / verify。
2. `model/last_metrics.json` 的 `feature_profile_meta.support_cohort` 必須與新的 exact proxy 治理順序一致，不能再停留在舊 neighbor proxy。
3. bull exact live bucket 若仍 0-support，runtime / docs / probe 都明確維持 blocker 語義。
4. `core_only` 與 `core_plus_macro` 的雙軌語義零漂移。
5. `support_governance_route` 持續可 machine-read，不回退成只有 blocker 沒有治理路徑。
6. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 刷新 `model/last_metrics.json` 與 train meta，使其正式採用新的 exact-proxy 治理順序；
  2. 持續維持 bull exact bucket 0-support 時的 `0 layers` runtime discipline；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下 train artifact 重刷的真 run / verify，不能只停在 probe 已經可見 route；
  2. `leaderboard_feature_profile_probe.json`、`live_predict_probe.json`、`bull_4h_pocket_ablation.json`、`model/last_metrics.json` 對 support governance 的敘述零漂移；
  3. 若 exact bucket rows 有變化，四條路徑能同輪同步更新結論。

- **Fallback if fail:**
  - 若 exact bucket 仍 0 support，維持 `0 layers`；
  - 若 train artifact 仍未刷新，下一輪至少要留下可重跑 retrain contract / command / blocker；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 support-governance contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_730_summary.json`。
  2. 再讀：
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `model/last_metrics.json`
  3. 若 `support_governance_route`、`bull_exact_live_lane_proxy_rows`、`bull_live_exact_bucket_proxy_rows`、`live_current_structure_bucket_rows` 四項大致不變，但 train meta 仍未刷新，下一輪不得只重跑 fast heartbeat；必須直接推進 **訓練工件重刷 / support-aware retrain 驗證**。