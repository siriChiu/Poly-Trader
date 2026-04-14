# ISSUES.md — Current State Only

_最後更新：2026-04-14 16:54 UTC — Heartbeat #736（已修正 bull q35 under-minimum exact bucket 的 blocker_state 漂移：當 exact bucket 已出現但仍 < minimum support 時，不再誤標成 `exact_missing`）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#735）要求本輪處理
- **Next focus**：
  1. 直接推進 `CAUTION|structure_quality_caution|q35` exact bucket 9 → 50 的 support 根因；
  2. 釐清 exact 9 / exact lane 26 / proxy 52 / broader same-bucket 10 之間，到底是 proxy cohort 過寬，還是 bull D pocket 本身不適合部署；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。
- **Success gate**：
  1. 必須留下至少一個與 q35 under-minimum exact bucket 直接相關的 patch / artifact / verify；
  2. blocker 語義在 artifact / probe / docs 間零漂移；
  3. exact rows < 50 時不得包裝成可部署。
- **Fallback if fail**：
  - 若 q35 exact rows 長期停在低位，優先懷疑 q35 bucket contract，而不是繼續等待自然累積；
  - 若 proxy cohort 與 exact rows 差異過大，優先縮窄 proxy；
  - `fin_netflow` auth 未修前持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - `scripts/bull_4h_pocket_ablation.py` 已修正 under-minimum 判斷順序：當 `exact_live_bucket_rows > 0` 且 `< minimum_support_rows` 時，`blocker_state` 固定維持 `exact_lane_proxy_fallback_only`，即使 exact-bucket proxy 已達 minimum；
  - 新增 regression tests，鎖住「exact bucket 已出現 + proxy 已就緒」這種最容易語義漂移的情境；
  - `ARCHITECTURE.md` 已同步 machine-readable contract，明確分開 `support_blocker_state` 與 `support_governance_route` 的語義。
- **本輪觀察導致前提更新**：
  - q35 exact bucket 已從 **9 rows → 10 rows**；
  - q35 exact-bucket proxy 已從 **52 rows → 53 rows**；
  - `support_governance_route` 仍是 **`exact_live_bucket_present_but_below_minimum`**，`allowed_layers` 仍是 **0**；
  - 也就是說：**blocker 語義已對齊，但 blocker 本身尚未解除。**
- **本輪明確不做**：
  - 不放寬 `allowed_layers=0`；
  - 不把 proxy 53 rows 當成 exact bucket 已被支持；
  - 不把 `fin_netflow` auth blocker 混入 bull q35 根因。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/bull_4h_pocket_ablation.py`
    - 修正 `support_pathology_summary` 的 under-minimum precedence；
    - exact bucket 已出現但 < 50 時，`blocker_state` 不再回退成 `exact_live_bucket_proxy_ready_but_exact_missing`；
    - 若 proxy 已達 minimum，`preferred_support_cohort` 仍可指向 `bull_live_exact_lane_bucket_proxy`，但 blocker 仍維持 under-minimum。
  - `tests/test_bull_4h_pocket_ablation.py`
    - 新增 q35 exact bucket 10 / proxy 53 的 regression case。
  - `tests/test_hb_leaderboard_candidate_probe.py`
    - 將 under-minimum probe case 改為 proxy 已達 minimum，驗證 probe alignment 仍回報 under-minimum route。
  - `ARCHITECTURE.md`
    - 新增 Heartbeat #736 的 under-minimum blocker-state 對齊約束。
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **16 passed**
- **Heartbeat verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 736` → **通過**

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #736：
  - Raw / Features / Labels：**21419 / 12848 / 42948**
  - 本輪增量：**+1 raw / +1 feature / +2 labels**
  - canonical target `simulated_pyramid_win`：**0.5755**
  - 240m labels：**21567 rows / target_rows 12645 / lag_vs_raw 3.2h**
  - 1440m labels：**12296 rows / target_rows 12296 / lag_vs_raw 23.1h**
  - recent raw age：**約 4.3 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**27/30 pass**
- TW 歷史：**#736=27/30，#735=27/30，#734=27/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 96.0%**
  - avg_quality：**0.6711**
  - avg_pnl：**+0.0208**
  - avg_drawdown_penalty：**0.0389**
