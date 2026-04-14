# ISSUES.md — Current State Only

_最後更新：2026-04-14 14:10 UTC — Heartbeat #730（bull exact bucket 支持樣本治理路徑已 machine-readable 化）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#729）要求本輪處理
- **Next focus**：
  1. 直接推進 **bull exact bucket 支持樣本治理**；
  2. 維持 `core_only`（leaderboard winner）與 `core_plus_macro`（train fallback）雙軌語義零漂移；
  3. 持續把 `fin_netflow` 當外部 source blocker 管理。
- **Success gate**：
  1. 本輪必須留下至少一個與 bull exact bucket 支持樣本治理直接相關的 patch / artifact / verify；
  2. 若 exact bucket 仍 0，必須明確維持 `0 layers`，並把 blocker 與治理路徑說清楚；
  3. probe / summary / docs 對 bull blocker 與 dual-profile 語義不得漂移。
- **Fallback if fail**：
  - 若仍無法直接補 exact bucket 樣本，至少要把治理路徑 machine-readable 化；
  - 若 probe / summary 缺欄位，下一輪先修 contract；
  - `fin_netflow` 未補 auth 前持續維持 blocked。

### 本輪承接結果
- **已處理**：
  - 已落地 **bull exact bucket 支持樣本治理 patch**：`model/train.py` 的 support-aware profile 選擇順序改為 `bull_live_exact_lane_bucket_proxy → bull_exact_live_lane_proxy → bull_supported_neighbor_buckets_proxy → bull_collapse_q35`，不再先退回較寬鬆 cohort。
  - 已落地 **治理路徑 machine-readable contract**：`scripts/hb_leaderboard_candidate_probe.py` 現在會輸出 `support_governance_route`、`bull_exact_live_lane_proxy_*`、`bull_live_exact_bucket_proxy_*`。
  - 已用 `pytest`、`hb_leaderboard_candidate_probe.py`、`hb_parallel_runner.py --fast --hb 730` 完成驗證。
- **仍未解**：
  - live exact structure bucket 仍為 **0 rows**，runtime 仍必須 `0 layers`。
  - `model/last_metrics.json` 目前仍保留上一版 train meta（`bull_supported_neighbor_buckets_proxy`），尚未重新訓練把新治理順序灌入訓練工件。
  - `fin_netflow` 仍是 **auth_missing**。
- **本輪明確不做**：
  - 不放寬 bull live guardrail。
  - 不把 proxy cohort 誤寫成 exact bucket 已修好。
  - 不把 `fin_netflow` auth blocker 誤報成 local feature/calibration 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `model/train.py`
    - `select_feature_profile()` 的 support-aware cohort 優先序改為：
      `bull_live_exact_lane_bucket_proxy` → `bull_exact_live_lane_proxy` → `bull_supported_neighbor_buckets_proxy` → `bull_collapse_q35`。
    - 目的：當 exact live bucket 仍 0 support 時，訓練 fallback 先依附**最接近當前 live bucket 的代理樣本**，而不是先回退到較寬鬆 cohort。
  - `scripts/hb_leaderboard_candidate_probe.py`
    - 新增 `support_governance_route`、`bull_exact_live_lane_proxy_profile/rows`、`bull_live_exact_bucket_proxy_profile/rows`。
    - 目的：讓 heartbeat / docs / probe 可以 machine-read「目前治理靠哪一層代理樣本」。
  - `tests/test_train_target_metrics.py`
    - 新增 regression test，鎖住「有 exact live bucket proxy 時要優先選它」的訓練治理邏輯。
  - `tests/test_hb_leaderboard_candidate_probe.py`
    - 新增 regression test，鎖住 probe 的 `support_governance_route` 與 proxy rows/profile 輸出。
  - `ARCHITECTURE.md`
    - 同步 support-aware training / leaderboard probe 的治理契約。

