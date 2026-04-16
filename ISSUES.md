# ISSUES.md — Current State Only

_最後更新：2026-04-16 06:46 UTC_

只保留目前仍有效的問題；不保留歷史敘事。

---

## Step 0.5 承接（把上輪結論當本輪輸入）
- 上輪 carry-forward 主軸：`q35 exact support accumulation`、`feat_atr_pct recent-window unexpected compression root cause`、`dual-role governance only after q35 support state is stable`。
- 本輪逐條對照結果：
  1. **q35 support accumulation 已不再是主 blocker**：`data/live_predict_probe.json` 顯示 current live 仍在 `bull / CAUTION / q35`，但 `q35_discriminative_redesign_applied=true`、`entry_quality=0.7047 (B)`、`allowed_layers_raw=2`、`current_live_structure_bucket_rows=187`，且 `deployment_blocker=null`。舊敘事 `unsupported/under-minimum exact support` 已失效。
  2. **`feat_atr_pct` 已從 unexpected compression 降級為 expected compression**：本輪修補 `scripts/recent_drift_report.py` 的 provenance 判讀後，recent drift 會把 `feat_atr_pct` 正確標成 `underlying_raw_volatility_compression`，不再把它列為 `new_compressed` 主病灶。
  3. **recent pathology 還沒解**：recent 100 仍是 `100x1 bull pocket`，主要漂移視窗仍是 `distribution_pathology`；只是新的 sibling-window 主病灶已從 `feat_atr_pct` 改成 **`feat_4h_bias200`**。
  4. **dual-role governance 仍不是本輪主 blocker**：q35 runtime 已可部署到 1 layer guardrail，現階段更該追 recent canonical pathology 與 bull pocket 的結構壓縮根因。

---

## 系統現況
- 本輪最新 DB：**Raw / Features / Labels = 30522 / 16155 / 43750**
- 最新時間：
  - Raw：`2026-04-16 06:27:57.203823`
  - Features：`2026-04-16 06:27:57.203823`
  - Labels：`2026-04-16 01:43:50.141947`
  - Canonical 1440m labels：`2026-04-15 05:53:35.506756`
- canonical 1440m：**12709 rows / simulated_pyramid_win = 0.6470**
- 全域 IC：**17 / 30 pass**
- TW-IC：**26 / 30 pass**
- regime-aware IC：**Bear 5/8、Bull 6/8、Chop 4/8**
- current live probe：
  - regime / gate / bucket：**bull / CAUTION / q35**
  - `entry_quality = 0.7047`
  - `entry_quality_label = B`
  - `q35_discriminative_redesign_applied = true`
  - `allowed_layers_raw = 2`
  - `allowed_layers = 1`
  - `execution_guardrail_reason = decision_quality_label_C_caps_layers`
  - `deployment_blocker = null`
  - `current_live_structure_bucket_rows = 187`
  - `decision_quality_calibration_scope = regime_label`
  - `decision_quality_structure_bucket_support_mode = exact_bucket_supported_via_q35_runtime_redesign`
  - `decision_quality_label = C`
