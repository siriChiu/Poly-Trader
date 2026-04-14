# ISSUES.md — Current State Only

_最後更新：2026-04-14 14:40 UTC — Heartbeat #731（train artifact 已刷新到 exact-proxy cohort，live exact bucket 仍 0-support）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#730）要求本輪處理
- **Next focus**：
  1. 刷新 `model/last_metrics.json` 與 train meta，使其正式採用新的 exact-proxy 治理順序；
  2. bull exact bucket 仍 0-support 時，runtime 必須維持 `0 layers`；
  3. 持續把 `fin_netflow` 當外部 source blocker 管理。
- **Success gate**：
  1. 本輪必須留下至少一個能重寫 train artifact 的 run / patch / verify；
  2. probe / metrics / docs 對 bull blocker 治理語義零漂移；
  3. 若 exact bucket 仍 0，不能把 proxy rows 包裝成可部署證據。
- **Fallback if fail**：
  - 若 train artifact 仍未刷新，至少留下可重跑 retrain contract / command / blocker；
  - 若 exact bucket rows 改變，要同步更新 probe / docs；
  - `fin_netflow` 未補 auth 前持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - 已直接重訓並刷新 `model/last_metrics.json`；`feature_profile_meta.support_cohort` 已從舊的 `bull_supported_neighbor_buckets_proxy` 切到 **`bull_exact_live_lane_proxy`**。
  - 已修補 `model/train.py` 入口可重跑性：現在可直接 `python model/train.py`，不再需要手動補 `PYTHONPATH`。
  - 已再次驗證 `leaderboard_feature_profile_probe.json` / `live_predict_probe.json` / `bull_4h_pocket_ablation.json` 與 train artifact 語義一致。
- **仍未解**：
  - live exact structure bucket 仍為 **0 rows**，runtime 仍必須 **`allowed_layers=0`**。
  - bull live 決策品質路徑仍被 4H 結構 pocket pathology 壓制。
  - `fin_netflow` 仍是 **auth_missing**。
- **本輪明確不做**：
  - 不放寬 bull live guardrail。
  - 不把 proxy cohort 誤寫成 exact bucket 已修好。
  - 不把 `fin_netflow` auth blocker 誤報成 local calibration 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `model/train.py`
    - 新增 repo-root `sys.path` bootstrap，讓 `python model/train.py` 可直接執行。
    - 目的：把「訓練工件重刷」從依賴 shell 前置條件的脆弱流程，修成 heartbeat / 人工都可直接重跑的訓練入口。
- **Artifacts（已刷新）**
  - `model/last_metrics.json`
    - `feature_profile = core_plus_macro`
    - `feature_profile_meta.support_cohort = bull_exact_live_lane_proxy`
    - `support_rows = 50`
    - `exact_live_bucket_rows = 0`
    - `trained_at = 2026-04-14T14:37:09.057137`
  - `data/leaderboard_feature_profile_probe.json`
    - `support_governance_route = exact_live_bucket_proxy_available`
    - `train_support_cohort = bull_exact_live_lane_proxy`
    - dual-profile state 仍為 `leaderboard_global_winner_vs_train_support_fallback`
  - `data/heartbeat_731_summary.json`
    - fast heartbeat 已刷新 counts / IC / drift / probe / ablation / blocker 狀態
