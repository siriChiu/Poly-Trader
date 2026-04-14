# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 19:42 UTC — Heartbeat #742（exact-supported bull governance 已從「support 是否足夠」推進到「train / leaderboard exact-supported profile 如何收斂」的新階段。本輪已把 train path 從 global fallback 拉回 exact-supported 分支，並把未收斂狀態正式命名為 `post_threshold_profile_governance_stalled`。）_

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
  - numbered summary：`data/heartbeat_742_summary.json`

### 本輪新完成：exact-supported training branch 正式接上
- `model/train.py` 已升級：
  - 當 `support_pathology_summary.exact_bucket_root_cause = exact_bucket_supported` 時，training 不再直接回退到 global `feature_group_ablation.recommended_profile`；
  - 會改走 **`bull_4h_pocket_ablation.exact_supported_profile`** 分支，優先嘗試：
    - `exact_live_bucket`
    - `bull_live_exact_lane_bucket_proxy`
    - `bull_all`
    - `bull_exact_live_lane_proxy`
- training registry 現在可直接消費 bull 4H ablation profile 名稱：
  - `core_plus_macro_plus_4h_structure_shift`
  - `core_plus_macro_plus_4h_trend`
  - `core_plus_macro_plus_4h_momentum`
  - `core_plus_macro_plus_all_4h`
- `scripts/hb_leaderboard_candidate_probe.py` 已升級：
  - exact-supported 但 train / leaderboard 尚未收斂時，現在會明確輸出：
    - `dual_profile_state = post_threshold_profile_governance_stalled`
- `ARCHITECTURE.md` 已同步 exact-supported training / probe governance contract。

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_train_target_metrics.py tests/test_hb_leaderboard_candidate_probe.py -q` → **13 passed**
- `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py tests/test_model_leaderboard.py -q` → **29 passed**
- `source venv/bin/activate && python model/train.py` → **通過**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 742` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#742）：
  - Raw / Features / Labels = **21426 / 12855 / 43031**
  - simulated_pyramid_win = **0.5766**
- label freshness 正常：
  - 240m lag 約 **3.2h**
  - 1440m lag 約 **23.0h**

