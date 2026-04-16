# ISSUES.md — Current State Only

_最後更新：2026-04-16 09:07 UTC_

只保留目前仍有效的問題；不保留歷史敘事。

---

## Step 0.5 承接（把上輪結論當本輪輸入）
- 上輪 carry-forward 主軸：`feat_4h_macd_hist recent-window unexpected compression root cause`、`q35 exact-lane historical replay / support accumulation`、`dual-role governance only after recent pathology and q35 replay are clear`。
- 本輪逐條對照結果：
  1. **`feat_4h_macd_hist` 已不再是 primary blocker**：本輪在 `scripts/recent_drift_report.py` 補上 **4H bias50 provenance contract**，確認 `raw_close_price`、`raw_volatility`、`feat_4h_rsi14`、`feat_4h_bb_pct_b`、`feat_4h_macd_hist` 同步收斂時，`feat_4h_bias50` 會降級為 `coherent_4h_trend_compression`，不再被誤列為單點 4H 投影失真。完成後，sibling-window `new_compressed` 已從 `feat_4h_bias50` 前移到 **`feat_4h_bias20`**。
  2. **current live blocker 已不再是 q35 exact-lane**：`hb_predict_probe.py` 顯示 current live row 已落到 **`CAUTION|structure_quality_caution|q15`**，exact current-bucket rows = **4**，目前 blocker 是 **`under_minimum_exact_live_structure_bucket`**，不是前一輪的 q35 exact-scope=0 敘事。
  3. **q35 audit 退回 reference-only**：`hb_q35_scaling_audit.py` 明確標記 `scope_applicability = reference_only_current_bucket_outside_q35`；q35 仍可作 formula / calibration 參考，但本輪不可再把它寫成 current-live 主 blocker。
  4. **dual-role governance 仍不是本輪主線**：live blocker 已轉成 q15 support accumulation + `feat_4h_bias20` recent pathology，優先級仍高於 leaderboard / dual-profile 類治理。

---

## 系統現況
- 本輪最新 DB：**Raw / Features / Labels = 30524 / 16750 / 43750**
- 最新時間：
  - Raw：`2026-04-16 08:35:24.573669`
  - Features：`2026-04-16 08:35:24.573669`
  - Labels：`2026-04-16 01:43:50.141947`
  - Canonical 1440m labels：`2026-04-15 05:53:35.506756`
- canonical 1440m：**12709 rows / simulated_pyramid_win = 0.6470**
- 全域 IC：**17 / 30 pass**
- TW-IC：**26 / 30 pass**
- regime-aware IC：**Bear 5/8、Bull 6/8、Chop 4/8**
- recent drift primary window：**100**
  - alerts = `constant_target`, `regime_concentration`, `regime_shift`
  - interpretation = `distribution_pathology`
  - `wins = 100 / losses = 0`
  - `dominant_regime = bull (100%)`
  - `expected_compressed_count = 6`
  - `feat_atr_pct.expected_compressed_reason = underlying_raw_volatility_compression`
  - `feat_4h_bias50.expected_compressed_reason = coherent_4h_trend_compression`
  - `feat_4h_bias200.expected_compressed_reason = underlying_price_and_volatility_compression`
  - `feat_4h_dist_swing_low.expected_compressed_reason = coherent_4h_support_cluster_compression`
  - `feat_4h_dist_bb_lower.expected_compressed_reason = coherent_4h_band_floor_compression`
  - sibling-window `new_compressed = feat_4h_bias20`
- current live probe：
  - regime / gate / bucket：**bull / CAUTION / q15**
  - `entry_quality = 0.4326`
  - `entry_quality_label = D`
  - `allowed_layers_raw = 0`
  - `allowed_layers = 0`
  - `deployment_blocker = under_minimum_exact_live_structure_bucket`
  - `decision_quality_calibration_scope = regime_label+regime_gate+entry_quality_label`
  - exact current-bucket rows = **4**
  - same scope dominant bucket = **q35 (187 rows)**，current q15 僅 **4 rows / 2.09%**
- q35 scaling audit：
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `scope_applicability = reference_only_current_bucket_outside_q35`
  - `base_stack_redesign_experiment.verdict = base_stack_redesign_discriminative_reweight_crosses_trade_floor`
  - 但這是 **q35 reference artifact**，不是 current q15 runtime closure

---

## Step 1 事實分類

