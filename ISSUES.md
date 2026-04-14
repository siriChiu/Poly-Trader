# ISSUES.md — Current State Only

_最後更新：2026-04-14 23:40 UTC — Heartbeat #745（本輪已修補 **live bull q35 runtime semantics 診斷漂移**：exact live lane 單一 bucket 不再被誤標為 sub-buckets-present，且 live probe / drilldown / heartbeat summary 現在會明確輸出 `allowed_layers_reason`，把「layers=0 是 entry-quality trade floor」和「execution guardrail 額外壓層」分開。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#744）要求本輪處理
- **Next focus**：
  1. 追 live bull q35 path，釐清 exact-supported 後仍 `CAUTION / D / 0-layer` 的根因；
  2. 收斂 global `core_only` 與 bull production `core_plus_macro_plus_4h_structure_shift` 的分工；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。
- **Success gate**：
  1. 至少留下 1 個與 **live bull runtime semantics / 4H shrinkage 分工** 直接相關的 patch / artifact / verify；
  2. `train_selected_profile / leaderboard_selected_profile / dual_profile_state / support_blocker_state / proxy_boundary_verdict / live_current_structure_bucket / allowed_layers` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 q35 exact-supported 仍成立，必須同輪說清楚為何 runtime 仍不放行，或留下修補後的驗證證據。
- **Fallback if fail**：
  - 若 train / leaderboard 再次分裂，回升為 `exact_supported_train_frame_parity_blocker`；
  - 若 docs 又把舊 q15 toxic narrative 當 current blocker，視為 stale-doc regression；
  - 若 source auth 未修，持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - `model/predictor.py`
    - 修正 exact live lane 只有單一 bucket 時的診斷：`decision_quality_exact_live_lane_bucket_verdict` 現在固定回 `no_exact_lane_sub_bucket_split`，`toxic_bucket=null`；
    - 新增 `allowed_layers_reason`，把 raw 層數決策原因 machine-read 化。
  - `scripts/hb_predict_probe.py`
    - probe JSON 現在持久化 `allowed_layers_reason`。
  - `scripts/live_decision_quality_drilldown.py`
    - drilldown JSON / markdown 現在直接揭露 `allowed_layers_reason`。
  - `scripts/hb_parallel_runner.py`
    - heartbeat summary 的 `live_predictor_diagnostics` 現在同步帶出 `allowed_layers_reason`。
  - `tests/test_api_feature_history_and_predictor.py`
    - 新增 regression test：single-bucket exact lane 必須回 `no_exact_lane_sub_bucket_split`；
    - 驗證 live decision profile 會輸出 `allowed_layers_reason`。
  - `tests/test_hb_parallel_runner.py`
    - 新增 heartbeat summary 對 `allowed_layers_reason` 的回歸檢查。
  - `ARCHITECTURE.md`
    - 已同步新 contract：`allowed_layers_reason` + single-bucket exact-lane semantics。
- **驗證已完成**：
  - `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q` → **42 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 745` → **通過**
  - `source venv/bin/activate && python scripts/hb_predict_probe.py > data/live_predict_probe.json && python scripts/live_decision_quality_drilldown.py` → **通過**
- **本輪前提更新**：
  - live bull current path 目前不是 q15 toxic pocket，也不是 execution guardrail 額外壓層；
  - 最新 probe 已證明：
    - `exact_live_lane_bucket_verdict = no_exact_lane_sub_bucket_split`
    - `allowed_layers_reason = entry_quality_below_trade_floor`
    - `execution_guardrail_applied = false`
  - 因此目前 `CAUTION / D / 0 layers` 的直接來源，是 **raw entry-quality trade floor + q35 weak-structure semantics**，不是 stale exact-lane toxicity 敘事。
- **本輪明確不做**：
  - 不把已解的 exact-lane diagnostic drift 留在 active issues；
  - 不在證據不足時直接放寬 q35 runtime gate；
  - 不把 `fin_netflow` auth 缺失混成 bull live lane 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `model/predictor.py`
  - `scripts/hb_predict_probe.py`
  - `scripts/live_decision_quality_drilldown.py`
  - `scripts/hb_parallel_runner.py`
  - `tests/test_api_feature_history_and_predictor.py`
  - `tests/test_hb_parallel_runner.py`
  - `ARCHITECTURE.md`
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q` → **42 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 745`
  - `source venv/bin/activate && python scripts/hb_predict_probe.py > data/live_predict_probe.json && python scripts/live_decision_quality_drilldown.py`
- **已刷新 artifacts**
  - `data/heartbeat_745_summary.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `model/ic_signs.json`

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #745：
  - Raw / Features / Labels：**21436 / 12865 / 43055**
  - 本輪增量：**+1 raw / +1 feature / +3 labels**
  - canonical target `simulated_pyramid_win`：**0.5765**
  - 240m labels：**21585 rows / target_rows 12663 / lag_vs_raw 3.2h**
  - 1440m labels：**12385 rows / target_rows 12385 / lag_vs_raw 23.0h**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**25/30 pass**
