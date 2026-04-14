# ISSUES.md — Current State Only

_最後更新：2026-04-14 16:29 UTC — Heartbeat #735（bull live blocker 已從「q65 exact=0」轉成「CAUTION|q35 exact bucket 已出現但仍低於 minimum support」；本輪補上 bucket-evidence comparison contract，並修正 leaderboard 會把 under-minimum exact bucket 誤當可選候選的語義漂移）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#734）要求本輪處理
- **Next focus**：
  1. 直接追 `ALLOW|base_allow|q65` exact bucket 為何仍是 0；
  2. 釐清 q85 exact lane / q65 proxy / broader q65 到底是 bucket 門檻問題還是 neutral spillover；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。
- **Success gate**：
  1. 必須留下至少一個與 q65 exact bucket absent / spillover 直接相關的 patch / artifact / verify；
  2. blocker 語義在 artifact / probe / docs 間零漂移；
  3. exact rows < 50 時不得包裝成可部署。
- **Fallback if fail**：
  - 若 q65 exact rows 持續 0，優先懷疑 bucket contract / lane selection；
  - 若 broader q65 仍由 neutral spillover 主導，優先把 broader lane 顯式降級；
  - `fin_netflow` auth 未修前持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - `scripts/bull_4h_pocket_ablation.py` 新增 `support_pathology_summary.bucket_evidence_comparison` 與 `bucket_comparison_takeaway`，把 **exact live lane / exact bucket proxy / broader same bucket** 變成 machine-readable artifact；
  - `backtesting/model_leaderboard.py` 現在會把 **under-minimum exact live bucket** 視為 blocker，避免 leaderboard 把 `exact_live_bucket_rows > 0 但 < minimum_support_rows` 的 support-aware 候選誤當可用；
  - `scripts/hb_parallel_runner.py` 會把新的 bucket comparison 摘要寫進 heartbeat summary，下一輪可直接承接。
- **本輪觀察導致前提更新**：
  - live bull blocker 已不再是 `ALLOW|base_allow|q65 exact=0`；
  - 最新 live path 變成 **`bull / CAUTION / D / CAUTION|structure_quality_caution|q35`**；
  - exact live bucket 已出現 **9 rows**，但仍低於 minimum support **50**，因此 blocker 轉為 **`exact_bucket_present_but_below_minimum`**。
- **本輪明確不做**：
  - 不放寬 `allowed_layers=0`；
  - 不把 `exact_live_bucket_rows=9` 寫成已解除 blocker；
  - 不把 `fin_netflow` auth blocker 混進 bull lane 根因。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/bull_4h_pocket_ablation.py`
    - 新增 `bucket_evidence_comparison = {exact_live_lane, exact_bucket_proxy, broader_same_bucket}`
    - 新增 `bucket_comparison_takeaway`
    - markdown artifact 現在直接列出 exact lane / proxy / broader same-bucket 對照表
  - `backtesting/model_leaderboard.py`
    - `support_aware_profile` 若 `0 < exact_live_bucket_rows < minimum_support_rows`，現在標成 `under_minimum_exact_live_structure_bucket`
    - leaderboard 不再把 under-minimum exact bucket 候選當成已支持候選
  - `scripts/hb_parallel_runner.py`
    - heartbeat summary 現在同步持久化 `support_pathology_summary.bucket_evidence_comparison` 與 `bucket_comparison_takeaway`
  - `ARCHITECTURE.md`
    - 同步寫入 Heartbeat #735 的 bucket-evidence comparison contract
  - 測試：
    - `tests/test_bull_4h_pocket_ablation.py`
    - `tests/test_hb_parallel_runner.py`
    - `tests/test_model_leaderboard.py`
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_parallel_runner.py tests/test_model_leaderboard.py tests/test_hb_leaderboard_candidate_probe.py -q` → **35 passed**
- **Heartbeat verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 735` → **通過**

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #735：
  - Raw / Features / Labels：**21418 / 12847 / 42946**
  - 本輪增量：**+1 raw / +1 feature / +1 label**
  - canonical target `simulated_pyramid_win`：**0.5754**
  - 240m labels：**21566 rows / target_rows 12644 / lag_vs_raw 3.4h**
  - 1440m labels：**12295 rows / target_rows 12295 / lag_vs_raw 23.1h**
  - recent raw age：**約 4.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**18/30 pass**
- TW-IC：**27/30 pass**
- TW 歷史：**#735=27/30，#734=27/30，#733=27/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 96.4%**
  - avg_quality：**0.6708**
  - avg_pnl：**+0.0208**
  - avg_drawdown_penalty：**0.0388**
- 判讀：近期 canonical path 仍是 supported extreme trend；這不是 live bull CAUTION lane 可部署的證據。

### Live predictor / bull blocker
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.6694**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.3900 (D)**
  - allowed layers：**0 → 0**
  - should trade：**false**
  - execution guardrail：**`decision_quality_below_trade_floor`**
  - chosen calibration scope：**`regime_label` / sample_size=203**
  - exact live lane（`bull|CAUTION|D`）：**26 rows / win_rate 0.5000 / quality 0.1985**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=9**
  - narrowed bull+D pathology：**156 rows / win_rate 0.1282 / quality -0.1578 / gate dominated by `bull|BLOCK`**
  - broader `regime_gate+entry_quality_label`：**2784 rows / dominant regime chop 97.4% / spillover not representative of bull live lane**
- `docs/analysis/bull_4h_pocket_ablation.md`
  - blocker_state：**`exact_live_bucket_proxy_ready_but_exact_missing`**
  - exact bucket root cause：**`exact_bucket_present_but_below_minimum`**
  - current bucket gap to minimum：**41**（9 / 50）
  - exact-bucket proxy：**52 rows / win_rate 0.9423**
  - exact live lane：**25~26 rows / win_rate 約 0.50 / quality 約 0.20**
  - broader same bucket：**10 rows / dominant regime = chop / win_rate 0.90 / quality 0.5732**
  - bucket comparison takeaway：**`prefer_same_bucket_proxy_over_cross_regime_spillover`**
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_only`**
  - train selected profile：**`core_plus_macro`**
  - dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
  - blocked candidate：**`core_plus_macro` 因 `under_minimum_exact_live_structure_bucket` 被降級**
  - support_governance_route：**`exact_live_bucket_present_but_below_minimum`**
