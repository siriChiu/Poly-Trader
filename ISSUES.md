# ISSUES.md — Current State Only

_最後更新：2026-04-14 17:49 UTC — Heartbeat #738（已把 bull exact lane 內部子 bucket 機器可讀化；主 blocker 仍是 q35 exact bucket support 不足，但現在已能明確指出 toxic 子 bucket 在 q15，而不是 current q35 本身）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#737）要求本輪處理
- **Next focus**：
  1. 把 `proxy_boundary_inconclusive` 收斂成明確決策：縮窄 proxy 或確認 proxy 可保留但仍 blocked；
  2. 拆解 exact lane 28 rows 的 `q35 / q15 / base_caution_q15 / base_caution_q85`，找出真正 toxic 子 bucket；
  3. 持續把 `fin_netflow` 當外部 source blocker 管理。
- **Success gate**：
  1. 必須留下至少一個與 `proxy_boundary_inconclusive / exact-lane toxic 子 bucket` 直接相關的 patch / artifact / verify；
  2. `support_blocker_state / support_governance_route / exact_bucket_root_cause / proxy_boundary_verdict / allowed_layers` 在 artifact / probe / docs / summary 間零漂移；
  3. exact rows < 50 時不得把 q35 寫成可部署。
- **Fallback if fail**：
  - 若 q35 exact rows 持續卡低位且 verdict 仍 inconclusive，優先做更窄 proxy contract；
  - 若 exact lane 內有明顯 toxic 子 bucket，升級成 lane-internal veto / rejection rule；
  - `fin_netflow` auth 未修前持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - `scripts/bull_4h_pocket_ablation.py` 新增 `exact_lane_bucket_diagnostics = {buckets, toxic_bucket, verdict, reason}`，把 bull exact lane 內的 `q35 / q15 / base_caution_q15 / base_caution_q85` 直接 machine-read 化；
  - `scripts/hb_parallel_runner.py` summary 已同步攜帶 `exact_lane_bucket_verdict / exact_lane_toxic_bucket / exact_lane_bucket_diagnostics`；
  - `tests/test_bull_4h_pocket_ablation.py`、`tests/test_hb_parallel_runner.py` 已補 regression；
  - `ARCHITECTURE.md` 已同步 exact-lane toxic sub-bucket contract。
- **本輪觀察導致前提更新**：
  - live exact lane 已從 **28 rows → 30 rows**；
  - current q35 exact bucket 已從 **11 rows → 13 rows**；
  - historical exact-bucket proxy 已從 **54 rows → 56 rows**；
  - broader same-bucket 已從 **13 rows → 15 rows**；
  - 新 artifact 明確指出 `exact_lane_bucket_verdict = toxic_sub_bucket_identified`，最差子 bucket 是 **`CAUTION|structure_quality_caution|q15`（4 rows / win_rate 0.0000）**；
  - `proxy_boundary_verdict` 仍是 **`proxy_boundary_inconclusive`**，表示 proxy 尚不能直接收斂成「過寬」或「可完全接受」。
- **本輪明確不做**：
  - 不放寬 `allowed_layers=0`；
  - 不把 proxy 56 rows 當成 q35 exact bucket 已獲支持；
  - 不把 `fin_netflow` auth blocker 混入 bull lane 根因敘事；
  - 不把 current q35 bucket 當成主要毒 pocket（本輪證據顯示真正更差的是 q15 子 bucket）。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/bull_4h_pocket_ablation.py`
    - 新增 `exact_lane_bucket_diagnostics`；
    - 新增 `support_pathology_summary.exact_lane_bucket_verdict / exact_lane_bucket_reason / exact_lane_toxic_bucket`；
    - markdown artifact 新增 `Exact lane sub-bucket diagnostics` 區塊。
  - `scripts/hb_parallel_runner.py`
    - summary 現在同步持久化 exact-lane toxic 子 bucket 診斷。
  - `tests/test_bull_4h_pocket_ablation.py`
    - 新增 toxic sub-bucket regression test。
  - `tests/test_hb_parallel_runner.py`
    - 新增 fast-summary 攜帶 exact-lane 子 bucket 診斷的 regression test。
  - `ARCHITECTURE.md`
    - 補上 `exact-lane toxic sub-bucket contract`。
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_parallel_runner.py -q` → **15 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/bull_4h_pocket_ablation.py` → artifact 重建成功
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 738` → **通過**

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #738：
  - Raw / Features / Labels：**21421 / 12850 / 42954**
  - 本輪增量：**+1 raw / +1 feature / +3 labels**
  - canonical target `simulated_pyramid_win`：**0.5755**
  - 240m labels：**21570 rows / target_rows 12648 / lag_vs_raw 3.2h**
  - 1440m labels：**12299 rows / target_rows 12299 / lag_vs_raw 23.2h**
  - recent raw age：**約 4.4 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**27/30 pass**