- **驗證（已通過）**
  - `source venv/bin/activate && python model/train.py` → **通過**（Train=63.1%, CV=73.5%）
  - `source venv/bin/activate && python -m pytest tests/test_train_target_metrics.py tests/test_hb_leaderboard_candidate_probe.py -q` → **11 passed**
  - `source venv/bin/activate && python scripts/hb_leaderboard_candidate_probe.py` → **通過**，確認 train / leaderboard / live blocker 語義一致
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 731` → **通過**

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #731：
  - Raw / Features / Labels：**21413 / 12842 / 42933**
  - 本輪增量：**+1 raw / +1 feature / +12 labels**
  - canonical target `simulated_pyramid_win`：**0.5752**
  - 240m labels：**21561 rows / target_rows 12639 / lag_vs_raw 3.3h**
  - 1440m labels：**12287 rows / target_rows 12287 / lag_vs_raw 23.1h**
  - recent raw age：**約 4.3 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**18/30 pass**
- TW-IC：**28/30 pass**
- TW 歷史：**#731=28/30，#730=28/30，#729=26/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 98.0%**
  - avg_quality：**0.6686**
  - avg_pnl：**+0.0208**
  - avg_drawdown_penalty：**0.0399**
- 判讀：近期 canonical 視窗仍是**被支持的極端趨勢口袋**；這不是 bull live blocker 已解掉的證據。

### 模型 / shrinkage / bull support governance
- `model/last_metrics.json`
  - train profile：**`core_plus_macro`**
  - train meta：**`bull_exact_live_lane_proxy` / 50 rows / exact_live_bucket_rows=0**
- `data/feature_group_ablation.json`
  - global recommended profile：**`core_only`**
- `data/bull_4h_pocket_ablation.json`
  - bull all best：**`core_plus_macro_plus_all_4h`**
  - bull collapse q35 best：**`core_plus_macro`**
  - `bull_exact_live_lane_proxy_rows = 50`
  - `bull_live_exact_lane_bucket_proxy_rows = 38`
  - `bull_supported_neighbor_buckets_proxy_rows = 12`
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_only`**
  - train support cohort：**`bull_exact_live_lane_proxy`**
  - `support_governance_route = exact_live_bucket_proxy_available`
- 判讀：**前一輪要求的 train artifact refresh 已完成**；目前剩下的不是「訓練 meta 還沒更新」，而是 **exact live bucket 本身仍 0-support**。

### Live predictor / bull blocker
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.2962**
  - regime：**bull**
  - gate：**ALLOW**
  - entry quality：**0.4826 (D)**
  - allowed layers：**0 → 0**
  - should trade：**false**
  - execution guardrail：
    - `decision_quality_below_trade_floor`
    - `unsupported_exact_live_structure_bucket_blocks_trade`
  - exact live lane：**14 rows / win_rate 0.50 / quality 0.2412**
  - current live structure bucket：**`ALLOW|base_allow|q65` rows = 0**
  - calibration scope：**`regime_label` / sample_size=199**
  - recent narrowed pathology：**`regime_label+entry_quality_label` rows=152 / win_rate=0.1053 / quality=-0.1803**
- 判讀：**治理路徑已可用、train artifact 已刷新，但部署仍 blocked**。當前 live ALLOW|q65 bucket 沒有 exact 支持樣本，且 bull same-regime narrowed lane 品質仍差，因此 `0 layers` 仍是正確行為。

### Source blockers
- blocked sparse features：**8 個**
- blocker 分布：
  - `archive_required`: **3**
  - `snapshot_only`: **4**
  - `short_window_public_api`: **1**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. bull exact live structure bucket 仍是 0-support，runtime 必須維持 0 layers
**現象**
- live 仍是 **bull / ALLOW / D / 0 layers**。
- `current_live_structure_bucket = ALLOW|base_allow|q65`，但 exact bucket rows 仍是 **0**。
- train artifact 雖已刷新到 `bull_exact_live_lane_proxy`，仍不能當成部署授權。

**判讀**
- 目前 blocker 已從「train meta 沒刷新」收斂成**exact bucket 缺真支持樣本 + live path 品質不足**。
- 這是**部署 blocker**，不是 retrain contract blocker。

**下一步方向**
- 維持 `0 layers`。
- 下一輪優先針對 bull live exact bucket 的 support accumulation / same-bucket evidence / pathology lane 做治理，而不是再重報 train meta 已刷新。

---

### P1. bull live 決策品質路徑仍被 4H 結構 pathology 壓制
**現象**
- chosen scope：`regime_label`
- narrowed worst scope：`regime_label+entry_quality_label`
- worst narrowed lane：**152 rows / win_rate 0.1053 / quality -0.1803 / dominant bull|BLOCK 76.3%**
- top shifts 仍集中在：
  - `feat_4h_dist_swing_low`
  - `feat_4h_dist_bb_lower`
  - `feat_4h_bb_pct_b`

**判讀**
- 即使 exact live lane 本身是 14 rows、win_rate 0.5，broader same-regime D lane 與 spillover lanes 仍顯示壞 pocket 會把 live decision-quality 壓回 D。
- 目前主要問題不在 global shrinkage，而在 **bull 4H 結構 pocket 的樣本與品質**。

