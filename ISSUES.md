# ISSUES.md — Current State Only

_最後更新：2026-04-14 17:22 UTC — Heartbeat #737（已新增 bull q35 exact/proxy/broader 邊界診斷 artifact，主 blocker 仍是 under-minimum support，而不是語義漂移）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#736）要求本輪處理
- **Next focus**：
  1. 直接比對 `CAUTION|structure_quality_caution|q35` 的 **exact 10 / exact lane 27 / proxy 53 / broader same-bucket 12**；
  2. 釐清 proxy cohort 是否過寬，或 bull D pocket 本身不適合部署；
  3. 持續把 `fin_netflow` 當外部 auth blocker 管理。
- **Success gate**：
  1. 必須留下至少一個與 q35 under-minimum exact bucket / proxy cohort 邊界直接相關的 patch / artifact / verify；
  2. blocker 語義在 artifact / probe / docs / summary 間零漂移；
  3. exact rows < 50 時不得包裝成可部署。
- **Fallback if fail**：
  - 若 q35 exact rows 繼續卡低位，優先縮窄 proxy cohort，而不是等待自然累積；
  - 若 proxy 與 exact 差異過大，優先把 support-aware train cohort 換成更窄代理集合；
  - `fin_netflow` auth 未修前持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - `scripts/bull_4h_pocket_ablation.py` 新增 `proxy_boundary_diagnostics`，把 **recent exact current bucket / recent exact live lane / historical exact-bucket proxy / recent broader same-bucket** 與相對 delta / verdict / reason 一次固化；
  - `scripts/hb_parallel_runner.py` 已把 `proxy_boundary_verdict / proxy_boundary_reason / proxy_boundary_diagnostics` 帶進 heartbeat summary；
  - `ARCHITECTURE.md` 已同步 `proxy-boundary diagnostics contract`。
- **本輪觀察導致前提更新**：
  - q35 exact current bucket 已從 **10 rows → 11 rows**；
  - exact live lane 已從 **27 rows → 28 rows**；
  - historical exact-bucket proxy 已從 **53 rows → 54 rows**；
  - broader same-bucket 已從 **12 rows → 13 rows**；
  - `proxy_boundary_verdict = proxy_boundary_inconclusive`：proxy 與 exact bucket 的差距尚未大到可直接判定為過寬，但仍不足以解除 blocker。
- **本輪明確不做**：
  - 不放寬 `allowed_layers=0`；
  - 不把 proxy 54 rows 當成 exact bucket 已被支持；
  - 不把 `fin_netflow` auth blocker 混入 bull q35 根因敘事。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/bull_4h_pocket_ablation.py`
    - 新增 `proxy_boundary_diagnostics`：
      - `recent_exact_current_bucket`
      - `recent_exact_live_lane`
      - `historical_exact_bucket_proxy`
      - `recent_broader_same_bucket`
      - `proxy_vs_current_live_bucket`
      - `exact_live_lane_vs_current_live_bucket`
      - `broader_same_bucket_vs_current_live_bucket`
      - `proxy_boundary_verdict / proxy_boundary_reason`
    - markdown artifact 新增 `Proxy boundary diagnostics` 區塊。
  - `scripts/hb_parallel_runner.py`
    - summary 現在同步持久化 `proxy_boundary_verdict / reason / diagnostics`，避免 heartbeat 報告與 bull pocket artifact 脫鉤。
  - `tests/test_bull_4h_pocket_ablation.py`
    - 新增 proxy-boundary verdict regression test。
  - `tests/test_hb_parallel_runner.py`
    - 新增 fast-heartbeat 摘要攜帶 proxy-boundary diagnostics 的 regression test。
  - `ARCHITECTURE.md`
    - 補上 `proxy-boundary diagnostics contract`。
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_parallel_runner.py tests/test_hb_leaderboard_candidate_probe.py -q` → **17 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/bull_4h_pocket_ablation.py` → artifact 重建成功
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 737` → **通過**

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #737：
  - Raw / Features / Labels：**21420 / 12849 / 42951**
  - 本輪增量：**+1 raw / +1 feature / +3 labels**
  - canonical target `simulated_pyramid_win`：**0.5754**
  - 240m labels：**21569 rows / target_rows 12647 / lag_vs_raw 3.2h**
  - 1440m labels：**12297 rows / target_rows 12297 / lag_vs_raw 23.4h**
  - recent raw age：**約 4.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**27/30 pass**
- TW 歷史：**#737=27/30，#736=27/30，#735=27/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 95.6%**
  - avg_quality：**0.6715**
  - avg_pnl：**+0.0209**
  - avg_drawdown_penalty：**0.0387**
- 判讀：近期 canonical path 仍是 supported extreme trend；它不是 bull q35 bucket 已可部署的證據。

