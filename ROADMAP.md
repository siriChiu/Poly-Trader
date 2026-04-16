# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 09:07 UTC_

只保留目前計畫，不保留歷史 roadmap。

---

## 已完成
- 已完成本輪 closed-loop diagnostics：
  - `python scripts/recent_drift_report.py`
  - `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
  - `python scripts/hb_q35_scaling_audit.py`
  - `python scripts/full_ic.py`
  - `python scripts/regime_aware_ic.py`
  - `python tests/comprehensive_test.py`
- 已確認本輪 canonical 基線：
  - 1440m canonical rows = **12709**
  - `simulated_pyramid_win = 0.6470`
  - Global IC = **17 / 30**
  - TW-IC = **26 / 30**
  - regime-aware IC = **Bear 5/8 / Bull 6/8 / Chop 4/8**
- 已完成本輪 real forward-progress patch：
  - `scripts/recent_drift_report.py` 補上 **4H bias50 provenance contract**
  - 當 `raw_close_price`、`raw_volatility`、`feat_4h_rsi14`、`feat_4h_bb_pct_b`、`feat_4h_macd_hist` 呈現 trend-stack coherence 時，`feat_4h_bias50` 會降級為 `coherent_4h_trend_compression`
  - `tests/test_recent_drift_report.py` 新增 `feat_4h_bias50` bull-pocket 壓縮回歸測試
  - `ARCHITECTURE.md` 新增 **4H bias50 provenance contract**
- 已完成驗證：
  - `python -m pytest tests/test_recent_drift_report.py -q` → **15 passed**
  - `python scripts/recent_drift_report.py`
  - `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
  - `python scripts/hb_q35_scaling_audit.py`
  - `python scripts/full_ic.py`
  - `python scripts/regime_aware_ic.py`
  - `python tests/comprehensive_test.py` → **6/6 PASS**
- 已刷新本輪 artifact：
  - `data/recent_drift_report.json`
  - `data/live_predict_probe.json`
  - `data/q35_scaling_audit.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
- 已確認 recent pathology 重新定位：
  - `feat_4h_bias50` 已從 unexpected compression 移出
  - `feat_4h_bias50.expected_compressed_reason = coherent_4h_trend_compression`
  - `feat_4h_dist_swing_low.expected_compressed_reason = coherent_4h_support_cluster_compression`
  - `feat_4h_dist_bb_lower.expected_compressed_reason = coherent_4h_band_floor_compression`
  - 新的 sibling-window `new_compressed` = **`feat_4h_bias20`**
- 已確認 current live blocker 已切換：
  - `bull / CAUTION / q15`
  - `entry_quality = 0.4326`
  - `entry_quality_label = D`
  - `allowed_layers = 0`
  - `deployment_blocker = under_minimum_exact_live_structure_bucket`
  - exact current q15 bucket rows = **4**
  - q35 scaling audit = **reference-only current bucket outside q35**

---

## 主目標

### 目標 A：把 recent bull pocket 主病灶收斂到 `feat_4h_bias20` root cause
重點：
- `feat_4h_bias50` 已被證明不是 isolated unexpected compression blocker
- current primary pathology 仍是 `recent 100 = 100x1 bull pocket`
- 下一輪必須直接追 `feat_4h_bias20` 為何在 sibling-window 對照下成為新的 `new_compressed`

### 目標 B：把 current live blocker 正式轉成 q15 exact support accumulation / replay
重點：
- current live row 已不在 q35，而是 `CAUTION|structure_quality_caution|q15`
- blocker 不是 q35 exact-scope=0，而是 **q15 exact bucket rows 只有 4，低於 deployment-grade minimum support**
- 下一輪若要處理 live blocker，應追 **q15 exact support accumulation / replay**，不是再重談 q35 bias50 formula review

### 目標 C：維持 q35 在 reference-only 層，避免搶走 current-live 主線
重點：
- q35 audit 仍有研究價值（`bias50_formula_may_be_too_harsh`）
- 但 current live row 不在 q35 lane
- 只有在 live path回到 q35 時，才重新升級 q35 scaling 為 current blocker

---

## 下一步
1. 下一輪先讀 `data/recent_drift_report.json`：
   - 確認 `feat_4h_bias50.expected_compressed_reason` 仍為 `coherent_4h_trend_compression`
   - 直接鎖定 `new_compressed=feat_4h_bias20`
2. 若 recent 100 仍為 `100x1 bull pocket`：
   - 直接做 `feat_4h_bias20` root-cause patch
   - 不可再把主病灶寫回 `feat_4h_bias50`、`feat_4h_macd_hist`、`feat_4h_dist_bb_lower`
3. 讀 `data/live_predict_probe.json`：
   - 確認 `current_live_structure_bucket` 是否仍為 q15
   - 確認 `current_live_structure_bucket_rows` 是否仍明顯低於 minimum support
   - 確認 `deployment_blocker` 是否仍為 `under_minimum_exact_live_structure_bucket`
4. 若要繼續處理 live blocker：
   - 只准追 q15 exact support accumulation / replay
   - 不可回到 q35 exact-lane 或 generic floor-gap 舊敘事
5. 只有在 A/B 主線清楚後，才回頭看 dual-role governance / source blockers

---

## 成功標準
- `data/recent_drift_report.json` 的 sibling-window `new_compressed` 不再是 `feat_4h_bias20`
- recent pathology 至少留下 1 個針對 `feat_4h_bias20` 的 root-cause patch + verify
- current live q15 bucket rows 明顯增加，或至少已有 q15 exact-support replay / accumulation patch 與對應驗證
- `deployment_blocker`、`allowed_layers`、`current_live_structure_bucket_rows`、`scope_applicability` 四者在 `ISSUES.md` / `ROADMAP.md` / `data/live_predict_probe.json` / `data/q35_scaling_audit.json` 語義一致
- `ISSUES.md` / `ROADMAP.md` / `ARCHITECTURE.md` / `data/recent_drift_report.json` 對 current blocker 語義一致

---

## Fallback if fail
- 若 recent pathology 仍無 patch：下一輪只能做 `feat_4h_bias20` root cause 修復，不再接受報告式心跳
- 若 q15 support accumulation / replay 仍未落地：維持為 P1 blocker，但不得再把問題重寫成 q35 或 generic floor-gap
- 若 current bucket / blocker 再切換：先重寫 current-state docs，再評估新 closure

---

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`
- `data/recent_drift_report.json`
- `data/live_predict_probe.json`
- `data/q35_scaling_audit.json`
- `data/full_ic_result.json`
- `data/ic_regime_analysis.json`

---

## Carry-forward input for next heartbeat
1. Step 0.5 先讀 `ISSUES.md` / `ROADMAP.md`，確認 `feat_4h_bias50` 已被改寫成 **expected compression**，不是 primary blocker。
2. 先讀最新 `data/recent_drift_report.json`：
   - `feat_4h_bias50.expected_compressed_reason` 是否仍為 `coherent_4h_trend_compression`
   - sibling-window `new_compressed` 是否仍為 `feat_4h_bias20`
   - recent 100 是否仍為 `100x1 bull pocket`
3. 再讀 `data/live_predict_probe.json`：
   - `current_live_structure_bucket` 是否仍為 q15
   - `current_live_structure_bucket_rows` 是否仍只有少量 exact support（目前 4）
   - `deployment_blocker` 是否仍為 `under_minimum_exact_live_structure_bucket`
4. 若 q15 support 仍不足，下一輪不得回退到 q35 敘事；若 recent pathology 仍在，必須直接留下 `feat_4h_bias20` patch。