**下一步方向**
- 直接檢查 bull exact / proxy pockets 的 same-bucket support 與 4H 結構塌陷條件，判定是要補 support、調整 lane selection，還是維持 blocker。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1543)**

**判讀**
- 這仍是**外部憑證缺失 blocker**。
- 未補憑證前，不應列為主決策成熟特徵。

---

## 本輪已清掉的問題

### RESOLVED. train artifact 尚未刷新到新的 exact-proxy 治理順序
**現象（上輪）**
- `model/last_metrics.json.feature_profile_meta.support_cohort` 仍停在舊的 `bull_supported_neighbor_buckets_proxy`。

**本輪 patch + 證據**
- 已直接重訓並重寫 `model/last_metrics.json`。
- 目前 train meta：**`bull_exact_live_lane_proxy` / 50 rows / exact_live_bucket_rows=0**。
- `leaderboard_feature_profile_probe.json` 也已同步看到相同 support cohort。

**狀態**
- **已修復**；下一輪不該再把「train artifact 尚未刷新」當主要 blocker。

### RESOLVED. `model/train.py` 不能直接重跑，需手動補 `PYTHONPATH`
**現象（本輪發現）**
- 直接 `python model/train.py` 會 `ModuleNotFoundError: No module named 'database'`。

**本輪 patch + 證據**
- 在 `model/train.py` 新增 repo-root `sys.path` bootstrap。
- 之後直接執行 `source venv/bin/activate && python model/train.py` 已通過。

**狀態**
- **已修復**；下一輪若要重刷 train artifact，不應再依賴手動 `PYTHONPATH` workaround。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **完成前一輪要求的 train artifact refresh。** ✅
2. **把 retrain 入口補成可直接重跑，避免下輪再被 shell 前置條件卡住。** ✅
3. **維持 bull exact bucket 仍 0-support 時的 `0 layers` 部署紀律。** ✅

### 本輪不做
- 不放寬 bull live guardrail。
- 不把 proxy cohort 誤認為 exact bucket 已修好。
- 不把 `fin_netflow` auth blocker 包裝成內部模型問題。

---

## 下一輪 gate

- **Next focus:**
  1. 直接推進 **bull exact live structure bucket 的 support / pathology 治理**，確認 exact bucket 為何仍 0-support；
  2. 持續驗證 live predictor 在 bull / ALLOW / D 情境下必須維持 `allowed_layers=0`；
  3. 繼續把 `fin_netflow` 當外部 source blocker 顯式管理。

- **Success gate:**
  1. next run 必須留下至少一個與 **bull exact bucket 真支持樣本或 live-path pathology root cause** 直接相關的 patch / artifact / verify；
  2. `leaderboard_feature_profile_probe.json`、`live_predict_probe.json`、`bull_4h_pocket_ablation.json`、`model/last_metrics.json` 對 bull blocker 的治理語義零漂移；
  3. 若 exact bucket 仍 0，heartbeat 必須明確維持 `0 layers`，不可把 proxy rows 誤寫成部署證據。

- **Fallback if fail:**
  - 若 exact bucket 仍 0-support，下一輪至少要留下 same-bucket / proxy-bucket / narrowed-pathology 的 machine-readable root-cause artifact，不能只重報 0；
  - 若 live path 仍被 bull narrowed lane 拖垮，下一輪優先修 lane selection / support evidence / pathology contract，而不是再重跑 retrain；
  - 若 `fin_netflow` auth 未修，持續標記 blocked，不准把 coverage 改善寫成既成事實。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull blocker 治理契約再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_731_summary.json`
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `model/last_metrics.json`
  2. 逐條確認：
     - `model/last_metrics.json.feature_profile_meta.support_cohort` 是否仍為 **`bull_exact_live_lane_proxy`**；
     - `alignment.support_governance_route` 是否仍為 `exact_live_bucket_proxy_available`（或已升級為 `exact_live_bucket_supported`）；
     - `alignment.live_current_structure_bucket_rows` 是否仍為 **0**；
     - `live_predict_probe.allowed_layers` 是否仍為 **0**；
     - `live_predict_probe.decision_quality_scope_diagnostics["regime_label+entry_quality_label"]` 是否仍是 bull live path 的主要 pathology lane。
  3. 若 train support cohort 仍正確、但 exact bucket 仍 0，下一輪不得再把「重訓工件」當主題；必須直接推進 **exact bucket support / live-path pathology**。