- 判讀：本輪的關鍵改善不是「bull blocker 已解」，而是 **artifact / leaderboard / docs 終於一致承認：q35 exact bucket 已出現，但 9/50 仍不足支持，不能部署。**

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. live bull `CAUTION|q35` exact bucket 已出現，但仍是 under-minimum support（9 / 50）
**現象**
- live bucket：**`CAUTION|structure_quality_caution|q35`**
- exact rows：**9**；minimum support：**50**；gap：**41**
- exact live lane：**26 rows / win_rate 0.50 / quality 0.1985**
- exact bucket proxy：**52 rows / win_rate 0.9423**
- leaderboard 已把 `core_plus_macro` 標成 **`under_minimum_exact_live_structure_bucket`**

**判讀**
- 這不是 exact bucket 缺失，而是 **已出現但支持不足**；
- 目前可以用 proxy 做治理判讀，但**不能拿來解除 runtime blocker**。

**下一步方向**
- 下一輪直接追 `q35 exact bucket 9 → 50` 的 support 累積是否來自真實同 lane；
- 同時比對 exact 9 rows 與 proxy 52 rows 的 4H 結構差異，判定 proxy 是否過寬。

---

### P1. bull-only narrow pathology 仍顯著偏壞，runtime 必須維持 0 layers
**現象**
- `regime_label+entry_quality_label`：**156 rows / win_rate 0.1282 / quality -0.1578**
- dominated gate：**`bull|BLOCK` 74.4%**
- live probe 預期：**expected_win_rate 0.09 / expected_quality -0.1936 / layers 0**

**判讀**
- 即使 exact live lane 本身不算極差（26 rows, q≈0.20），bull-only 更寬的 D pocket 仍被 BLOCK 病灶主導。
- runtime guardrail 繼續把層數壓成 0 是正確行為。

**下一步方向**
- 下一輪優先對比 exact 9 rows 與同 regime wider 156 rows 的 gate-path / 4H 結構 shift，確認是 q35 bucket 邊界過寬，還是 bull D pocket 本身就不適合部署。

---

### P1. feature shrinkage 與 support-aware profile 仍分流：global `core_only`，bull-support-aware `core_plus_macro`
**現象**
- feature-group ablation global winner：**`core_only`**
- bull collapse-pocket best：**`core_plus_macro`**
- train selected profile：**`core_plus_macro`**（support-aware）
- leaderboard visible winner：**`core_only`**（under-minimum exact bucket blocker 已正確降級 support-aware candidate）

**判讀**
- 這是目前設計上的**刻意雙軌**：
  - global 縮減層面仍是 `core_only`；
  - bull live blocker 治理仍需 `core_plus_macro` 當 support-aware 研究候選；
  - 但 exact bucket 未達 minimum support 前，leaderboard / runtime 都不能把它包裝成 production winner。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1548)**

**判讀**
- 這仍是**外部憑證 blocker**，不是 bull lane 根因。

---

## 本輪已清掉的問題