- 判讀：近期 canonical path 仍是 supported extreme trend，不能被誤用成 bull D pocket 已可部署的證據。

### Live predictor / bull blocker
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.5904**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.3890 (D)**
  - allowed layers：**0 → 0**
  - should trade：**false**
  - execution guardrail：**`decision_quality_below_trade_floor`**
  - chosen calibration scope：**`regime_label` / sample_size=204**
  - exact live lane（`bull|CAUTION|D`）：**27 rows / win_rate 0.5185 / quality 0.2177**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=10**
  - narrowed bull+D pathology：**157 rows / win_rate 0.1338 / quality -0.1522 / gate dominated by `bull|BLOCK`**
  - broader `regime_gate+entry_quality_label`：**2784 rows / dominant regime chop 97.2% / spillover not representative of bull live lane**
- `docs/analysis/bull_4h_pocket_ablation.md`
  - blocker_state：**`exact_lane_proxy_fallback_only`**
  - exact bucket root cause：**`exact_bucket_present_but_below_minimum`**
  - current bucket gap to minimum：**40**（10 / 50）
  - preferred support cohort：**`bull_live_exact_lane_bucket_proxy`**
  - exact-bucket proxy：**53 rows / win_rate 0.9434**
  - exact live lane：**27 rows / win_rate 0.5185 / quality 0.2177**
  - broader same bucket：**12 rows / dominant regime = chop / win_rate 0.9167 / quality 0.5953**
  - bucket comparison takeaway：**`prefer_same_bucket_proxy_over_cross_regime_spillover`**
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_only`**
  - train selected profile：**`core_plus_macro`**
  - dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
  - blocked candidate：**`core_plus_macro` 因 `under_minimum_exact_live_structure_bucket` 被降級**
  - support_blocker_state：**`exact_lane_proxy_fallback_only`**
  - support_governance_route：**`exact_live_bucket_present_but_below_minimum`**
- 判讀：**本輪真正前進點是 blocker_state / governance_route / docs 已經零漂移。** 但 q35 exact bucket 仍只有 10 rows，runtime blocker 仍必須維持。

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. live bull `CAUTION|q35` exact bucket 仍是 under-minimum support（10 / 50）
**現象**
- live bucket：**`CAUTION|structure_quality_caution|q35`**
- exact rows：**10**；minimum support：**50**；gap：**40**
- exact live lane：**27 rows / win_rate 0.5185 / quality 0.2177**
- exact bucket proxy：**53 rows / win_rate 0.9434**
- broader same bucket：**12 rows / dominant regime = chop**

**判讀**
- blocker 已從「語義漂移」收斂成真正的**support 不足**問題；
- proxy 53 rows 只能當治理輔助，不足以解除 exact runtime blocker。

**下一步方向**
- 下一輪直接比對 exact 10 rows 與 proxy 53 rows 的 4H 結構差異，判定 proxy cohort 是否過寬；
- 若差異明顯，優先縮窄 proxy，而不是等待自然累積。

---

### P1. bull-only narrowed pathology 仍顯著偏壞，runtime 必須維持 0 layers
**現象**
- `regime_label+entry_quality_label`：**157 rows / win_rate 0.1338 / quality -0.1522**
- dominated gate：**`bull|BLOCK` 73.9%**
- live probe 預期：**expected_win_rate 0.10 / expected_quality -0.184 / layers 0**

**判讀**
- 即使 q35 exact bucket 本身較乾淨，bull-only 更寬的 D pocket 仍高度 pathological；
- runtime guardrail 維持 0 layers 是正確行為，現階段不能放寬。

**下一步方向**
- 下一輪對比 exact 10 rows 與 wider 157 rows 的 gate-path / 4H 結構 shift，確認是 q35 bucket 邊界過寬，還是 bull D pocket 本身不適合部署。

---

### P1. feature shrinkage 與 support-aware profile 仍分流：global `core_only`，bull-support-aware `core_plus_macro`
**現象**
- feature-group ablation global winner：**`core_only`**
- bull collapse-pocket best：**`core_plus_macro`**
- train selected profile：**`core_plus_macro`**（support-aware）
- leaderboard visible winner：**`core_only`**

**判讀**
- 這仍是刻意雙軌：
  - global 縮減層面仍是 `core_only`；
  - bull live blocker 研究仍需 `core_plus_macro`；
  - 但 exact bucket 未達 minimum support 前，leaderboard / runtime 都不能把 support-aware profile 包裝成 production winner。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1549)**

**判讀**
- 這仍是**外部憑證 blocker**，不是 bull lane 根因。

---

## 本輪已清掉的問題

### RESOLVED. bull pocket artifact 會把「exact bucket 已出現但仍 under-minimum」誤標成 `exact_missing`
**現象（修前）**
- 當 `current_live_structure_bucket_rows > 0`、但 exact-bucket proxy 已達 minimum 時，`blocker_state` 仍可能落成 `exact_live_bucket_proxy_ready_but_exact_missing`；
- 結果造成 artifact / probe / docs 口徑不一致：root cause 說 under-minimum，blocker_state 卻像 exact bucket 根本不存在。

**本輪 patch + 證據**
- `scripts/bull_4h_pocket_ablation.py`
  - under-minimum precedence 改為優先判斷 `current_live_structure_bucket_rows > 0`
- `tests/test_bull_4h_pocket_ablation.py`
  - 新增 q35 exact=9 / proxy=52 regression
- `tests/test_hb_leaderboard_candidate_probe.py`
  - 驗證在 under-minimum + proxy-ready 情境下，alignment 仍回報 `support_blocker_state=exact_lane_proxy_fallback_only`
- 最新 heartbeat 證據：
  - `support_blocker_state = exact_lane_proxy_fallback_only`
  - `support_governance_route = exact_live_bucket_present_but_below_minimum`
  - `exact_bucket_root_cause = exact_bucket_present_but_below_minimum`

**狀態**
- **已修復**；目前 artifact / leaderboard probe / docs 對 under-minimum exact bucket 的 blocker 語義已同步。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **修掉 q35 under-minimum exact bucket 的 blocker_state 漂移。** ✅
2. **用 regression test 鎖住「exact rows 已出現 + proxy 已就緒」的最危險漂移情境。** ✅
3. **重跑 fast heartbeat，確認 blocker 仍是 under-minimum support，而不是舊的 exact-missing 敘事。** ✅

### 本輪不做
- 不放寬 live layers。
- 不把 proxy 53 rows 當成 exact bucket 已支持。
- 不把 `fin_netflow` auth blocker 誤寫成模型問題。

---

## 下一輪 gate

- **Next focus:**
  1. 直接比對 **exact 10 rows / exact lane 27 rows / proxy 53 rows / broader same-bucket 12 rows** 的 4H 結構與 gate-path，判定 proxy cohort 是否過寬；
  2. 若 proxy 仍顯著寬於 exact，留下更窄的 q35 support-aware proxy contract 或 artifact；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q35 under-minimum exact bucket / proxy cohort 邊界** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`allowed_layers` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 exact bucket 仍 < 50，heartbeat 必須明確維持 blocker 語義，不得把 proxy / broader rows 寫成可部署。

- **Fallback if fail:**
  - 若 q35 exact rows 仍停在低位，下一輪優先縮窄 proxy cohort，而不是繼續等待自然累積；
  - 若 exact 10 rows 與 proxy 53 rows 差異過大，優先把 support-aware train cohort 改成更窄代理集合；
  - 若 `fin_netflow` auth 未修，持續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull support contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_736_summary.json`
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/live_predict_probe.json`
     - `data/leaderboard_feature_profile_probe.json`
  2. 逐條確認：
     - `support_pathology_summary.current_live_structure_bucket` 是否仍是 **`CAUTION|structure_quality_caution|q35`**；
     - `support_pathology_summary.current_live_structure_bucket_gap_to_minimum` 是否仍 **> 0**；
     - `support_pathology_summary.blocker_state` 是否仍是 **`exact_lane_proxy_fallback_only`**；
     - `support_governance_route` 是否仍是 **`exact_live_bucket_present_but_below_minimum`**；
     - `leaderboard_candidate_diagnostics.blocked_candidate_profiles[*].blocker_reason` 是否仍含 **`under_minimum_exact_live_structure_bucket`**；
     - `live_predict_probe.allowed_layers` 是否仍為 **0**。
  3. 若以上條件仍成立，下一輪不得再把「語義對齊完成」當主題；必須直接推進 **q35 under-minimum exact bucket / proxy cohort 邊界 / bull-only pathology**。