- **驗證（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_train_target_metrics.py tests/test_hb_leaderboard_candidate_probe.py -q` → **11 passed**
  - `source venv/bin/activate && python scripts/hb_leaderboard_candidate_probe.py` → **通過**，alignment 現在輸出：
    - `support_governance_route = exact_live_bucket_proxy_available`
    - `bull_exact_live_lane_proxy_rows = 50`
    - `bull_live_exact_bucket_proxy_rows = 38`
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 730` → **通過**

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #730：
  - Raw / Features / Labels：**21412 / 12841 / 42921**
  - 本輪增量：**+2 raw / +2 features / +7 labels**（相對 #729）
  - canonical target `simulated_pyramid_win`：**0.5750**
  - 240m labels：**21560 rows / target_rows 12638 / lag_vs_raw 3.3h**
  - 1440m labels：**12276 rows / target_rows 12276 / lag_vs_raw 23.0h**
  - recent raw age：**約 4.4 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**18/30 pass**
- TW-IC：**28/30 pass**
- TW 歷史：**#730=28/30，#729=26/30，#728=26/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 98.4%**
  - avg_quality：**0.6663**
  - avg_pnl：**+0.0207**
  - avg_drawdown_penalty：**0.0379**
- 判讀：近期 canonical 視窗仍是**被支持的極端趨勢口袋**，不是 bull live blocker 已解掉的證據。

### 模型 / shrinkage / bull support governance
- `data/feature_group_ablation.json`
  - global recommended profile：**`core_only`**
