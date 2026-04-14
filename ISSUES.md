# ISSUES.md — Current State Only

_最後更新：2026-04-14 15:03 UTC — Heartbeat #732（已把 bull exact bucket 缺口 / pathology 收斂成 machine-readable support artifact；部署 blocker 仍在）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#731）要求本輪處理
- **Next focus**：
  1. 直接推進 bull exact live structure bucket 的 support / pathology 治理；
  2. 持續驗證 bull / ALLOW / D 情境必須維持 `allowed_layers=0`；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。
- **Success gate**：
  1. 本輪必須留下至少一個與 bull exact bucket 真支持樣本或 live-path pathology root cause 直接相關的 patch / artifact / verify；
  2. probe / metrics / docs 對 bull blocker 治理語義零漂移；
  3. 若 exact bucket 仍 0，不能把 proxy rows 包裝成可部署證據。
- **Fallback if fail**：
  - 若 exact bucket 仍 0-support，至少留下 same-bucket / proxy-bucket / narrowed-pathology 的 machine-readable root-cause artifact；
  - 若 live path 仍被 bull narrowed lane 拖垮，優先修 lane selection / support evidence / pathology contract，而不是再重跑 retrain；
  - `fin_netflow` 未補 auth 前持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - 已對 `scripts/bull_4h_pocket_ablation.py` 落地 patch，新增 `support_pathology_summary`，把 bull live blocker 轉成 machine-readable 的 exact-bucket 缺口 / proxy fallback / pathology artifact。
  - 已產出並刷新：
    - `data/bull_4h_pocket_ablation.json`
    - `docs/analysis/bull_4h_pocket_ablation.md`
    - `data/heartbeat_732_summary.json`
  - 已再次驗證 live runtime 仍為 `allowed_layers=0`，未把 proxy rows 誤寫成部署證據。
- **仍未解**：
  - exact live structure bucket 仍 **0 rows**；`support_pathology_summary.blocker_state = exact_lane_proxy_fallback_only`。
  - bull same-regime pathology 仍由 4H 結構 pocket 主導；shared shifts 仍集中在 `feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`。
  - `fin_netflow` 仍是 **auth_missing**。
- **本輪明確不做**：
  - 不放寬 bull live guardrail；
  - 不把 `bull_live_exact_lane_bucket_proxy_rows=38` 誤寫成 exact bucket 已支持；
  - 不把 `fin_netflow` auth blocker 包裝成本地模型問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/bull_4h_pocket_ablation.py`
    - `live_context` 現在會攜帶 decision-quality scope / label / pathology scope / shared shift features；
    - 新增 `support_pathology_summary`，輸出：
      - `blocker_state`
      - `preferred_support_cohort`
      - `current_live_structure_bucket_gap_to_minimum`
      - `exact_live_bucket_proxy_gap_to_minimum`
      - `exact_live_lane_proxy_gap_to_minimum`
      - `dominant_neighbor_bucket`
      - `bucket_gap_vs_dominant_neighbor`
      - `pathology_worst_scope`
      - `recommended_action`
    - Markdown 分析檔同步顯示 support/pathology 摘要，讓下一輪不必再人工拼接 exact-bucket 缺口。
- **Tests（已通過）**
  - `tests/test_bull_4h_pocket_ablation.py`（新增）
  - `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_leaderboard_candidate_probe.py tests/test_train_target_metrics.py -q` → **13 passed**
- **Heartbeat verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 732` → **通過**

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #732：
  - Raw / Features / Labels：**21414 / 12843 / 42937**
  - 本輪增量：**+1 raw / +1 feature / +4 labels**
  - canonical target `simulated_pyramid_win`：**0.5753**
  - 240m labels：**21563 rows / target_rows 12641 / lag_vs_raw 3.4h**
  - 1440m labels：**12289 rows / target_rows 12289 / lag_vs_raw 23.3h**
  - recent raw age：**約 4.1 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**18/30 pass**
- TW-IC：**27/30 pass**
- TW 歷史：**#732=27/30，#731=28/30，#730=28/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 98.0%**
  - avg_quality：**0.6691**
  - avg_pnl：**+0.0208**
  - avg_drawdown_penalty：**0.0395**