### 已改善
1. **`feat_4h_bias50` 假性 recent blocker 已解除**：本輪新增 `coherent_4h_trend_compression` provenance，避免把健康 bull-pocket trend-stack 收斂誤寫成單點 4H bias50 投影故障。
2. **recent drift artifact 更完整**：`expected_compressed_examples` 現在同時覆蓋 `feat_atr_pct / feat_4h_bias50 / feat_4h_bias200 / feat_4h_dist_swing_low / feat_4h_dist_bb_lower`，machine-read 能直接區分 underlying / trend-stack / support-cluster 類壓縮。
3. **主病灶繼續前移**：完成 bias50 provenance 後，sibling-window `new_compressed` 已改成 `feat_4h_bias20`，代表 heartbeat 沒有停在舊假 blocker 上空轉。
4. **驗證完整通過**：
   - `python -m pytest tests/test_recent_drift_report.py -q` → **15 passed**
   - `python scripts/recent_drift_report.py`
   - `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
   - `python scripts/hb_q35_scaling_audit.py`
   - `python scripts/full_ic.py`
   - `python scripts/regime_aware_ic.py`
   - `python tests/comprehensive_test.py` → **6/6 PASS**

### 惡化
1. **recent canonical pathology 仍持續**：recent 100 依然是 `100x1 bull pocket / distribution_pathology`，只是主病灶已從 `feat_4h_macd_hist → feat_4h_bias50 → feat_4h_bias20`。
2. **current live 從 q35 漂移到 q15**：live row 雖已有 exact q15 rows，但只有 **4 rows**，support 仍遠低於 deployment-grade 門檻，造成 runtime 直接維持 `allowed_layers=0`。
3. **q35 不能再當 current-live closure 敘事**：q35 audit 目前只是 reference-only；若下輪仍把 q35 當主 blocker，會再次偏離 current live 真實路徑。

### 卡住不動
1. **recent 100 bull pocket 的 constant-target / regime concentration 尚未解除**：這仍會污染 calibration 與 drift triage。
2. **q15 exact-support accumulation / replay 尚未落地**：目前只有 4 筆 exact q15 rows，無法 deployment-grade 放行。
3. **dual-role governance / source-level blocker 本輪未處理**：仍保持後排，等待 P0/P1 收斂後再升級。

---

## Open Issues

### P0. recent canonical pathology 仍持續；`feat_4h_bias20` 成為新的 unexpected compression 主病灶
**現象**
- recent 100 rows：`wins=100 / losses=0`
- `dominant_regime = bull (100%)`
- alerts = `constant_target`, `regime_concentration`, `regime_shift`
- 完成 `feat_4h_bias50` provenance patch 後，sibling-window `new_compressed = feat_4h_bias20`

**影響**
- 這會持續污染 recent calibration、bull pocket 解讀與 drift triage。
- 下輪若還停在 `feat_4h_bias50` 或 `feat_4h_macd_hist`，就是重新處理已降級的假 blocker。

**本輪 patch / 證據**
- `scripts/recent_drift_report.py`：新增 **4H bias50 provenance contract**。
- `tests/test_recent_drift_report.py`：新增 `feat_4h_bias50` trend-stack 壓縮回歸測試。
- `ARCHITECTURE.md`：同步新增 **4H bias50 provenance contract**。
- 驗證：
  - `python -m pytest tests/test_recent_drift_report.py -q` → **15 passed**
  - `python scripts/recent_drift_report.py`
- 證據：
  - `feat_4h_bias50.expected_compressed_reason = coherent_4h_trend_compression`
  - `expected_compressed_count = 6`
  - `new_compressed = feat_4h_bias20`

**下一步**
- 直接追 `feat_4h_bias20` 為何在 recent bull pocket 被壓縮：先區分這是 market-state 真收斂、4H bias20 projection 過度平滑、還是短週期 4H 對齊 / backfill 問題。

### P1. current live blocker 已切到 q15 exact support 不足；必須做 q15 support accumulation / replay，而不是繼續追 q35
**現象**
- live predictor：`bull / CAUTION / q15`
- `entry_quality = 0.4326`、`entry_quality_label = D`
- `allowed_layers_raw = 0`、`allowed_layers = 0`
- `deployment_blocker = under_minimum_exact_live_structure_bucket`
- same scope `regime_label+regime_gate+entry_quality_label` rows = **191**，但 current q15 bucket rows 只有 **4**，dominant bucket 是 q35（187 rows）

**影響**
- runtime 現在不是被 q35 exact-lane=0 卡住，而是被 **q15 exact support 遠低於 minimum support** 卡住。
- 若下輪仍把 q35 exact-lane replay 當主線，會再次偏離 current-live blocker。

**本輪證據**
- `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
- `python scripts/hb_q35_scaling_audit.py`
- probe 顯示：
  - `current_live_structure_bucket = CAUTION|structure_quality_caution|q15`
  - `current_live_structure_bucket_rows = 4`
  - `deployment_blocker = under_minimum_exact_live_structure_bucket`