### RESOLVED. leaderboard 會把 under-minimum exact bucket support-aware candidate 誤當成可選候選
**現象（修前）**
- `exact_live_bucket_rows > 0` 但 `< minimum_support_rows` 時，`backtesting/model_leaderboard.py` 不會套 blocker；
- 結果 probe 可以說「under-minimum」，但 leaderboard 仍可能把 support-aware candidate 排到第一，造成語義漂移。

**本輪 patch + 證據**
- `backtesting/model_leaderboard.py`
  - `_feature_profile_blocker_assessment()` 現在會把 `0 < exact_live_bucket_rows < minimum_support_rows` 標成 `under_minimum_exact_live_structure_bucket`
- `tests/test_model_leaderboard.py`
  - 新增 regression test 鎖住 under-minimum blocker
- 最新 heartbeat 證據：
  - `leaderboard_selected_profile = core_only`
  - `blocked_candidate_profiles[0].blocker_reason = under_minimum_exact_live_structure_bucket`

**狀態**
- **已修復**；目前 leaderboard / bull pocket artifact / docs 對 under-minimum exact bucket 的 blocker 語義已同步。

### RESOLVED. bull pocket artifact 先前缺少 exact lane / proxy / broader same-bucket 的 machine-readable 對照
**現象（修前）**
- 只能看到 gap / route，無法在同一份 artifact 直接讀出 q35 exact / proxy / broader same-bucket 的對照。

**本輪 patch + 證據**
- `scripts/bull_4h_pocket_ablation.py`
  - 新增 `bucket_evidence_comparison` 與 `bucket_comparison_takeaway`
- `scripts/hb_parallel_runner.py`
  - heartbeat summary 會同步持久化這組欄位
- `docs/analysis/bull_4h_pocket_ablation.md`
  - 新增 **Bucket evidence comparison** 表格

**狀態**
- **已修復**；下一輪 Step 0.5 可直接讀 artifact，不需重新手工比對。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 bull pocket exact / proxy / broader same-bucket 對照變成 machine-readable contract。** ✅
2. **修掉 leaderboard 對 under-minimum exact bucket 的語義漂移。** ✅
3. **重跑 fast heartbeat，確認最新 live blocker 已改成 `CAUTION|q35` under-minimum，而非舊的 q65 exact=0。** ✅

### 本輪不做
- 不放寬 live layers。
- 不把 proxy rows 當成 exact bucket 已支持。
- 不把 `fin_netflow` auth blocker 誤寫成模型問題。

---

## 下一輪 gate

- **Next focus:**
  1. 直接追 **`CAUTION|structure_quality_caution|q35` exact bucket 9 → 50** 的 support 累積與 bucket contract；
  2. 對比 **exact 9 rows / exact lane 26 rows / proxy 52 rows / broader same-bucket 10 rows** 的 4H 結構與 gate-path，判定 proxy 是否過寬；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q35 under-minimum exact bucket** 直接相關的 patch / artifact / verify；
  2. `support_pathology_summary.bucket_comparison_takeaway`、`leaderboard_feature_profile_probe.blocked_candidate_profiles[*].blocker_reason`、`live_predict_probe.allowed_layers` 對 blocker 的敘述零漂移；
  3. 若 exact bucket 仍 < 50，heartbeat 必須明確維持 blocker 語義，不得把 proxy / broader rows 寫成可部署。

- **Fallback if fail:**
  - 若 q35 exact rows 長期停在低位，下一輪優先懷疑 q35 bucket contract 過寬 / 過窄，而不是繼續等待自然累積；
  - 若 proxy 52 rows 與 exact 9 rows 的 4H 結構差異過大，優先縮窄 support-aware proxy cohort；
  - 若 `fin_netflow` auth 未修，持續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull bucket / support contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_735_summary.json`
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/live_predict_probe.json`
     - `data/leaderboard_feature_profile_probe.json`
  2. 逐條確認：
     - `support_pathology_summary.current_live_structure_bucket` 是否仍是 **`CAUTION|structure_quality_caution|q35`**；
     - `support_pathology_summary.current_live_structure_bucket_gap_to_minimum` 是否仍 **> 0**；
     - `support_pathology_summary.bucket_comparison_takeaway` 是否仍是 **`prefer_same_bucket_proxy_over_cross_regime_spillover`**；
     - `leaderboard_candidate_diagnostics.blocked_candidate_profiles[*].blocker_reason` 是否仍含 **`under_minimum_exact_live_structure_bucket`**；
     - `live_predict_probe.allowed_layers` 是否仍為 **0**。
  3. 若以上條件仍成立，下一輪不得再把「proxy 可用」當主題；必須直接推進 **q35 under-minimum exact bucket / proxy cohort 邊界 / bull-only pathology**。