- TW 歷史：**#738=27/30，#737=27/30，#736=27/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 94.8%**
  - avg_quality：**0.6723**
  - avg_pnl：**+0.0209**
  - avg_drawdown_penalty：**0.0383**
- 判讀：近期 canonical path 仍是 supported extreme trend；它不是 bull q35 bucket 已可部署的證據。

### Live predictor / bull blocker
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.3044**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.3801 (D)**
  - allowed layers：**0 → 0**
  - should trade：**false**
  - execution guardrail：**`decision_quality_below_trade_floor`**
  - chosen calibration scope：**`regime_label+regime_gate+entry_quality_label` / sample_size=30**
  - exact live lane（`bull|CAUTION|D`）：**30 rows / win_rate 0.5667 / quality 0.2694**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=13 / win_rate 1.0000 / quality 0.7036**
  - broader same-bucket：**15 rows / win_rate 0.9333 / quality 0.6231 / dominant regime chop 96.6%**
- `data/bull_4h_pocket_ablation.json`
  - blocker_state：**`exact_lane_proxy_fallback_only`**
  - exact bucket root cause：**`exact_bucket_present_but_below_minimum`**
  - current bucket gap to minimum：**37**（13 / 50）
  - preferred support cohort：**`bull_live_exact_lane_bucket_proxy`**
  - historical exact-bucket proxy：**56 rows / win_rate 0.9464**
  - `proxy_boundary_verdict`：**`proxy_boundary_inconclusive`**
  - `exact_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
  - toxic 子 bucket：**`CAUTION|structure_quality_caution|q15`（4 rows / win_rate 0.0000）**
  - lane 內其他子 bucket：
    - `CAUTION|base_caution_regime_or_bias|q15`：**7 rows / win_rate 0.5714**
    - `CAUTION|base_caution_regime_or_bias|q85`：**6 rows / win_rate 0.8333**
  - current q35 與 toxic q15 的差距：**win_rate Δ = -1.0000**
  - bucket comparison takeaway：**`prefer_same_bucket_proxy_over_cross_regime_spillover`**
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_only`**
  - train selected profile：**`core_plus_macro`**
  - dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
  - blocked candidate：**`core_plus_macro` 因 `under_minimum_exact_live_structure_bucket` 被降級**
- 判讀：**本輪已把「exact lane 到底是哪個 bucket 在拖累」收斂成機器可讀證據。** 目前 q35 current bucket 本身不差；拖累 exact lane 的主 pocket 在 `CAUTION|structure_quality_caution|q15`。

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. live bull `CAUTION|q35` exact bucket 仍是 under-minimum support（13 / 50）
**現象**
- live bucket：**`CAUTION|structure_quality_caution|q35`**
- exact current rows：**13**；minimum support：**50**；gap：**37**
- exact live lane：**30 rows / win_rate 0.5667 / quality 0.2694**
- historical exact-bucket proxy：**56 rows / win_rate 0.9464**

**判讀**
- blocker 仍然是 **support 不足**；
- current q35 bucket 已有 13 rows 且表現好，但還不能解除 runtime blocker。

**下一步方向**
- 先維持 `allowed_layers=0`；
- 下一輪重點不是再證明 q35 好不好，而是把 q15 toxic pocket 轉成 runtime / governance 規則。

---

### P1. bull exact lane 的主要毒 pocket 已收斂到 `CAUTION|structure_quality_caution|q15`
**現象**
- current q35：**13 rows / win_rate 1.0000 / quality 0.7036**
- toxic q15：**4 rows / win_rate 0.0000**
- q15 vs q35：**win_rate Δ = -1.0000**
- base_caution_q15：**7 rows / win_rate 0.5714**
- base_caution_q85：**6 rows / win_rate 0.8333**

**判讀**
- exact lane 30 rows 被拉低，主要不是 current q35 本身失敗；
- 最差的是 **同為 structure_quality_caution 分支的 q15 子 bucket**；
- 這已達到「lane-internal pathology」等級，不應再只把整條 exact lane 視為單一 bucket。

**下一步方向**
- 把 q15 toxic pocket 升級成 machine-readable veto / rejection rule 候選；
- 驗證這條規則是否只擋 q15，而不誤傷 q35 current bucket。

---

### P1. proxy cohort 邊界仍未收斂，verdict 仍是 `proxy_boundary_inconclusive`
**現象**
- recent exact current bucket：**13 rows / win_rate 1.0000**
- historical exact-bucket proxy：**56 rows / win_rate 0.9464**
- broader same-bucket：**15 rows / win_rate 0.9333 / dominant regime chop 96.6%**
- `proxy_vs_current_live_bucket.win_rate_delta = -0.0536`
- `proxy_boundary_verdict = proxy_boundary_inconclusive`