- q35 scaling audit：
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`
  - `deployment_grade_component_experiment.verdict = runtime_patch_crosses_trade_floor`
  - `runtime_entry_quality = 0.7047`
  - `runtime_remaining_gap_to_floor = -0.1547`
- recent drift primary window：**100**
  - alerts = `constant_target`, `regime_concentration`, `regime_shift`
  - interpretation = `distribution_pathology`
  - `wins = 100 / losses = 0`
  - `dominant_regime = bull (100%)`
  - `expected_compressed_count = 1`
  - `feat_atr_pct.expected_compressed_reason = underlying_raw_volatility_compression`
  - `new_compressed = feat_4h_bias200`
- latest saved training artifact（**本輪未重訓，只引用既有 artifact**）：
  - `feature_profile = core_plus_macro`
  - `train_accuracy = 0.6457`
  - `cv_accuracy = 0.6978 ± 0.1161`
  - `trained_at = 2026-04-15T23:35:43.653238`

---

## Step 1 事實分類

### 已改善
1. **q35 runtime path 已真正跨過 trade floor**：current live `entry_quality=0.7047`、`allowed_layers_raw=2`，不再是 floor-gap blocker。
2. **假性 support blocker 已解除**：`current_live_structure_bucket_rows=187`、`decision_quality_structure_bucket_support_mode=exact_bucket_supported_via_q35_runtime_redesign`、`deployment_blocker=null`。
3. **`feat_atr_pct` provenance 已修正**：recent drift 會把 ATR 壓縮歸因到 `raw_volatility` 壓縮，不再把它算成 unexpected compression。
4. **驗證完整通過**：
   - `pytest tests/test_recent_drift_report.py -q` → **10 passed**
   - `pytest tests/test_api_feature_history_and_predictor.py -q` → **43 passed**
   - `python tests/comprehensive_test.py` → **6/6 PASS**

### 惡化
1. **recent canonical pathology 仍原地持續**：recent 100 仍是 `100x1 bull pocket`，distribution pathology 尚未收斂。
2. **主病灶已移位到 `feat_4h_bias200`**：`feat_atr_pct` 清掉後，sibling-window 的 `new_compressed` 現在改成 `feat_4h_bias200`，代表真正的 bull pocket root cause 還在後面。

### 卡住不動
1. **decision-quality calibration 仍未回放到 exact live lane 歷史 rows**：雖然 runtime 已有 support override，`decision_quality_calibration_scope` 仍回退在 `regime_label`，exact scope rows 仍是 0。
2. **dual-role governance 仍待後排**：當前沒有 deployment blocker，優先級仍低於 recent pathology root cause。
3. **source-level blockers 未本輪處理**：本輪沒有處理 sparse-source auth / archive 類 blocker。

---

## Open Issues

### P0. recent canonical pathology 仍持續；`feat_4h_bias200` 成為新的 unexpected compression 主病灶
**現象**
- recent 100 rows：`wins=100 / losses=0`
- `dominant_regime = bull (100%)`
- alerts = `constant_target`, `regime_concentration`, `regime_shift`
- sibling-window 對照後的 `new_compressed = feat_4h_bias200`

**影響**
- 這會持續污染 recent calibration、bull pocket 解讀與後續 deployment 信心。
- `feat_atr_pct` 已被證明不是主病灶，因此若下輪仍只追 ATR，會浪費心跳。

**本輪 patch / 證據**
- `scripts/recent_drift_report.py`：移除 ATR expected-compression 對 proxy mean 方向的錯誤 gating，改成只要 `raw_volatility` dispersion 同步壓縮就視為 expected compression。
- `tests/test_recent_drift_report.py`：新增「raw volatility 均值上升但 dispersion 崩縮」回歸測試。
- 驗證：
  - `python -m pytest tests/test_recent_drift_report.py -q` → **10 passed**
  - `python scripts/recent_drift_report.py`
- 證據：
  - `expected_compressed_count = 1`
  - `feat_atr_pct.expected_compressed_reason = underlying_raw_volatility_compression`
  - `new_compressed` 已改為 **`feat_4h_bias200`**

**下一步**
- 直接追 `feat_4h_bias200` 為何在 bull pocket recent window 被壓縮，並確認這是 market-state 真收斂還是 4H 特徵生成/校準問題。

### P1. q35 runtime 已可部署，但 exact live lane 的歷史 calibration rows 尚未回放
**現象**
- live predictor：`q35_discriminative_redesign_applied=true`
- `current_live_structure_bucket_rows = 187`
- `deployment_blocker = null`
- 但 `decision_quality_calibration_scope = regime_label`
- exact `regime_label+regime_gate+entry_quality_label` scope rows 仍是 **0**

**影響**
- runtime 已健康，但歷史 calibration surface 仍靠 support override，而不是 exact-lane row replay。
- 這不是 deployment blocker，但仍是治理 / artifact 對齊債務。

**本輪證據**
- `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
- `python scripts/hb_q35_scaling_audit.py`
- probe 已明確顯示：
  - `entry_quality = 0.7047`
  - `allowed_layers_raw = 2`
  - `allowed_layers = 1`
  - `deployment_blocker = null`
  - `decision_quality_structure_bucket_support_mode = exact_bucket_supported_via_q35_runtime_redesign`