### IC / drift / live contract
- Global IC：**19/30**
- TW-IC：**25/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- drift primary window：**100**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**bull 85.0%**
- live predictor：
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**D**
  - decision-quality label：**C**
  - allowed layers：**0**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=85**
  - `decision_quality_exact_live_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
  - `decision_quality_exact_live_lane_toxic_bucket`：**`CAUTION|structure_quality_caution|q15` rows=4 / win_rate=0.0**

### 模型 / shrinkage / support-aware ranking
- global recommended profile：**`core_only`**
- bull all cohort recommended profile：**`core_plus_macro_plus_4h_structure_shift`**
- train selected profile：**`core_plus_macro`**
  - source：**`bull_4h_pocket_ablation.exact_supported_profile`**
  - support cohort：**`bull_exact_live_lane_proxy`**
  - support rows：**377**
  - exact live bucket rows：**61**
- leaderboard selected profile：**`core_plus_macro_plus_4h_structure_shift`**
  - source：**`bull_4h_pocket_ablation.exact_supported_profile`**
  - support cohort：**`bull_all`**
  - support rows：**759**
  - exact live bucket rows：**85**
- dual profile state：**`post_threshold_profile_governance_stalled`**
- bull pocket artifact（當前 live bucket）
  - `blocker_state = exact_live_bucket_supported`
  - `exact_bucket_root_cause = exact_bucket_supported`
  - `support_governance_route = exact_live_bucket_supported`
  - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
  - `exact_lane_bucket_verdict = toxic_sub_bucket_identified`

### Source blocker
- `fin_netflow` 仍是 **auth_missing**
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵

---

## 當前主目標

### 目標 A：把 exact-supported 後的 train / leaderboard profile 真正收斂
本輪已完成：
- training 已不再直接回退到 global `core_only`；
- leaderboard / probe / summary 已能明確標記 exact-supported 後的 stalled governance。

下一步主目標：
- **直接找出為何 leaderboard 已能選 `core_plus_macro_plus_4h_structure_shift`，但 train 仍停在 `core_plus_macro`**；
- 讓 train / leaderboard 對 exact-supported bull lane 使用同一個 profile，或至少能用文件化門檻說清楚為什麼不能收斂。

### 目標 B：維持 q15 toxic pocket 與 q35 exact-supported 的雙重語義
目前已明確：
- q35：**exact support 已足夠**
- q15：**lane-internal toxic sub-bucket**
- runtime deployment：**仍保守（allowed_layers=0）**，原因是 CAUTION + D quality，不是 support 不足

下一步主目標：
- 在 profile 收斂時仍維持所有 surface 都明講：
  - q35 support 已到位；
  - q15 仍是 veto 候選；
  - blocked / hold 的原因來自 gate / quality，而不是 q35 support deficit。

### 目標 C：把 post-threshold governance 明確制度化
本輪已完成：
- `post_threshold_profile_governance_stalled` 已成為 machine-readable state；
- `bull_4h_pocket_ablation.exact_supported_profile` 已成為 training / leaderboard 可共同引用的 source label。

下一步主目標：
- 確保所有 exact-supported surface 都用這套治理語義；
- 不再回退成 `leaderboard_global_winner_vs_train_support_fallback` 或 `proxy_boundary_inconclusive` 這類 pre-threshold 文案。

### 目標 D：維持 source auth blocker 與 bull pathology 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 bull exact-supported profile 收斂敘事

---

## 接下來要做

### 1. 追 exact-supported train-frame parity
要做：
- 直接檢查 train frame / selected columns / ablation profile 可用欄位，找出 train 為何仍落在 `bull_exact_live_lane_proxy/core_plus_macro`；
- 若可行，讓 train path 真正切到 `core_plus_macro_plus_4h_structure_shift`；
- 若不可行，明確寫出缺哪一段 feature parity / frame availability / gating 邏輯。

### 2. 維持 exact-supported contract 零漂移
要做：
- 持續檢查 artifact / leaderboard probe / heartbeat summary / docs 的：
  - `support_blocker_state = exact_live_bucket_supported`
  - `support_governance_route = exact_live_bucket_supported`
  - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
  - `dual_profile_state = post_threshold_profile_governance_stalled`（若尚未收斂）
- 任何一條路徑回退成 pre-threshold blocker 文案都視為 regression。

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
- 不把它重包裝成 bull exact-supported 後的新問題。

---

## 暫不優先

以下本輪後仍不排最前面：
- 直接放寬 live execution guardrail
- 把 exact-supported 已達標解讀成可立即部署
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸已從「q35 support 還差幾 rows」轉成 **exact-supported 後的 train / leaderboard governance 收斂**；不是資料量不夠，也不是 proxy 還講不清楚。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **train / leaderboard exact-supported profile 收斂** 直接相關的真 patch / run / verify。
2. `data/bull_4h_pocket_ablation.json.support_pathology_summary`、`data/live_predict_probe.json`、`data/leaderboard_feature_profile_probe.json`、`data/heartbeat_742_summary.json` 的 exact-supported 語義持續零漂移。
3. 若 q35 exact bucket 仍 ≥50，所有 surface 都不得再把 support deficit 當 blocker。
4. 若 train / leaderboard 仍不一致，必須保留 `post_threshold_profile_governance_stalled`，直到 root cause 被 patch + verify。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 追 `post_threshold_profile_governance_stalled` 的 root cause，讓 exact-supported bull lane 的 train / leaderboard profile 收斂；
  2. 若 q35 rows 仍 ≥50，持續驗證 `exact_bucket_supported_proxy_not_required` 與 q15 toxic contract 在所有 surface 零漂移；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下至少一個與 **exact-supported train-frame parity / leaderboard convergence** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`exact_lane_bucket_verdict`、`dual_profile_state`、`allowed_layers` 對 bull lane 的敘述零漂移；
  3. 若 q35 exact rows 仍 ≥50，所有路徑同輪同步維持 exact-supported 結論；若 rows 再跌回 <50，必須同輪恢復 support blocker 文案。

- **Fallback if fail:**
  - 若 train / leaderboard 仍停在不同的 exact-supported profile，下一輪升級為 `exact_supported_train_frame_parity_blocker`；
  - 若 proxy contract 任一路徑回退成 `proxy_boundary_inconclusive`，視為 exact-supported governance regression；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 train/leaderboard 收斂 contract 再擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_742_summary.json`
  2. 再讀：
     - `model/last_metrics.json`
     - `data/leaderboard_feature_profile_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `data/live_predict_probe.json`
  3. 若 `current_live_structure_bucket = CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_rows >= 50`、`support_blocker_state = exact_live_bucket_supported`、`support_governance_route = exact_live_bucket_supported`、`proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`、`decision_quality_exact_live_lane_bucket_verdict = toxic_sub_bucket_identified`、`decision_quality_exact_live_lane_toxic_bucket.bucket = CAUTION|structure_quality_caution|q15`、`allowed_layers = 0` 仍同時成立，下一輪不得再把「support 達標」當成功；必須直接推進 **exact-supported train-frame parity / leaderboard convergence / q15 toxic pocket 保守治理**。