- `data/bull_4h_pocket_ablation.json`
  - bull all best：**`current_full`**
  - bull collapse q35 best：**`core_plus_macro`**
  - `bull_exact_live_lane_proxy_rows = 50`
  - `bull_live_exact_lane_bucket_proxy_rows = 38`
  - `bull_supported_neighbor_buckets_proxy_rows = 12`
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_only`**
  - dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
  - blocked candidate：**`core_plus_macro` → `unsupported_exact_live_structure_bucket`**
  - **NEW** `support_governance_route = exact_live_bucket_proxy_available`
  - **NEW** `bull_exact_live_lane_proxy_profile/rows = core_plus_macro / 50`
  - **NEW** `bull_live_exact_bucket_proxy_profile/rows = core_plus_macro / 38`
- `model/last_metrics.json`
  - train profile 仍為：**`core_plus_macro`**
  - train meta 仍指向：**`bull_supported_neighbor_buckets_proxy` / 84 rows / exact_live_bucket_rows=0**
- 判讀：**治理路徑已明確化，但訓練工件尚未重刷到新順序**。本輪真正前進的是「知道該用哪個代理 cohort」，不是「已可放寬 live deployment」。

### Live predictor / bull blocker
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.0966**
  - regime：**bull**
  - gate：**ALLOW**
  - entry quality：**0.4706 (D)**
  - allowed layers：**0 → 0**
  - should trade：**false**
  - execution guardrail：
    - `decision_quality_below_trade_floor`
    - `unsupported_exact_live_structure_bucket_blocks_trade`
  - exact live lane：**14 rows / win_rate 0.50 / quality 0.2412**
  - current live structure bucket：**`ALLOW|base_allow|q65` rows = 0**
  - exact-bucket proxy rows：**38**
  - exact-lane proxy rows：**50**
- 判讀：**exact bucket 本身仍無真支持樣本**，所以 runtime 擋單仍正確；但下一輪已不該再只說「0 support」，因為 proxy 治理路徑已經 machine-readable。

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
- `unsupported_exact_live_structure_bucket_blocks_trade` 仍成立。
- `current_live_structure_bucket = ALLOW|base_allow|q65`，但 exact bucket rows 仍是 **0**。

**本輪新進展**
- 治理路徑不再是黑箱：
  - `support_governance_route = exact_live_bucket_proxy_available`
  - `bull_live_exact_bucket_proxy_rows = 38`
  - `bull_exact_live_lane_proxy_rows = 50`

**判讀**
- 目前 blocker 仍是**exact bucket 本身缺真樣本**，不是 guardrail 過嚴。
- 但本輪已把「下一條該走哪個代理 cohort」正式 machine-readable 化。

**下一步方向**
- 維持 `0 layers`。
- 下一輪要把**訓練工件 / metrics / docs**正式切到新的 proxy 優先序，不能只停在 probe 已經看得到 route。

---

### P1. train fallback 的治理順序已修，但訓練工件尚未重刷到新 contract
**現象**
- code 已修：train 會優先選 `bull_live_exact_lane_bucket_proxy` / `bull_exact_live_lane_proxy`。
- 但 `model/last_metrics.json` 仍保留舊 meta：`bull_supported_neighbor_buckets_proxy`。

**判讀**
- 這是**工件尚未刷新**，不是 patch 未落地。
- 若下一輪不重刷訓練工件，文件會再次出現「probe 已說有 exact proxy，train meta 卻還停在 neighbor proxy」的語義漂移。

**下一步方向**
- 下一輪優先執行能重寫 `model/last_metrics.json` 的 train/retrain 驗證，確認 train meta 改成新的 proxy cohort。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1542)**

**判讀**
- 這仍是**外部憑證缺失 blocker**。
- 未補憑證前，不應列為主決策成熟特徵。

---

## 本輪已清掉的問題

### RESOLVED. bull exact bucket 支持樣本治理路徑不可見
**現象（上輪）**
- 文件只知道 exact bucket 仍 0 support，但無法 machine-read 下一條治理路徑是 exact-lane proxy、exact-bucket proxy、還是 neighbor proxy。

**本輪 patch + 證據**
- `model/train.py` 已把 support-aware selection 改成優先 exact proxy。
- `scripts/hb_leaderboard_candidate_probe.py` 已輸出：
  - `support_governance_route`
  - `bull_exact_live_lane_proxy_*`
  - `bull_live_exact_bucket_proxy_*`
- 相關 regression tests 已通過。

**狀態**
- **已修復**；下一輪不該再回到只說「unsupported_exact_live_structure_bucket」卻沒有治理路徑細節。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 bull exact bucket 支持樣本治理路徑正式 machine-readable 化。** ✅
2. **維持 dual-profile 語義零漂移，同時明確指出 train artifact 尚未重刷。** ✅
3. **用 #730 事實覆寫 ISSUES / ROADMAP / ARCHITECTURE。** ✅

### 本輪不做
- 不放寬 bull live guardrail。
- 不把 proxy cohort 誤認為 exact bucket 已修好。
- 不處理 `fin_netflow` auth 以外的虛假替代敘事。

---

## 下一輪 gate

- **Next focus:**
  1. 重新訓練/刷新 `model/last_metrics.json`，讓 train meta 真正採用新的 proxy 優先序；
  2. 持續驗證 bull exact bucket 仍為 0 時，runtime 必須維持 `0 layers`；
  3. 繼續把 `fin_netflow` 當外部 source blocker 顯式治理。

- **Success gate:**
  1. next run 必須留下至少一個**能刷新 train artifact** 的 patch / run / verify，讓 `feature_profile_meta.support_cohort` 不再停在舊的 `bull_supported_neighbor_buckets_proxy`；
  2. `leaderboard_feature_profile_probe.json`、`live_predict_probe.json`、`bull_4h_pocket_ablation.json`、`model/last_metrics.json` 對 bull blocker 的治理語義零漂移；
  3. 若 exact bucket 仍 0，heartbeat 仍需明確維持 `0 layers`，不可把 proxy rows 包裝成可部署證據。

- **Fallback if fail:**
  - 若本輪仍無法重刷訓練工件，下一輪至少要留下**可重跑的 retrain artifact / command / contract**，不能只停在 probe 已有 route；
  - 若 exact bucket rows > 0，必須同輪更新 live probe / bull pocket / leaderboard probe / docs；
  - 若 `fin_netflow` auth 未修，持續標記 blocked，不准把 coverage 改善寫成既成事實。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 support-governance contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_730_summary.json`
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `model/last_metrics.json`
  2. 逐條確認：
     - `alignment.support_governance_route` 是否仍為 `exact_live_bucket_proxy_available`（或已升級成 `exact_live_bucket_supported`）；
     - `alignment.bull_exact_live_lane_proxy_rows` 是否仍 ≥ 50；
     - `alignment.bull_live_exact_bucket_proxy_rows` 是否仍 > 0；
     - `alignment.live_current_structure_bucket_rows` 是否仍為 0；
     - `model/last_metrics.json.feature_profile_meta.support_cohort` 是否已從舊的 `bull_supported_neighbor_buckets_proxy` 切到新的 exact proxy 路徑。
  3. 若前四項大致不變、但最後一項仍未刷新，下一輪不得只重跑 fast heartbeat；必須直接推進**訓練工件重刷 / support-aware retrain 驗證**。