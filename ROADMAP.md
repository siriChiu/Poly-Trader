# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 06:46 UTC_

只保留目前計畫，不保留歷史 roadmap。

---

## 已完成
- 已完成本輪 closed-loop diagnostics：
  - `python scripts/recent_drift_report.py`
  - `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
  - `python scripts/hb_q35_scaling_audit.py`
  - `python scripts/full_ic.py`
  - `python scripts/regime_aware_ic.py`
- 已確認本輪 canonical 基線：
  - 1440m canonical rows = **12709**
  - `simulated_pyramid_win = 0.6470`
  - Global IC = **17 / 30**
  - TW-IC = **26 / 30**
  - regime-aware IC = **Bear 5/8 / Bull 6/8 / Chop 4/8**
- 已完成本輪 real forward-progress patch：
  - `scripts/recent_drift_report.py` 修正 `feat_atr_pct` expected-compression provenance
  - 不再要求 `raw_volatility` proxy mean 必須同方向下降；只要 raw volatility dispersion 同步壓縮，就標記為 `underlying_raw_volatility_compression`
  - `tests/test_recent_drift_report.py` 新增 higher-mean / lower-dispersion regression case
- 已完成驗證：
  - `python -m pytest tests/test_recent_drift_report.py -q` → **10 passed**
  - `python -m pytest tests/test_api_feature_history_and_predictor.py -q` → **43 passed**
  - `python tests/comprehensive_test.py` → **6/6 PASS**
- 已刷新本輪 artifact：
  - `data/live_predict_probe.json`
  - `data/q35_scaling_audit.json`
  - `data/recent_drift_report.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
- 已確認 current live q35 狀態：
  - `bull / CAUTION / q35`
  - `entry_quality = 0.7047`
  - `entry_quality_label = B`
  - `q35_discriminative_redesign_applied = true`
  - `allowed_layers_raw = 2`
  - `allowed_layers = 1`
  - `deployment_blocker = null`
  - `current_live_structure_bucket_rows = 187`
  - `decision_quality_structure_bucket_support_mode = exact_bucket_supported_via_q35_runtime_redesign`
- 已確認 recent pathology 狀態：
  - recent 100 仍是 `100x1 bull pocket`
  - `feat_atr_pct` 已被降級為 expected compression
  - 新的 `new_compressed` = **`feat_4h_bias200`**

---

## 主目標

### 目標 A：把 recent bull pocket 主病灶收斂到 `feat_4h_bias200` root cause
重點：
- `feat_atr_pct` 已被證明不是 unexpected compression blocker
- current primary pathology 仍是 `recent 100 = 100x1 bull pocket`
- 下一輪必須直接追 `feat_4h_bias200` 為何在 sibling-window 對照下成為新的 `new_compressed`

### 目標 B：把 q35 runtime 成功，正式轉成 exact-lane historical replay / calibration 對齊
重點：
- q35 已不再是 support blocker，也不再是 floor-gap blocker
- runtime 已成功，但 exact `regime+gate+entry_quality_label` 歷史 rows 仍未回放
- 下一輪若要繼續處理 q35，應追 **historical replay / calibration alignment**，不是重談 support shortage

### 目標 C：維持 dual-role governance 在次要層，避免搶走主線焦點
重點：
- current live 已可 1-layer guarded deployment，當前不是 parity blocker
- 只有在 recent pathology 與 q35 replay 收斂後，才重新評估 dual-role governance 是否要升級

---

## 下一步
1. 下一輪先讀 `data/recent_drift_report.json`：確認 `feat_atr_pct.expected_compressed_reason` 仍為 `underlying_raw_volatility_compression`，並直接鎖定 `new_compressed=feat_4h_bias200`
2. 若 recent 100 仍為 `100x1 bull pocket`：
   - 直接做 `feat_4h_bias200` root-cause patch
   - 不可再把主病灶寫回 ATR 或 generic drift
3. 讀 `data/live_predict_probe.json`：
   - 確認 `deployment_blocker=null`
   - 確認 `current_live_structure_bucket_rows` 仍高於 0
   - 確認 `allowed_layers=1` 是 `decision_quality_label_C_caps_layers`，不是 support blocker
4. 若要繼續處理 q35：
   - 只准追 exact-lane historical replay / calibration alignment
   - 不可回到 unsupported / under-minimum / floor-gap 舊敘事
5. 只有在 A/B 主線清楚後，才回頭看 dual-role governance / source blockers

---

## 成功標準
- `data/recent_drift_report.json` 的 `new_compressed` 不再是 `feat_4h_bias200`
- recent pathology 至少留下 1 個 root-cause patch + verify
- q35 current live 維持 `deployment_blocker = null`，且文件不再把 q35 當作 support blocker
- 若 q35 replay 有做，`decision_quality_calibration_scope` 或 exact-lane rows 必須更接近 runtime semantics
- `ISSUES.md` / `ROADMAP.md` / `data/live_predict_probe.json` / `data/recent_drift_report.json` 對 current blocker 語義一致

---

## Fallback if fail
- 若 recent pathology 仍無 patch：下一輪只能做 `feat_4h_bias200` root cause 修復，不再接受報告式心跳
- 若 q35 replay 仍未落地：維持為 P1 governance debt，但不得再把 q35 重寫成 deployment blocker
- 若 current bucket / gate / runtime path 切換：先重寫 current-state docs，再評估新 closure

---

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `data/live_predict_probe.json`
- `data/q35_scaling_audit.json`
- `data/recent_drift_report.json`
- `data/full_ic_result.json`
- `data/ic_regime_analysis.json`
- `ARCHITECTURE.md`（只有在新增新的 drift / q35 contract 時才更新）

---

## Carry-forward input for next heartbeat
1. Step 0.5 先讀 `ISSUES.md` / `ROADMAP.md`，確認 q35 已被改寫成 **runtime success + replay debt**，不是 support blocker。
2. 先讀最新 `data/live_predict_probe.json`：
   - `deployment_blocker` 是否仍為 `null`
   - `current_live_structure_bucket_rows` 是否仍維持高支撐
   - `allowed_layers` 是否仍由 `decision_quality_label_C_caps_layers` 控制
   - `q35_discriminative_redesign_applied` 是否仍為 `true`
3. 再讀 `data/recent_drift_report.json`：
   - `feat_atr_pct.expected_compressed_reason` 是否仍為 `underlying_raw_volatility_compression`
   - `new_compressed` 是否仍為 `feat_4h_bias200`
   - recent 100 是否仍為 `100x1 bull pocket`
4. 若 q35 runtime 仍健康，下一輪不得回退到 unsupported / floor-gap 敘事；若 recent pathology 仍在，必須直接留下 `feat_4h_bias200` patch。