- q35 audit 顯示：
  - `scope_applicability = reference_only_current_bucket_outside_q35`
  - `recommended_action` 明確要求優先處理 current bucket 的 exact support / structure component blocker

**下一步**
- 下輪若要處理 live blocker，必須直接做 **q15 exact support accumulation / replay**，並把 `under_minimum_exact_live_structure_bucket` 的 support route、current rows、minimum rows、replay artifact 同步清楚；不得再回退到 q35 exact-lane 敘事。

### P2. q35 bias50 calibration 仍可作 reference，但不得誤寫成 current-live closure
**現象**
- q35 audit 仍顯示 `bias50_formula_may_be_too_harsh`
- `base_stack_redesign_experiment` 仍可在 q35 reference lane 內跨過 trade floor
- 但 `scope_applicability = reference_only_current_bucket_outside_q35`

**影響**
- q35 仍是研究/備援路線，但不是當前 q15 blocker 的直接解法。
- 若 heartbeat 混用 q35 reference 結論與 current q15 runtime，文件會再次失真。

**下一步**
- 保留 q35 artifact 作 formula-review / calibration 參考；直到 current live row回到 q35 lane 前，不得把它寫成 current deployment 路徑。

---

## Not Issues
- **`feat_4h_macd_hist` 仍是 primary blocker**：不是。本輪已把主病灶前移，`new_compressed` 已改成 `feat_4h_bias20`。
- **`feat_4h_bias50` 仍是 isolated projection blocker**：不是。本輪已證明它屬於 `coherent_4h_trend_compression`。
- **current live 仍在 q35 exact-lane=0 blocker**：不是。current live 已切到 q15，blocker 是 `under_minimum_exact_live_structure_bucket`。
- **q35 redesign 可直接放行 current live row**：不是。q35 現在只可當 reference-only artifact。
- **本輪可以直接把 dual-role governance 拉回 P0**：不是。主 blocker 已轉成 `feat_4h_bias20` 與 q15 exact support。

---

## Current Priority
1. **recent 100 bull pocket root cause：直接追 `feat_4h_bias20` unexpected compression**
2. **q15 exact support accumulation / replay（current live 真 blocker）**
3. **q35 只保留 reference-only，dual-role governance 與 source blockers 繼續後排**

---

## Next Gate Input
- **Next focus**：`feat_4h_bias20 recent-window unexpected compression root cause`、`q15 exact support accumulation / replay`、`keep q35 reference-only until current live returns to q35`
- **Success gate**：
  - recent drift 的 `new_compressed` 不再是 `feat_4h_bias20`
  - recent 100 bull pocket 至少留下 1 個針對 `feat_4h_bias20` 的 root-cause patch + verify
  - current live q15 bucket rows 明顯增加，或至少留下 q15 exact-support replay / accumulation patch，並把 `under_minimum_exact_live_structure_bucket` 的 support 進度與門檻寫清楚
  - `ISSUES.md` / `ROADMAP.md` / `ARCHITECTURE.md` / `data/recent_drift_report.json` / `data/live_predict_probe.json` / `data/q35_scaling_audit.json` 對 blocker 語義一致
- **Fallback if fail**：
  - 若 recent pathology 仍無 patch，下輪只能做 `feat_4h_bias20` root cause 修復，不再接受報告式心跳
  - 若 q15 support accumulation / replay 仍沒做，維持為 P1 blocker，不得重寫成 q35 floor-gap 或 generic support 問題
  - 若 current live bucket 再切換，先重寫 current-state docs，再評估新 closure
- **Carry-forward input for next heartbeat**：
  1. 先讀最新 `data/recent_drift_report.json`，確認 `feat_4h_bias50.expected_compressed_reason=coherent_4h_trend_compression` 是否仍成立，以及 sibling-window `new_compressed` 是否仍是 `feat_4h_bias20`。
  2. 若 recent 100 仍是 `100x1 bull pocket`，下一輪必須直接留下 `feat_4h_bias20` root-cause patch，不可回頭追 `feat_4h_bias50`、`feat_4h_macd_hist`、`feat_4h_dist_bb_lower`。
  3. 再讀 `data/live_predict_probe.json`，確認 `current_live_structure_bucket` 是否仍為 q15、`current_live_structure_bucket_rows` 是否仍只有 4 左右、`deployment_blocker` 是否仍為 `under_minimum_exact_live_structure_bucket`。
  4. 若 current live 仍在 q15 且 rows 仍低於 minimum support，下一輪只能追 q15 exact-support accumulation / replay，不得回退到 q35 exact-lane 敘事。