- 判讀：近期 canonical 視窗仍是 supported extreme trend；這不能當成 bull live blocker 已解除的證據。

### Live predictor / bull blocker
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.5071**
  - regime：**bull**
  - gate：**ALLOW**
  - entry quality：**0.4967 (D)**
  - allowed layers：**0 → 0**
  - should trade：**false**
  - execution guardrail：
    - `decision_quality_below_trade_floor`
    - `unsupported_exact_live_structure_bucket_blocks_trade`
  - chosen calibration scope：**`regime_label` / sample_size=199**
  - exact live lane：**14 rows / win_rate 0.50 / quality 0.2412**
  - current live structure bucket：**`ALLOW|base_allow|q65` rows = 0**
  - worst pathology scope：**`regime_label+entry_quality_label`**
  - shared shift features：**`feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`**
- `data/bull_4h_pocket_ablation.json -> support_pathology_summary`
  - `blocker_state = exact_lane_proxy_fallback_only`
  - `preferred_support_cohort = bull_exact_live_lane_proxy`
  - `current_live_structure_bucket_gap_to_minimum = 50`
  - `exact_live_bucket_proxy_gap_to_minimum = 12`
  - `exact_live_lane_proxy_gap_to_minimum = 0`
  - `dominant_neighbor_bucket = ALLOW|base_allow|q85` / rows=14
  - `bucket_gap_vs_dominant_neighbor = 14`
  - `recommended_action = 維持 0 layers；優先查 exact bucket 缺口與 same-bucket pathology，而不是再重訓。`
- 判讀：本輪已把 blocker 從「口頭描述」升級成 **可機器讀取的 support / pathology 摘要**；部署仍 blocked，且主缺口仍是 exact bucket 真樣本不足 + same-regime pathology。

### 模型 / shrinkage / bull support governance
- `data/feature_group_ablation.json`
  - global recommended profile：**`core_only`**
