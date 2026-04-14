# ISSUES.md — Current State Only

_最後更新：2026-04-14 15:53 UTC — Heartbeat #734（live bull bucket 從上輪 q35 under-supported 轉回 q65 exact=0；本輪補上 leaderboard probe 的 under-minimum exact-bucket 語義，避免再次把「有幾筆 exact rows」誤寫成已支持）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#733）要求本輪處理
- **Next focus**：
  1. 直接追 `CAUTION|structure_quality_caution|q35` exact bucket 5→50 的 support 累積 / contract root cause；
  2. 對 exact rows、exact-bucket proxy、supported neighbors 做同桶/鄰桶 4H 差異與 pathology 對照；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。
- **Success gate**：
  1. 本輪必須留下至少一個與 q35 exact bucket under-supported 直接相關的 patch / artifact / verify；
  2. blocker 語義在 probe / artifact / docs 間零漂移；
  3. 若 exact rows 仍 < 50，不得包裝成可部署。
- **Fallback if fail**：
  - 若 q35 exact rows 長期卡住，優先懷疑 lane / bucket contract；
  - 若 narrower pathology 仍差，優先修 runtime lane contract / veto；
  - `fin_netflow` auth 未修前持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - 已 patch `scripts/hb_leaderboard_candidate_probe.py`，把「exact bucket 已出現但低於 minimum support」獨立 machine-read 成 `support_governance_route=exact_live_bucket_present_but_below_minimum`，並同步輸出：
    - `minimum_support_rows`
    - `live_current_structure_bucket_gap_to_minimum`
    - `exact_bucket_root_cause`
    - `support_blocker_state`
  - 已新增 / 擴充 `tests/test_hb_leaderboard_candidate_probe.py`，鎖住：
    - exact-bucket proxy route
    - under-minimum exact bucket route
    - 新增欄位的 regression
  - 已同步 `ARCHITECTURE.md` 的 governance-route contract。
- **未照原先路徑持續成立的地方**：
  - live bull bucket **不再是** q35 under-supported；本輪已回到 **`ALLOW|base_allow|q65` exact rows = 0**。
  - 因此本輪主 blocker 由「q35 已出現但不足支持」轉為「q65 exact bucket 消失，只剩 q85 same-lane neighbor 與 broader neutral spillover」。
- **本輪明確不做**：
  - 不放寬 `allowed_layers=0`；
  - 不把 `exact_live_lane_proxy_rows=50` 或 `exact_live_bucket_proxy_rows=38` 誤寫成 exact bucket 已支持；
  - 不把 `fin_netflow` auth blocker 包裝成 bull lane 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_leaderboard_candidate_probe.py`
    - 新增 under-minimum exact bucket route：`exact_live_bucket_present_but_below_minimum`
    - alignment 現在會持久化 `minimum_support_rows / live_current_structure_bucket_gap_to_minimum / exact_bucket_root_cause / support_blocker_state`
  - `tests/test_hb_leaderboard_candidate_probe.py`
    - 新增 under-minimum exact bucket regression test
    - 擴充 exact-bucket proxy scenario 驗證新欄位
  - `ARCHITECTURE.md`
    - 補上 #734 governance-route contract，避免 probe 把 under-minimum 誤判成 supported
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_bull_4h_pocket_ablation.py tests/test_train_target_metrics.py -q` → **15 passed**
- **Artifact verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_leaderboard_candidate_probe.py` → **通過**
- **Heartbeat verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 734` → **通過**

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #734：
  - Raw / Features / Labels：**21416 / 12845 / 42942**
  - 本輪增量：**+1 raw / +1 feature / +2 labels**
  - canonical target `simulated_pyramid_win`：**0.5754**
  - 240m labels：**21565 rows / target_rows 12643 / lag_vs_raw 3.2h**
  - 1440m labels：**12292 rows / target_rows 12292 / lag_vs_raw 23.1h**
  - recent raw age：**約 4.1 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**18/30 pass**
- TW-IC：**27/30 pass**
- TW 歷史：**#734=27/30，#733=27/30，#732=27/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 97.6%**
  - avg_quality：**0.6699**
  - avg_pnl：**+0.0208**
  - avg_drawdown_penalty：**0.0390**
- 判讀：近期 canonical path 仍屬 supported extreme trend；這不是 live bull ALLOW lane 已可部署的證據。

