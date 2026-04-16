# ISSUES.md — Current State Only

_最後更新：2026-04-16 05:10 UTC_

只保留目前仍有效的問題；不保留歷史敘事。

---

## Step 0.5 承接（把上輪結論當本輪輸入）
- 上輪 carry-forward 主軸：`q35 exact support accumulation`、`feat_atr_pct recent-window compression root cause`、`dual-role governance 僅在 q35/support 狀態清楚後再處理`。
- 本輪逐條對照結果：
  1. **q35 blocker 已重新定義，且比上輪更嚴格**：上輪是 `under_minimum_exact_live_structure_bucket (1/50)`；本輪最新 `data/live_predict_probe.json` 已變成 **`unsupported_exact_live_structure_bucket (0 exact rows)`**。也就是說，current live row 仍在 `bull / CAUTION / q35`，但 exact lane 支持從「太少」退回成「完全沒有」。
  2. **q35 redesign runtime 仍有效，但不能被包裝成 deployment closure**：本輪 `q35_discriminative_redesign_applied=true`、`entry_quality=0.804`、`allowed_layers_raw=2`，代表 runtime floor 已跨過；但 `allowed_layers=0`、`deployment_blocker=unsupported_exact_live_structure_bucket`，因此 blocker 已從 floor gap 明確切換成 **exact support 缺失**。
  3. **`feat_atr_pct` root-cause 只推進到 provenance 層，不是 closure**：本輪已補 `scripts/recent_drift_report.py`，讓 drift artifact 能把 `feat_atr_pct` 這類波動特徵標成 `expected_compressed`，前提是 `raw_market_data.volatility` 也同步壓縮；並已補 pytest 鎖住這條 contract。**但在真實資料上，`expected_compressed_count=0`，`new_unexpected_compressed_features` 仍含 `feat_atr_pct`**，所以這個 blocker 還在。
  4. **dual-role governance 仍不是主 blocker**：`leaderboard=core_only`、`train support-aware=core_plus_macro` 仍存在，但 current live path 的第一優先級仍是 q35 exact support = 0。
  5. **新的本輪主 blocker 已明確收斂**：current live q35 不是 floor gap，也不是 q15 lane；而是 **`bull / CAUTION / q35` live row 缺少 exact bucket 歷史支持（0/50）**。

---

## 系統現況
- 本輪最新 DB：**Raw / Features / Labels = 21850 / 13279 / 43750**
- 最新時間：
  - Raw：`2026-04-16 05:02:38.776737`
  - Features：`2026-04-16 05:02:38.776737`
  - Canonical 1440m labels：`2026-04-15 05:53:35.506756`
- canonical 1440m：**12709 rows / simulated_pyramid_win = 0.6470**
- 全域 IC：**17 / 30 pass**
- TW-IC：**26 / 30 pass**
- regime-aware IC：**Bear 5/8、Bull 6/8、Chop 4/8**
- current live probe：
  - regime / gate / bucket：**bull / CAUTION / q35**
  - `entry_quality = 0.804`
  - `entry_quality_label = B`
  - `q35_discriminative_redesign_applied = true`
  - `allowed_layers_raw = 2`
  - `allowed_layers = 0`
  - `allowed_layers_reason = caution_gate_caps_two_layers`
  - `execution_guardrail_reason = decision_quality_label_C_caps_layers; unsupported_exact_live_structure_bucket`
  - `deployment_blocker = unsupported_exact_live_structure_bucket`
  - `current_live_structure_bucket_rows = 0`
  - `decision_quality_calibration_scope = regime_label`
  - `decision_quality_label = C`