**判讀**
- proxy 與 exact current bucket 的差距不大，但 evidence 仍不足以直接宣告「proxy 完全可用」；
- 目前比較像：**proxy 可作治理參考，但 exact support 未滿前仍不得部署**。

**下一步方向**
- 把 proxy 規則與 q15 toxic pocket 分開治理；
- 先做 q15 veto / rejection rule，再決定 proxy 是否還需要進一步縮窄。

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
  - bull blocker 研究仍需 `core_plus_macro`；
  - exact bucket 未達 minimum support 前，leaderboard / runtime 都不能把 support-aware profile 包裝成 production winner。

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

### RESOLVED. exact lane 仍是黑盒，heartbeat 無法 machine-read 到底哪個子 bucket 在拖累 bull `CAUTION|D`
**現象（修前）**
- 即使 probe 已有 `recent500_structure_bucket_counts`，heartbeat 仍看不到 q35 / q15 / base_caution_q15 / base_caution_q85 的逐 bucket target 差異；
- 每輪只能重複說 exact lane 30 rows 不夠好，但無法機器化指出真正 toxic pocket。

**本輪 patch + 證據**
- `scripts/bull_4h_pocket_ablation.py`
  - 新增 `exact_lane_bucket_diagnostics`；
  - 新增 `exact_lane_bucket_verdict / reason / toxic_bucket`。
- `scripts/hb_parallel_runner.py`
  - summary 已同步持久化上述欄位。
- `tests/test_bull_4h_pocket_ablation.py`
  - 新增 toxic sub-bucket regression test。
- `tests/test_hb_parallel_runner.py`
  - 新增 fast-summary regression test。
- `ARCHITECTURE.md`
  - 已同步 contract。

**狀態**
- **已修復**；現在 heartbeat 能直接 machine-read：「bull exact lane 的主 toxic pocket 是 `CAUTION|structure_quality_caution|q15`，不是 current q35 bucket 本身。」

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 exact lane 內部子 bucket 直接 machine-read 化，找出真正 toxic pocket。** ✅
2. **讓 fast heartbeat summary 直接攜帶 toxic sub-bucket evidence，而不是只剩 exact lane rows。** ✅
3. **重跑 fast heartbeat，確認 blocker 仍是 under-minimum support，且 q15 才是 lane-internal pathology。** ✅

### 本輪不做
- 不放寬 live layers。
- 不把 proxy 56 rows 當成 q35 exact bucket 已支持。
- 不把 `fin_netflow` auth blocker 誤寫成 bull lane 問題。
- 不把 q35 current bucket 誤判為 toxic pocket。

---

## 下一輪 gate

- **Next focus:**
  1. 把 `CAUTION|structure_quality_caution|q15` toxic pocket 升級成 machine-readable veto / rejection rule 候選，並驗證它只擋壞 pocket、不誤傷 current q35；
  2. 重新檢查 `proxy_boundary_inconclusive`：若 q15 veto 生效後 blocker 仍只剩 support 不足，則正式固定成「proxy 可保留但 exact 未滿前仍 blocked」；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q15 toxic pocket veto / proxy boundary 定稿** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`exact_lane_bucket_verdict`、`allowed_layers` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 q35 exact rows 仍 < 50，所有路徑同輪同步維持 blocker 結論，不得把 q35 寫成可部署。

- **Fallback if fail:**
  - 若 q15 veto 還不能穩定區分壞 pocket，下一輪至少把 `q15 / q35` 差異轉成更窄 proxy contract；
  - 若 q35 exact rows 仍停在低位，繼續維持 `allowed_layers=0`，不要因 current bucket 短期漂亮而放寬；
  - 若 `fin_netflow` auth 未修，持續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull veto / proxy contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_738_summary.json`
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/live_predict_probe.json`
     - `data/leaderboard_feature_profile_probe.json`
  2. 逐條確認：
     - `support_pathology_summary.current_live_structure_bucket` 是否仍是 **`CAUTION|structure_quality_caution|q35`**；
     - `support_pathology_summary.current_live_structure_bucket_gap_to_minimum` 是否仍 **> 0**；
     - `support_pathology_summary.proxy_boundary_verdict` 是否仍為 **`proxy_boundary_inconclusive`**；
     - `support_pathology_summary.exact_lane_bucket_verdict` 是否仍為 **`toxic_sub_bucket_identified`**；
     - `support_pathology_summary.exact_lane_toxic_bucket.bucket` 是否仍是 **`CAUTION|structure_quality_caution|q15`**；
     - `leaderboard_candidate_diagnostics.blocked_candidate_profiles[*].blocker_reason` 是否仍含 **`under_minimum_exact_live_structure_bucket`**；
     - `live_predict_probe.allowed_layers` 是否仍為 **0**。
  3. 若以上條件仍成立，下一輪不得再把「已找到 toxic pocket」當成功；必須直接推進 **q15 veto / proxy 定稿 / runtime guardrail 對齊**。