### Live predictor / bull blocker
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.4814**
  - regime：**bull**
  - gate：**ALLOW**
  - entry quality：**0.4786 (D)**
  - allowed layers：**0 → 0**
  - should trade：**false**
  - execution guardrail：**`decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade`**
  - chosen calibration scope：**`regime_label` / sample_size=200**
  - exact live lane：**14 rows / win_rate 0.5000 / quality 0.2412 / all rows in `ALLOW|base_allow|q85`**
  - broader `regime_gate+entry_quality_label`：**115 rows / q65 rows 66 / win_rate 0.2348 / quality -0.0575**
  - broader recent dominant regime：**neutral 87.8%**
  - worst pathology scope：**`regime_label+entry_quality_label`**
  - shared negative 4H shifts：**`feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`**
- `data/bull_4h_pocket_ablation.json -> support_pathology_summary`
  - `blocker_state = exact_lane_proxy_fallback_only`
  - `current_live_structure_bucket = ALLOW|base_allow|q65`
  - `current_live_structure_bucket_rows = 0`
  - `current_live_structure_bucket_gap_to_minimum = 50`
  - `exact_live_bucket_proxy_rows = 38` → **gap 12**
  - `exact_live_lane_proxy_rows = 50` → **gap 0**
  - `supported_neighbor_bucket_rows = 12`
  - `exact_bucket_root_cause = cross_regime_spillover_dominates_q65`
  - `root_cause_interpretation`：較寬 ALLOW+D scope 內的 q65 主要由其他 regime 支配，bull exact lane 只剩 q85 neighbor。
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_only`**
  - train selected profile：**`core_plus_macro`**
  - dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
  - `support_governance_route = exact_live_bucket_proxy_available`
  - `live_current_structure_bucket_rows = 0`
  - blocked candidate：**`core_plus_macro: unsupported_exact_live_structure_bucket`**
- 判讀：本輪 bull live blocker 的核心不是 q35 under-supported，而是 **q65 exact bucket 消失 + broader q65 evidence 被 neutral spillover 汙染**。train 仍可用 same-lane proxy 選 `core_plus_macro`；leaderboard 正確地因 exact bucket = 0 而退回 `core_only`。

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. bull live q65 exact bucket 再次歸零，當前 blocker 變成 cross-regime spillover 主導
**現象**
- 當前 live bucket：**`ALLOW|base_allow|q65`**
- exact rows：**0**；minimum support：**50**；gap：**50**
- exact lane rows：**14**，但全部落在 **`ALLOW|base_allow|q85`**
- broader q65 rows：**66**，但 broader lane **115 rows** 中最近 87.8% 來自 **neutral|ALLOW**
- `exact_bucket_root_cause = cross_regime_spillover_dominates_q65`

**判讀**
- 上輪的 q35 under-supported 狀態已不是 current live 狀態。
- 目前需要處理的是：**q65 在 broader ALLOW+D lane 看似有 rows，但它們不是 live bull exact lane 的可部署證據。**

**下一步方向**
- 下一輪必須直接比較：
  1. bull exact lane `q85` 14 rows
  2. exact-bucket proxy `q65` 38 rows
  3. broader `q65` 66 rows（neutral spillover 主導）
- 目標是判定：
  - q65 bucket threshold 是否過嚴，或
  - ALLOW lane contract 是否被 neutral spillover 汙染到不應再當 bull calibration 代理。

---

### P1. bull ALLOW lane 的 broader evidence 仍是負品質 pocket，runtime 必須繼續 0 layers
**現象**
- exact live lane：**14 rows / win_rate 0.5000 / quality 0.2412**
- broader `regime_gate+entry_quality_label`：**115 rows / win_rate 0.2348 / quality -0.0575 / dd 0.3297 / tuw 0.7464**
- broader q65 bucket metrics：**66 rows / win_rate 0.3030 / quality -0.0380**
- worst narrowed pathology：**`regime_label+entry_quality_label` = 153 rows / win_rate 0.1111 / quality -0.1746**

**判讀**
- 即使 gate 回到 `ALLOW`，live contract 仍被 exact bucket 0-support 與 broader negative ALLOW pocket 擋住。
- 不得把 `ALLOW` 誤寫成「可部署」。

**下一步方向**
- 下一輪優先做 same-lane vs broader-lane 的 gate contract 對照 artifact，確認：
  - `q85 → q65` 是否只是 bucket 邊界問題；
  - 或者 broader ALLOW lane 已被 neutral spillover 汙染，應該被拒絕當 bull 代理 lane。

---

### P1. support-aware training 與 leaderboard ranking 仍故意分離，需持續防語義漂移
**現象**
- train selected profile：**`core_plus_macro`**（support cohort = `bull_exact_live_lane_proxy`, rows=50）
- leaderboard selected profile：**`core_only`**
- blocked candidate：**`core_plus_macro` 因 `unsupported_exact_live_structure_bucket` 被降級**
- `support_governance_route = exact_live_bucket_proxy_available`

**判讀**
- 這不是 profile 混亂，而是目前治理設計的**刻意分流**：
  - train 可使用 same-lane proxy 做 support-aware fallback；
  - leaderboard 不可把 0-support exact bucket 誤當成已支持。
- 下一輪仍必須保持這條語義零漂移。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1546)**

**判讀**
- 這仍是**外部憑證缺失 blocker**，不是模型 / bull lane 問題。

---

## 本輪已清掉的問題

### RESOLVED. leaderboard probe 無法區分 under-minimum exact bucket vs truly supported exact bucket
**現象（修前）**
- `scripts/hb_leaderboard_candidate_probe.py` 只要 `live_current_structure_bucket_rows > 0` 就會標成 `exact_live_bucket_supported`。
- 這會把「exact rows 已出現但仍低於 minimum support」誤寫成已支持，造成 blocker 語義漂移。

**本輪 patch + 證據**
- `scripts/hb_leaderboard_candidate_probe.py` 現在會：
  - 讀取 `support_pathology_summary.minimum_support_rows`
  - 在 under-minimum 狀況輸出 `support_governance_route=exact_live_bucket_present_but_below_minimum`
  - 同步輸出 `minimum_support_rows / live_current_structure_bucket_gap_to_minimum / exact_bucket_root_cause / support_blocker_state`
- `tests/test_hb_leaderboard_candidate_probe.py` 新增 under-minimum regression
- `pytest ...` → **15 passed**

**狀態**
- **已修復**；之後若 live exact bucket 再次出現少量 rows，不應再被 probe 誤判成 supported。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **補上 leaderboard probe 的 under-minimum exact-bucket machine-readable contract。** ✅
2. **重跑 fast heartbeat，確認 current live blocker 已從 q35 under-supported 轉回 q65 exact=0 + neutral spillover。** ✅
3. **維持 `fin_netflow` source auth blocker 顯式治理。** ✅

### 本輪不做
- 不放寬 live layers。
- 不把 `ALLOW` gate 當成可部署證據。
- 不重開 retrain side quest。

---

## 下一輪 gate

- **Next focus:**
  1. 直接追 **`ALLOW|base_allow|q65` exact bucket 為何仍是 0**，並對 `q85 exact lane 14 rows / q65 proxy 38 rows / broader q65 66 rows` 做同桶對照；
  2. 釐清 broader q65 是否只是 bucket 邊界問題，或已被 **neutral spillover** 汙染到不應作 bull calibration lane；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q65 exact bucket=0 / spillover-dominates** 直接相關的 patch / artifact / verify；
  2. `support_pathology_summary.exact_bucket_root_cause`、`leaderboard_feature_profile_probe.support_governance_route`、`live_predict_probe.allowed_layers` 對 blocker 的敘述零漂移；
  3. 若 exact bucket 仍 0，heartbeat 必須明確維持 blocker 語義，不得把 proxy / broader rows 寫成可部署。

- **Fallback if fail:**
  - 若 q65 exact bucket 持續 0，下一輪優先懷疑 q65 bucket contract / lane selection，而不是等待自然累積；
  - 若 broader q65 仍由 neutral spillover 主導，優先把這條 broader lane 從 bull calibration 代理集合中顯式降級；
  - 若 `fin_netflow` auth 未修，持續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull lane contract / governance route 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_734_summary.json`
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/live_predict_probe.json`
     - `data/leaderboard_feature_profile_probe.json`
  2. 逐條確認：
     - `support_pathology_summary.current_live_structure_bucket` 是否仍是 **`ALLOW|base_allow|q65`**；
     - `support_pathology_summary.current_live_structure_bucket_rows` 是否仍 **0**；
     - `support_pathology_summary.exact_bucket_root_cause` 是否仍是 **`cross_regime_spillover_dominates_q65`**；
     - `leaderboard_feature_profile_probe.support_governance_route` 是否仍是 **`exact_live_bucket_proxy_available`**；
     - `leaderboard_feature_profile_probe.live_current_structure_bucket_gap_to_minimum` 是否仍 **> 0**；
     - `live_predict_probe.allowed_layers` 是否仍為 **0**。
  3. 若以上條件仍成立，下一輪不得再把「train 可用 proxy profile」當主題；必須直接推進 **q65 exact bucket absent / broader neutral spillover / lane contract**。