**下一步**
- 若要讓 calibration surface 與 runtime 完全一致，下一輪應追 exact-lane 歷史 replay / label replay，而不是再把主 blocker寫回 support 不足。

### P2. dual-role governance / source blockers 仍在後排
**現象**
- 本輪沒有新的 dual-role parity failure。
- sparse-source / auth / archive 問題也未在本輪主線處理。

**下一步**
- 只有在 recent pathology 與 q35 exact-lane replay 收斂後，才重新升級這些治理題。

---

## Not Issues
- **q35 still blocked by unsupported/under-minimum exact support**：不是。current live 已 `deployment_blocker=null`，support rows = **187**。
- **`feat_atr_pct` 還是 unexpected compression**：不是。本輪已證明它是 `underlying_raw_volatility_compression`。
- **q35 runtime redesign 仍只是 audit preview**：不是。live predictor 已輸出 `q35_discriminative_redesign_applied=true`。
- **本輪需要先處理 dual-role governance**：不是。主 blocker 已轉成 recent pathology / bull pocket drift。

---

## Current Priority
1. **recent 100 bull pocket root cause：直接追 `feat_4h_bias200` unexpected compression**
2. **q35 exact-lane historical replay / calibration 對齊（非 blocker，但需治理收斂）**
3. **最後才處理 dual-role governance 與 source-level blockers**

---

## Next Gate Input
- **Next focus**：`feat_4h_bias200 recent-window unexpected compression root cause`, `q35 exact-lane historical replay`, `dual-role governance only after recent pathology and q35 replay are clear`
- **Success gate**：
  - recent drift 的 `new_compressed` 不再是 `feat_4h_bias200`
  - recent 100 bull pocket 至少留下 1 個 root-cause patch + verify
  - q35 calibration surface 若仍 fallback，需留下 exact-lane replay patch；若未做，至少不能再把 q35 寫成 deployment blocker
  - `ISSUES.md` / `ROADMAP.md` / `data/live_predict_probe.json` / `data/recent_drift_report.json` 對 blocker 與 pathology 語義一致
- **Fallback if fail**：
  - 若 recent pathology 仍無 patch，下輪只能做 `feat_4h_bias200` root cause 修復
  - 若 q35 exact-lane replay 仍沒做，明確維持為 P1 governance debt，不得重寫成 support blocker
  - 若 current live bucket 切換，先重寫 current-state docs 再談 closure
- **Carry-forward input for next heartbeat**：
  1. 先讀最新 `data/live_predict_probe.json`，確認 `deployment_blocker` 是否仍為 `null`、`current_live_structure_bucket_rows` 是否仍遠高於 0、`allowed_layers` 是否仍被 `decision_quality_label_C_caps_layers` 控制。
  2. 再讀 `data/recent_drift_report.json`，確認 `feat_atr_pct.expected_compressed_reason=underlying_raw_volatility_compression` 是否仍成立，以及 `new_compressed` 是否仍是 `feat_4h_bias200`。
  3. 若 q35 runtime 仍是 `entry_quality >= 0.55` 且 `q35_discriminative_redesign_applied=true`，不得再把 q35 主題寫回 unsupported / floor-gap 舊敘事。
  4. 若 recent pathology 仍是 `100x1 bull pocket`，下一輪必須直接留下 `feat_4h_bias200` root-cause patch，不可只重跑 drift report。