- TW 歷史：**#745=25/30，#744=25/30，#743=26/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 5/8**
- primary drift window：**recent 100**
  - alerts：`label_imbalance`, `regime_concentration`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 94.0%**
  - win_rate：**0.9700**
  - avg_quality：**0.6764**
  - avg_pnl：**+0.0212**
  - avg_drawdown_penalty：**0.0343**
- 判讀：recent canonical pocket 仍健康；問題不在 recent target pathology，而在 live q35 runtime semantics 與 4H spillover 對 raw entry-quality 的壓制。

### Train / leaderboard / live contract
- `model/last_metrics.json`
  - `feature_profile = core_plus_macro_plus_4h_structure_shift`
  - `feature_profile_meta.source = bull_4h_pocket_ablation.exact_supported_profile`
  - Train=`67.5%`
  - CV=`71.7% ± 9.9pp`
  - `n_features = 21`
- `data/leaderboard_feature_profile_probe.json`
  - `train_selected_profile = core_plus_macro_plus_4h_structure_shift`
  - `leaderboard_selected_profile = core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = aligned`
  - `support_blocker_state = exact_live_bucket_supported`
  - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
  - `live_current_structure_bucket = CAUTION|structure_quality_caution|q35`
  - `live_current_structure_bucket_rows = 90`
  - `exact_lane_bucket_verdict = no_exact_lane_sub_bucket_split`
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.4312**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.3861 (D)**
  - decision-quality label：**B**
  - expected win / quality：**0.9697 / 0.6755**
  - allowed layers：**0 → 0**
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `execution_guardrail_applied = false`
  - chosen calibration scope：**`regime_label+entry_quality_label` / sample_size=99**
  - exact live lane：**90 rows / win=1.0 / quality=0.7033 / verdict=no_exact_lane_sub_bucket_split**
  - same-regime spillover：**9 rows / bucket=`bull|ALLOW` / win=0.6667 / quality=0.3969 / 4H shift = bias200↑, dist_swing_low↑, dist_bb_lower↑**
- 判讀：**目前 0-layer 是 raw entry-quality trade floor 的結果，不是 execution guardrail 額外壓層；exact lane 本身沒有 toxic sub-bucket，但同 regime 的 ALLOW spillover 仍顯示更高 4H 延伸距離會明顯惡化品質。**

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. live bull q35 path 仍停在 CAUTION / D / allowed_layers=0，但 root cause 已收斂成「raw entry-quality trade floor」
**現象**
- q35 exact-supported 已成立（rows=90）；
- train / leaderboard 已對齊 exact-supported profile；
- probe 顯示：
  - `exact_lane_bucket_verdict = no_exact_lane_sub_bucket_split`
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `execution_guardrail_applied = false`
  - exact lane `win_rate=1.0 / quality=0.7033`

**判讀**
- 目前 bottleneck 已從「train parity」與「exact-lane toxic bucket」收斂到：
  1. q35 lane 的 raw entry-quality 本身偏低（0.3861 → D）；
  2. 同 regime 的少量 `bull|ALLOW` spillover rows 雖然結構更高，但 quality 明顯更差（0.3969），說明單純提高 4H 延伸不會自動變成可部署 pocket。
- 換句話說：
  - **現在的 `CAUTION / D / 0-layer` 更像是正確保守治理，而不是 stale blocker。**
  - 下一步不是直接放寬 gate，而是要驗證 entry-quality 公式是否過度懲罰 q35，或 bull q35 根本就只該是 hold-only lane。

**下一步方向**
- 針對 q35 current lane 與 bull ALLOW spillover 的 **entry-quality 組成** 做 component-level 對比；
- 把 `feat_4h_bias50 / feat_nose / feat_pulse / feat_ear` 與 `feat_4h_*` 結構欄位如何壓低 raw quality 量化出來，再決定要調公式還是保留 hold-only 語義。

---

### P1. global shrinkage winner 與 production bull profile 仍分裂
**現象**
- `feature_group_ablation.json.recommended_profile = core_only`；
- bull exact-supported production profile = `core_plus_macro_plus_4h_structure_shift`；
- 這個分裂在 #745 仍成立，但 train / leaderboard 對齊沒有漂移。

**判讀**
- global CV 最佳與 bull exact-supported best 仍然不同；
- 現在需要回答的是：`4h_structure_shift` 在 bull q35 path 到底是必要 signal、風控提示，還是只是一個讓 raw quality 變保守的 proxy。

**下一步方向**
- 直接對 bull q35 exact lane 跑 feature attribution / ablation drilldown；
- 優先看：`feat_4h_bias200`、`feat_4h_dist_swing_low`、`feat_4h_dist_bb_lower`、`feat_4h_bb_pct_b` 與 `feat_4h_bias50` 的交互作用；
- 不再把 `core_only` 直接當 production 結論，也不因 parity 已解就停止 shrinkage 治理。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1565)**

**判讀**
- 這仍是**外部憑證 blocker**，不是 bull live lane 問題。