- `data/bull_4h_pocket_ablation.json`
  - bull all best：**`core_plus_macro_plus_all_4h`**
  - bull collapse q35 best：**`core_plus_macro`**
  - bull exact live lane proxy：**50 rows / best=core_plus_macro**
  - bull live exact lane bucket proxy：**38 rows / best=core_plus_macro**
  - supported neighbor buckets proxy：**12 rows / best=None**
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_only`**
  - train selected profile：**`core_plus_macro`**
  - `support_governance_route = exact_live_bucket_proxy_available`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
- 判讀：治理路徑仍清楚分成兩件事：
  1. leaderboard/global winner 維持 `core_only`；
  2. train / support fallback 維持 `core_plus_macro`；
  3. 但 exact bucket 仍 0，因此 runtime 仍必須 `0 layers`。

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. bull exact live structure bucket 仍 0-support，且 root cause 已收斂成 fallback-only support 缺口
**現象**
- live 仍是 **bull / ALLOW / D / 0 layers**。
- `current_live_structure_bucket = ALLOW|base_allow|q65`，exact rows 仍 **0**。
- 新 artifact 已顯示：
  - current bucket gap to minimum = **50**
  - exact-bucket proxy gap = **12**
  - exact-lane proxy gap = **0**
  - blocker_state = **`exact_lane_proxy_fallback_only`**

**判讀**
- 現在的 blocker 已不是「缺 artifact」，而是 **exact bucket 真支持樣本仍為零**。
- 目前只能用 exact-lane proxy 做治理 fallback，不得用來授權部署。

**下一步方向**
- 下一輪必須直接查 `ALLOW|base_allow|q65` exact bucket 為何完全沒樣本，並留下 same-bucket / exact-bucket 的 root-cause patch 或新 artifact。

---

### P1. bull same-regime pathology 仍被 4H 結構 pocket 壓制
**現象**
- worst pathology scope：**`regime_label+entry_quality_label`**
- shared shift features：
  - `feat_4h_dist_swing_low`
  - `feat_4h_dist_bb_lower`
  - `feat_4h_bb_pct_b`
- `regime_label+entry_quality_label` 仍是 **152 rows / win_rate 0.1053 / quality -0.1803**。

**判讀**
- 問題主體仍是 bull same-regime 4H structure pocket，而不是 global calibration。
- 下一輪不應再把 retrain 當主題；應直接做 same-bucket / same-regime 4H pocket contract 檢查與修補。

**下一步方向**
- 檢查 `ALLOW|base_allow|q65` 與 `ALLOW|base_allow|q85` 的結構條件分界，確認是 gate 分桶過嚴、樣本累積不足，還是真正的壞 pocket。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1544)**

**判讀**
- 這仍是**外部憑證缺失 blocker**。
- 未補憑證前，不應列為主決策成熟特徵。

---

## 本輪已清掉的問題

### RESOLVED. bull blocker 缺少可機器讀取的 exact-bucket / pathology 摘要
**現象（上輪）**
- 文件要求下一輪至少留下 same-bucket / proxy-bucket / narrowed-pathology 的 machine-readable root-cause artifact。

**本輪 patch + 證據**
- `scripts/bull_4h_pocket_ablation.py` 新增 `support_pathology_summary` 與對應 markdown 摘要。
- `data/bull_4h_pocket_ablation.json` 現在已直接輸出 blocker_state、bucket gaps、preferred support cohort、worst pathology scope 與 recommended_action。
- `docs/analysis/bull_4h_pocket_ablation.md` 同步出現 Support / pathology summary 區塊。

**狀態**
- **已修復**；下一輪不該再說「缺少 bull exact bucket root-cause artifact」。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 bull exact bucket blocker 收斂成 machine-readable support/pathology artifact。** ✅
2. **再次驗證 exact bucket 仍 0 時 runtime 必須維持 `0 layers`。** ✅
3. **持續把 `fin_netflow` 當 source auth blocker 管理。** ✅

### 本輪不做
- 不放寬 bull live guardrail。
- 不把 `bull_live_exact_lane_bucket_proxy_rows=38` 誤報成 exact bucket 已支持。
- 不把 retrain 當成本輪主題。

---

## 下一輪 gate

- **Next focus:**
  1. 直接對 **`ALLOW|base_allow|q65` exact bucket 0-support** 做 root-cause patch / artifact；
  2. 釐清 bull same-regime 4H pocket 是 **分桶過嚴、樣本不足，還是真壞 pocket**；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q65 exact bucket 0-support** 直接相關的 patch / artifact / verify；
  2. `data/bull_4h_pocket_ablation.json.support_pathology_summary`、`data/live_predict_probe.json`、`data/leaderboard_feature_profile_probe.json` 對 blocker 的敘述零漂移；
  3. 若 exact bucket 仍 0，heartbeat 必須明確維持 `allowed_layers=0`，不可把任何 proxy rows 當部署證據。

- **Fallback if fail:**
  - 若 q65 exact bucket 仍 0 且未找出根因，下一輪至少要新增更窄的 same-bucket artifact（例如 exact bucket vs q85 proxy 的 feature/gate 對照）；
  - 若 same-regime pathology 仍集中在 4H 結構 shift，下一輪優先修分桶 / lane contract，不再重報 retrain；
  - 若 `fin_netflow` auth 未修，持續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull support/pathology contract 改變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_732_summary.json`
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/live_predict_probe.json`
     - `data/leaderboard_feature_profile_probe.json`
  2. 逐條確認：
     - `support_pathology_summary.blocker_state` 是否仍是 **`exact_lane_proxy_fallback_only`**；
     - `support_pathology_summary.current_live_structure_bucket_gap_to_minimum` 是否仍是 **50**；
     - `support_pathology_summary.exact_live_bucket_proxy_gap_to_minimum` 是否仍大於 0；
     - `live_predict_probe.allowed_layers` 是否仍為 **0**；
     - `live_predict_probe.decision_quality_scope_diagnostics["regime_label+entry_quality_label"]` 是否仍是主要 pathology scope。
  3. 若以上條件仍成立，下一輪不得再把「artifact 已齊」當主題；必須直接推進 **q65 exact bucket root cause**。