- q35 scaling audit：
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`
  - `scope_applicability = current_live_q35_lane_active`
  - `deployment_grade_component_experiment.verdict = runtime_patch_crosses_trade_floor`
  - `runtime_entry_quality = 0.804`
  - `runtime_remaining_gap_to_floor = -0.254`
- recent drift primary window：**100**
  - alerts = `constant_target`, `regime_concentration`, `regime_shift`
  - interpretation = `distribution_pathology`
  - `wins = 100 / losses = 0`
  - `dominant_regime = bull (100%)`
  - feature diagnostics：`expected_static=4`, `expected_compressed=0`, `overlay_only=5`, `unexpected_frozen=0`, `compressed=26`, `null_heavy=10`
  - sibling-window 新病灶：**`feat_atr_pct` 仍是 `new_unexpected_compressed_features`**
- source blockers：**8 個 blocked features**；其中 `fin_netflow = source_auth_blocked(auth_missing)` 仍未解

---

## Step 1 事實分類

### 已改善
1. **runtime floor / q35 redesign 仍有效**：current live row 現在 `entry_quality=0.804`，`allowed_layers_raw=2`，不再是 floor-gap 問題。
2. **drift artifact 已新增 compression provenance contract**：`recent_drift_report.py` 現在能把 `feat_atr_pct` 與 `raw_market_data.volatility` 的同步壓縮標成 `expected_compressed`，避免未來把真實波動收縮誤判成 pipeline 壞掉。
3. **collector 仍在推進**：本輪 collect 成功新增 `+1 raw / +1 features / +1 labels`。
4. **canonical 診斷仍健康**：Global 17/30、TW-IC 26/30，並未出現整體訊號崩壞。

### 惡化
1. **current live q35 exact support 從 1/50 退到 0/50**：blocker 從 under-minimum 升級成 `unsupported_exact_live_structure_bucket`。
2. **recent 100 canonical pathology 仍未解除**：仍是 `100x1 bull pocket`，且 `feat_atr_pct` 仍是新壓縮病灶。

### 卡住不動
1. **`feat_atr_pct` 在真實 recent window 仍未被證明是 expected compression**：新 patch 建好 provenance contract，但真實資料未過門檻，仍需根因分析。
2. **dual-role governance 仍存在**：`leaderboard_global_winner_vs_train_support_fallback` 尚未收斂。
3. **source-level sparse blockers 仍未推進**：`fin_netflow` auth_missing 依舊存在。

---

## Open Issues

### P0. current live q35 已跨 floor，但 exact support 退回 0 rows，部署被 `unsupported_exact_live_structure_bucket` 阻擋
**現象**
- current live probe：`bull / CAUTION / q35`
- `entry_quality = 0.804`
- `q35_discriminative_redesign_applied = true`
- `allowed_layers_raw = 2`
- 但 `allowed_layers = 0`
- `deployment_blocker = unsupported_exact_live_structure_bucket`
- `current_live_structure_bucket_rows = 0`

**影響**
- 現在不能再沿用「只差 exact support 1/50」的敘事。
- 主 blocker 已升級成 **exact q35 bucket 完全缺失**；任何 q35 calibration / formula patch 都只能算 runtime candidate，不能作 deployment closure。

**本輪 patch / 證據**
- 已重跑 `python scripts/hb_parallel_runner.py --fast`
- 已刷新 `data/live_predict_probe.json`
- 已刷新 `data/q35_scaling_audit.json`
- 已刷新 `data/heartbeat_fast_summary.json`
- 證據：
  - `runtime_patch_crosses_trade_floor`
  - `entry_quality = 0.804`
  - `allowed_layers_raw = 2`
  - `deployment_blocker = unsupported_exact_live_structure_bucket`
  - `current_live_structure_bucket_rows = 0`

**下一步**
- 之後 heartbeat 一律把 **q35 exact bucket missing (0/50)** 當主 blocker。
- 在 `current_live_structure_bucket_rows >= 50` 前，不可把 q35 redesign / formula review 包裝成 deployment closure。

### P1. recent canonical pathology 仍存在；`feat_atr_pct` 新增 provenance contract，但真實資料仍屬 unexpected compression
**現象**
- recent 100 rows：`wins=100 / losses=0`
- `dominant_regime = bull (100%)`
- alerts = `constant_target`, `regime_concentration`, `regime_shift`
- `expected_compressed_count = 0`
- `new_unexpected_compressed_features = [feat_atr_pct]`

**影響**
- recent pathology 仍會污染 calibration / deployment 解讀。
- 本輪已能區分「真實原始波動同步收縮」與「feature 壓縮異常」，但 `feat_atr_pct` 在真實資料上尚未被歸類到 expected compression，因此 blocker 尚未 closure。

**本輪 patch / 證據**
- 已修 `scripts/recent_drift_report.py`：
  - 新增 `expected_compressed_count / expected_compressed_examples`
  - 新增 `feat_atr_pct -> raw_market_data.volatility` 的 compression provenance 判定
- 已補測試：`tests/test_recent_drift_report.py`
- 驗證：`python -m pytest tests/test_recent_drift_report.py -q` → **9 passed**
- 驗證：重跑 `python scripts/recent_drift_report.py`
  - 真實資料結果：`expected_compressed_count = 0`
  - `new_unexpected_compressed_features` 仍含 `feat_atr_pct`

**下一步**
- 直接追 `feat_atr_pct` 為何壓縮而 `raw_market_data.volatility` 沒一起落到 expected-compression 門檻。
- 在這個根因沒查清前，recent 100 仍視為 `distribution_pathology`，不可作 deployment 放行證據。

### P1. dual-role governance 仍在：leaderboard global winner 與 support-aware production winner 未合流
**現象**
- `leaderboard = core_only`
- `train support-aware = core_plus_macro`
- `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`

**影響**
- 這不是 current-live 第一 blocker，但會持續干擾 profile parity 解讀。

**下一步**
- 先解 q35 exact support missing，再判斷這是健康雙角色治理，還是 support 恢復後應該收斂的 parity blocker。

### P2. sparse-source auth / archive blocker 仍在
**現象**
- blocked features = **8**
- `fin_netflow = source_auth_blocked / auth_missing`

**影響**
- 不是 current-live 主 blocker，但仍限制 research / sparse feature maturity。

**下一步**
- 待 q35 support + recent pathology 主線收斂後再處理。

---

## Not Issues
- **current live q35 仍卡 trade floor**：不是，本輪已明確跨過 floor。
- **`feat_atr_pct` 已被證明只是 expected compression**：不是，contract 已補，但真實資料尚未通過 expected-compression 判定。
- **Global / TW-IC 全面衰退**：不是，本輪仍為 17/30 與 26/30。
- **current live 主線已切到 q15**：不是，本輪最新 current row 又回到 `bull / CAUTION / q35`。

---

## Current Priority
1. **q35 exact support missing（0/50）deployment blocker**
2. **recent pathology 的 `feat_atr_pct` unexpected compression root cause**
3. **最後才處理 dual-role governance 與 sparse-source auth blocker**

---

## Next Gate Input
- **Next focus**：`q35 exact support accumulation from 0/50`, `feat_atr_pct recent-window unexpected compression root cause`, `dual-role governance only after q35 support state is clear`
- **Success gate**：
  - `current_live_structure_bucket_rows` 不再是 0，且 blocker 不再是 `unsupported_exact_live_structure_bucket`
  - recent pathology 至少留下 1 個 `feat_atr_pct` root-cause patch + verify
  - 文件與 artifact 一致把 current q35 blocker 寫成 **exact bucket missing / unsupported**, 不再沿用 1/50 或 floor-gap 舊敘事
- **Fallback if fail**：
  - 若 q35 exact support 連續兩輪仍是 0，升級成 explicit `exact-bucket-missing` blocker，禁止再把 q35 redesign 當 closure 敘事
  - 若 drift 仍只更新數字沒 patch，下一輪只能做 `feat_atr_pct` pathology 修復
  - 若 current bucket 再切換，先重寫 `ISSUES.md` / `ROADMAP.md` 再談任何 closure
- **Carry-forward input for next heartbeat**：
  1. 先讀最新 `data/live_predict_probe.json`，確認 current row 是否仍是 `bull / CAUTION / q35`，並先看 blocker 是否還是 `unsupported_exact_live_structure_bucket`。
  2. 若 `q35_discriminative_redesign_applied=true` 且 `entry_quality >= 0.55`，就不得再把主 blocker 寫成 floor gap；只能追 exact support missing / accumulation。
  3. 先讀 `data/recent_drift_report.json`，確認 `expected_compressed_count` 是否仍為 0，並檢查 `new_unexpected_compressed_features` 是否仍包含 `feat_atr_pct`。
  4. 若下一輪沒有留下 `feat_atr_pct` root-cause patch` 或 `q35 support accumulation evidence`，明確標記治理失敗。