### Live predictor / bull blocker
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.5604**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.3851 (D)**
  - allowed layers：**0 → 0**
  - should trade：**false**
  - execution guardrail：**`decision_quality_below_trade_floor`**
  - chosen calibration scope：**`regime_label` / sample_size=205**
  - exact live lane（`bull|CAUTION|D`）：**28 rows / win_rate 0.5357 / quality 0.2363**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=11 / win_rate 1.0000 / quality 0.6983**
  - broader `regime_gate+entry_quality_label` same bucket：**13 rows / win_rate 0.9231 / quality 0.6062**
  - broader scope dominant regime：**chop 97.0%**
- `data/bull_4h_pocket_ablation.json`
  - blocker_state：**`exact_lane_proxy_fallback_only`**
  - exact bucket root cause：**`exact_bucket_present_but_below_minimum`**
  - current bucket gap to minimum：**39**（11 / 50）
  - preferred support cohort：**`bull_live_exact_lane_bucket_proxy`**
  - historical exact-bucket proxy：**54 rows / win_rate 0.9444**
  - proxy boundary diagnostics：
    - recent exact current bucket：**11 rows / win_rate 1.0000**
    - recent exact live lane：**28 rows / win_rate 0.7500**
    - recent broader same-bucket：**13 rows / win_rate 0.9231 / dominant regime bull 84.6%**
    - proxy vs current-bucket win Δ：**-0.0556**
    - exact lane vs current-bucket win Δ：**-0.2500**
    - broader same-bucket vs current-bucket win Δ：**-0.0769**
    - `proxy_boundary_verdict`：**`proxy_boundary_inconclusive`**
    - `proxy_boundary_reason`：**proxy 與 exact bucket 差距尚未大到可直接判定，但也不足以解除 runtime blocker。**
  - bucket comparison takeaway：**`prefer_same_bucket_proxy_over_cross_regime_spillover`**
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_only`**
  - train selected profile：**`core_plus_macro`**
  - dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
  - blocked candidate：**`core_plus_macro` 因 `under_minimum_exact_live_structure_bucket` 被降級**
  - support_blocker_state：**`exact_lane_proxy_fallback_only`**
  - support_governance_route：**`exact_live_bucket_present_but_below_minimum`**
- 判讀：**語義對齊已經不是主題。** 本輪新的 machine-readable artifact 已把 q35 邊界比對固定下來；但 exact bucket 仍只有 11 rows，runtime blocker 必須繼續維持。

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. live bull `CAUTION|q35` exact bucket 仍是 under-minimum support（11 / 50）
**現象**
- live bucket：**`CAUTION|structure_quality_caution|q35`**
- exact current rows：**11**；minimum support：**50**；gap：**39**
- exact live lane：**28 rows / win_rate 0.5357 / quality 0.2363**
- historical exact-bucket proxy：**54 rows / win_rate 0.9444**
- broader same-bucket：**13 rows / win_rate 0.9231 / quality 0.6062**

**判讀**
- blocker 已完全收斂成 **support 不足**；
- exact bucket 已出現且 proxy/broader 都看起來不差，但這仍不足以解除 `allowed_layers=0`。

**下一步方向**
- 下一輪要把 `proxy_boundary_inconclusive` 進一步收斂成可執行結論：
  - 要嘛證明 proxy cohort 可接受但只差 support；
  - 要嘛證明 proxy 其實太寬，需進一步縮窄。

---

### P1. bull D exact lane 的壞 pocket 主要不在 current q35 bucket 內，而在同 lane 其他 bucket / wider lane
**現象**
- current q35 bucket：**11 rows / win_rate 1.0000 / quality 0.6983**
- exact live lane：**28 rows / win_rate 0.5357 / quality 0.2363**
- delta：**win_rate -0.2500 / quality -0.4620**

**判讀**
- current q35 bucket 本身近期表現明顯優於整個 bull `CAUTION|D` exact lane；
- 這代表現階段更像是 **same-lane 其他 bucket / wider lane 的 pathology 在拖累 exact lane**，而不只是 q35 自身失敗。

**下一步方向**
- 下一輪需把 exact lane 28 rows 再切成 q35 / q15 / base_caution_q15 / base_caution_q85 的 gate-path / 4H 結構對照，確認真正 toxic pocket 在哪一個子 bucket。

---

### P1. proxy cohort 邊界已可 machine-read，但 verdict 仍是 `proxy_boundary_inconclusive`
**現象**
- `proxy_vs_current_live_bucket.win_rate_delta = -0.0556`
- `broader_same_bucket_vs_current_live_bucket.win_rate_delta = -0.0769`
- `exact_live_lane_vs_current_live_bucket.win_rate_delta = -0.2500`
- `proxy_boundary_verdict = proxy_boundary_inconclusive`

**判讀**
- 現在已不是「沒有資料可比」，而是「已有邊界證據，但差距尚未大到足以直接做 proxy 縮窄決策」。

**下一步方向**
- 直接把 4H 結構均值差（尤其 `feat_4h_bias200 / feat_4h_dist_swing_low / feat_4h_dist_bb_lower / feat_4h_bb_pct_b`）轉成明確的 proxy 收斂規則或 rejection rule。

---

### P1. feature shrinkage 與 support-aware profile 仍分流：global `core_only`，bull-support-aware `core_plus_macro`
**現象**
- feature-group ablation global winner：**`core_only`**
- bull support-aware / train selected：**`core_plus_macro`**
- leaderboard visible winner：**`core_only`**
- blocked candidate：**`core_plus_macro` → `under_minimum_exact_live_structure_bucket`**

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
- archive_window_coverage：**0.0% (0/1550)**

**判讀**
- 這仍是**外部憑證 blocker**，不是 bull lane 根因。

---

## 本輪已清掉的問題

### RESOLVED. bull q35 exact/proxy/broader 邊界比較仍靠人工讀 markdown，heartbeat 無法 machine-read
**現象（修前）**
- artifact 雖然已有 `bucket_evidence_comparison`，但 heartbeat 無法直接判讀 exact current bucket / exact lane / proxy / broader same-bucket 的相對關係；
- 每輪都要人工重算「proxy 究竟是太寬，還是只是 support 還不夠」。

**本輪 patch + 證據**
- `scripts/bull_4h_pocket_ablation.py`
  - 新增 `proxy_boundary_diagnostics` 與 `proxy_boundary_verdict / reason`
- `scripts/hb_parallel_runner.py`
  - summary 已同步持久化上述欄位
- `tests/test_bull_4h_pocket_ablation.py`
  - 新增 proxy-boundary regression test
- `tests/test_hb_parallel_runner.py`
  - 新增 fast-summary regression test
- `ARCHITECTURE.md`
  - 新增 `proxy-boundary diagnostics contract`

**狀態**
- **已修復**；現在 heartbeat 能直接 machine-read q35 exact/proxy/broader 邊界，不必再只靠人工對照 markdown。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 q35 exact / exact lane / proxy / broader same-bucket 的邊界比較固化成 machine-readable artifact。** ✅
2. **讓 fast heartbeat summary 直接吃到 proxy-boundary verdict，而不是停在 bucket rows。** ✅
3. **重跑 fast heartbeat，確認 blocker 仍是 under-minimum support，且 live layers 仍維持 0。** ✅

### 本輪不做
- 不放寬 live layers。
- 不把 proxy 54 rows 當成 exact bucket 已支持。
- 不把 `fin_netflow` auth blocker 誤寫成模型問題。

---

## 下一輪 gate

- **Next focus:**
  1. 把 `proxy_boundary_inconclusive` 收斂成明確決策：為 q35 建立更窄 proxy 規則，或正式證明目前 proxy 可保留但只差 support；
  2. 直接拆解 exact lane 28 rows 內的 **q35 / q15 / base_caution_q15 / base_caution_q85**，找出真正拖累 bull `CAUTION|D` lane 的 toxic 子 bucket；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **proxy_boundary_inconclusive / exact lane 子 bucket 毒 pocket** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`allowed_layers` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 exact rows 仍 < 50，所有路徑同輪同步維持 blocker 結論，不得把 q35 寫成可部署。

- **Fallback if fail:**
  - 若 q35 exact rows 仍停在低位且 verdict 仍 inconclusive，下一輪優先做**更窄 proxy contract**，不要再等待自然累積；
  - 若 exact lane 內某個非-q35 子 bucket 明顯 toxic，下一輪把 blocker 升級成 **lane-internal bucket veto / rejection rule**；
  - 若 `fin_netflow` auth 未修，持續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull support / proxy contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_737_summary.json`
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/live_predict_probe.json`
     - `data/leaderboard_feature_profile_probe.json`
  2. 逐條確認：
     - `support_pathology_summary.current_live_structure_bucket` 是否仍是 **`CAUTION|structure_quality_caution|q35`**；
     - `support_pathology_summary.current_live_structure_bucket_gap_to_minimum` 是否仍 **> 0**；
     - `support_pathology_summary.proxy_boundary_verdict` 是否仍為 **`proxy_boundary_inconclusive`**；
     - `support_pathology_summary.proxy_boundary_diagnostics` 是否仍含 **recent_exact_current_bucket / recent_exact_live_lane / historical_exact_bucket_proxy / recent_broader_same_bucket**；
     - `leaderboard_candidate_diagnostics.blocked_candidate_profiles[*].blocker_reason` 是否仍含 **`under_minimum_exact_live_structure_bucket`**；
     - `live_predict_probe.allowed_layers` 是否仍為 **0**。
  3. 若以上條件仍成立，下一輪不得再把「邊界可讀了」當成功；必須直接推進 **proxy 收斂規則 / exact lane toxic 子 bucket / bull-only pathology**。