---

## 本輪已清掉的問題

### RESOLVED. exact live lane single-bucket diagnostic drift
**修前**
- `live_predict_probe.json` 的 exact live lane 明明只有一個 q35 bucket，卻仍回 `sub_buckets_present_but_not_toxic`，與 leaderboard probe / docs 的 `no_exact_lane_sub_bucket_split` 不一致。

**本輪 patch + 證據**
- `model/predictor.py`
  - `_exact_live_lane_bucket_diagnostics()` 現在在 single-bucket 情境下強制回：
    - `verdict = no_exact_lane_sub_bucket_split`
    - `toxic_bucket = null`
- `tests/test_api_feature_history_and_predictor.py`
  - 新增 single-bucket regression test。
- `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
  - 最新 artifact 已顯示：
    - `bucket_count = 1`
    - `verdict = no_exact_lane_sub_bucket_split`
    - `toxic_bucket = null`

**狀態**
- **已修復**：exact-lane verdict 已與 leaderboard probe / docs 對齊。

### RESOLVED. 0-layer root cause 在 probe / drilldown / heartbeat summary 中不再模糊
**修前**
- probe 只看到 `allowed_layers_raw=0 → allowed_layers=0`，但無法 machine-check 這是 raw trade floor 還是 execution guardrail 額外壓層。

**本輪 patch + 證據**
- `model/predictor.py`
  - `_build_live_decision_profile()` 新增 `allowed_layers_reason`。
- `scripts/hb_predict_probe.py`
  - probe JSON 會持久化 `allowed_layers_reason`。
- `scripts/live_decision_quality_drilldown.py`
  - markdown / JSON 現在會顯示 `allowed_layers_reason`。
- `scripts/hb_parallel_runner.py`
  - heartbeat summary 的 `live_predictor_diagnostics` 也同步帶出 `allowed_layers_reason`。
- 最新 artifact：
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `execution_guardrail_applied = false`

**狀態**
- **已修復**：本輪已能明確證明 `0-layer` 來自 raw entry-quality trade floor，不是額外 guardrail。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **修 exact live lane 單一 bucket 誤診斷，消除 artifact / probe / docs 漂移。** ✅
2. **把 0-layer 的直接原因 machine-read 化，避免再把 raw trade floor 和 execution guardrail 混為一談。** ✅
3. **重跑 fast heartbeat / probe / drilldown，驗證 live bull q35 path 的當前 blocker 是否真的收斂。** ✅

### 本輪不做
- 不直接放寬 q35 runtime gate；
- 不把單一 exact lane 高勝率直接當成可加碼依據；
- 不把 `fin_netflow` auth 缺失寫成即將恢復。

---

## 下一輪 gate

- **Next focus:**
  1. 拆解 bull q35 current lane 的 raw entry-quality 組成，驗證 `entry_quality_below_trade_floor` 是否過嚴；
  2. 釐清 `core_only` 與 `core_plus_macro_plus_4h_structure_shift` 在 bull q35 production path 的分工；
  3. 持續把 `fin_netflow` 當外部 source auth blocker 管理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q35 raw entry-quality 組成 / 4H shrinkage 分工** 直接相關的 patch / artifact / verify；
  2. `exact_lane_bucket_verdict / allowed_layers_reason / execution_guardrail_applied / train_selected_profile / leaderboard_selected_profile / dual_profile_state` 必須在 artifact / docs / summary 間零漂移；
  3. 若 q35 仍是 `CAUTION / D / 0-layer`，必須以 component-level 證據說清楚這是正確保守治理還是公式過嚴。

- **Fallback if fail:**
  - 若 exact-lane verdict 又回成 `sub_buckets_present_but_not_toxic`，視為 live diagnostic regression；
  - 若 `allowed_layers_reason` 消失或 again 無法分辨 raw vs guardrail，視為 runtime semantics regression；
  - 若 train / leaderboard 再次分裂，立刻回升為 `exact_supported_train_frame_parity_blocker`；
  - 若 `fin_netflow` auth 未修，持續標記 blocked，不准寫成「快好了」。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 entry-quality contract 或 4H shrinkage contract 再擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_745_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/feature_group_ablation.json`
     - `data/bull_4h_pocket_ablation.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若下輪仍看到：
     - `exact_lane_bucket_verdict = no_exact_lane_sub_bucket_split`
     - `allowed_layers_reason = entry_quality_below_trade_floor`
     - `execution_guardrail_applied = false`
     - `live_current_structure_bucket = CAUTION|structure_quality_caution|q35`
     - `live_current_structure_bucket_rows >= 50`
     - `feature_group_ablation.recommended_profile = core_only`
     - `train_selected_profile = leaderboard_selected_profile = core_plus_macro_plus_4h_structure_shift`
     則不得再把問題描述成「q15 toxic pocket」或「train parity」；必須直接推進 **q35 raw entry-quality root cause / 4H shrinkage 分工 / source auth blocker 顯式治理**。
