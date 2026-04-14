# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 23:40 UTC — Heartbeat #745（本輪已完成 **live bull q35 runtime semantics 診斷對齊**：exact live lane 單一 bucket 不再被誤判為 sub-buckets-present，並新增 `allowed_layers_reason` 讓 runtime 能明確說出 `0-layer` 是 raw entry-quality trade floor，而不是 execution guardrail 額外壓層。）_

本文件只保留**目前已落地能力、當前主目標、下一步 gate**，不保留歷史 roadmap 敘事。

---

## 已完成

### Canonical heartbeat / diagnostics
- fast heartbeat 持續刷新：
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `issues.json`
  - numbered summary：`data/heartbeat_745_summary.json`

### 本輪新完成：live bull q35 runtime semantics 診斷對齊
- `model/predictor.py`
  - exact live lane 若只有單一 current bucket，現在固定輸出：
    - `decision_quality_exact_live_lane_bucket_verdict = no_exact_lane_sub_bucket_split`
    - `decision_quality_exact_live_lane_toxic_bucket = null`
  - live decision profile 新增：
    - `allowed_layers_reason`
- `scripts/hb_predict_probe.py`
  - 最新 probe JSON 已持久化 `allowed_layers_reason`
- `scripts/live_decision_quality_drilldown.py`
  - drilldown markdown / JSON 現在直接顯示 `allowed_layers_reason`
- `scripts/hb_parallel_runner.py`
  - heartbeat summary 的 `live_predictor_diagnostics` 已同步帶出 `allowed_layers_reason`
- `ARCHITECTURE.md`
  - 已同步 single-bucket exact-lane contract 與 `allowed_layers_reason`

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q` → **42 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 745` → **通過**
- `source venv/bin/activate && python scripts/hb_predict_probe.py > data/live_predict_probe.json && python scripts/live_decision_quality_drilldown.py` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#745）：
  - Raw / Features / Labels = **21436 / 12865 / 43055**
  - simulated_pyramid_win = **0.5765**
- label freshness 正常：
  - 240m lag 約 **3.2h**
  - 1440m lag 約 **23.0h**

### IC / drift / live contract
- Global IC：**19/30**
- TW-IC：**25/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 5/8**
- drift primary window：**100**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**bull 94.0%**
- live predictor：
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**D**
  - decision-quality label：**B**
  - allowed layers：**0**
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `execution_guardrail_applied = false`
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=90**
  - exact live lane：**single bucket / no toxic split / rows=90 / win=1.0 / quality=0.7033**
  - chosen calibration scope：**`regime_label+entry_quality_label`**（sample_size=99）

### 模型 / shrinkage / bull exact-supported 對齊
- global recommended profile：**`core_only`**
- bull exact-supported best profile：**`core_plus_macro_plus_4h_structure_shift`**
- train selected profile：**`core_plus_macro_plus_4h_structure_shift`**
  - source：**`bull_4h_pocket_ablation.exact_supported_profile`**
  - support cohort：**`bull_all`**
  - support rows：**761**
  - exact live bucket rows：**90**
- leaderboard selected profile：**`core_plus_macro_plus_4h_structure_shift`**
  - source：**`bull_4h_pocket_ablation.exact_supported_profile`**
- dual profile state：**`aligned`**
- support blocker state：**`exact_live_bucket_supported`**
- proxy boundary verdict：**`exact_bucket_supported_proxy_not_required`**

### Source blocker
- `fin_netflow` 仍是 **auth_missing**
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵

---

## 當前主目標

### 目標 A：把 bull q35 的「0-layer」從現象收斂成可修/可接受的 root cause
目前已確認：
- q35 exact-supported 已恢復；
- train / leaderboard parity 已解且仍對齊；
- exact live lane 沒有 toxic sub-bucket；
- `allowed_layers_reason = entry_quality_below_trade_floor` 且 `execution_guardrail_applied = false`。

下一步主目標：
- **判斷 q35 current lane 的 raw entry-quality 公式是否過嚴，或它本來就應該是 hold-only lane**；
- 用 component-level 分解說清楚：`feat_4h_bias50 / feat_nose / feat_pulse / feat_ear / 4H 結構欄位` 哪些在壓低 q35 current lane 的 raw quality。

### 目標 B：收斂 global shrinkage winner 與 bull production profile 的分工
目前已確認：
- global best：`core_only`
- bull exact-supported best：`core_plus_macro_plus_4h_structure_shift`

下一步主目標：
- **確認 `4h_structure_shift` 在 bull q35 lane 是必要 signal、必要風控，還是只是過度保守的 proxy**；
- 不把 global `core_only` 直接當 production 結論，也不因 parity 已解就停止 shrinkage 治理。

### 目標 C：維持 exact-supported contract 與 live semantics 零漂移
本輪已完成：
- exact live lane single-bucket verdict 已與 leaderboard probe / docs 對齊；
- `allowed_layers_reason` 已打通 probe / drilldown / heartbeat summary / docs。

下一步主目標：
- 繼續確保：
  - `train_selected_profile = leaderboard_selected_profile`
  - `dual_profile_state = aligned`
  - `support_blocker_state = exact_live_bucket_supported`
  - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
  - `decision_quality_exact_live_lane_bucket_verdict = no_exact_lane_sub_bucket_split`
  - `allowed_layers_reason` 不再遺失或漂移

### 目標 D：維持 source auth blocker 與 bull live gate 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 bull q35 runtime semantics 敘事

---

## 接下來要做

### 1. 拆解 q35 current lane 的 raw entry-quality 組成
要做：
- 比對 current q35 lane 與同 regime `bull|ALLOW` spillover 的：
  - `feat_4h_bias50`
  - `feat_nose`
  - `feat_pulse`
  - `feat_ear`
  - `feat_4h_bias200`
  - `feat_4h_dist_swing_low`
  - `feat_4h_dist_bb_lower`
  - `feat_4h_bb_pct_b`
- 目標不是直接放寬 gate，而是明確決定：
  - 公式應調整；或
  - q35 就應維持 hold-only / no-layer 語義。

### 2. 追 4H shrinkage 與 bull q35 production 的真正交集
要做：
- 用 bull q35 exact lane / spillover / bull_all cohort 交叉驗證 `core_plus_macro_plus_4h_structure_shift` 的必要性；
- 聚焦：`feat_4h_bias200`、`feat_4h_dist_swing_low`、`feat_4h_dist_bb_lower`、`feat_4h_bb_pct_b`；
- 不再用「global CV 比較高」直接取代 production bull lane 的治理判斷。

### 3. 維持 exact-supported + live semantics 零漂移
要做：
- 持續檢查 artifact / probe / heartbeat summary / docs 的：
  - `train_selected_profile`
  - `leaderboard_selected_profile`
  - `dual_profile_state`
  - `support_blocker_state`
  - `proxy_boundary_verdict`
  - `decision_quality_exact_live_lane_bucket_verdict`
  - `allowed_layers_reason`
- 任何一路徑若再漂移，都視為 regression。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 bull live path 問題。

---

## 暫不優先

以下本輪後仍不排最前面：
- 重新追已解的 train / leaderboard parity blocker
- 沿用舊 q15 toxic pocket 敘事
- 直接放寬 live execution guardrail 或 q35 gate
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸已不是 artifact freshness，也不是 exact-lane toxicity，而是 **q35 raw entry-quality root cause 與 4H shrinkage 分工**。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **q35 raw entry-quality 組成 / 4H shrinkage 分工** 直接相關的真 patch / run / verify。
2. `train_selected_profile / leaderboard_selected_profile / dual_profile_state / support_blocker_state / proxy_boundary_verdict / decision_quality_exact_live_lane_bucket_verdict / allowed_layers_reason` 在 artifact / docs / summary 間持續零漂移。
3. 若 current live bucket 仍是 q35 且 rows ≥ 50，必須明確解釋 `CAUTION / D / 0-layer` 是正確保守治理還是公式過嚴，而不是只報現象。
4. global `core_only` 與 production `core_plus_macro_plus_4h_structure_shift` 的分工必須更 machine-read 化。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 拆解 bull q35 current lane 的 raw entry-quality 組成，驗證 `entry_quality_below_trade_floor` 是否過嚴；
  2. 收斂 global `core_only` 與 bull production `core_plus_macro_plus_4h_structure_shift` 的分工；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下至少一個與 **q35 raw entry-quality / 4H shrinkage 分工** 直接相關的 patch / artifact / verify；
  2. `train_selected_profile / leaderboard_selected_profile / dual_profile_state / support_blocker_state / proxy_boundary_verdict / decision_quality_exact_live_lane_bucket_verdict / allowed_layers_reason` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 q35 exact-supported 仍成立，必須同輪說清楚為何 runtime 仍不放行，或留下修補後的驗證證據。

- **Fallback if fail:**
  - 若 exact-lane verdict 又回退成 `sub_buckets_present_but_not_toxic`，視為 live diagnostic regression；
  - 若 `allowed_layers_reason` 再次消失，視為 runtime semantics regression；
  - 若 train / leaderboard 再次分裂，立刻回升為 `exact_supported_train_frame_parity_blocker`；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

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
  3. 若 `exact_lane_bucket_verdict = no_exact_lane_sub_bucket_split`、`allowed_layers_reason = entry_quality_below_trade_floor`、`execution_guardrail_applied = false`、`live_current_structure_bucket = CAUTION|structure_quality_caution|q35`、`live_current_structure_bucket_rows >= 50`、`feature_group_ablation.recommended_profile = core_only`、`train_selected_profile = leaderboard_selected_profile = core_plus_macro_plus_4h_structure_shift` 仍同時成立，下一輪不得再把 train parity 或 q15 toxic pocket 當主結論；必須直接推進 **q35 raw entry-quality root cause / 4H shrinkage 分工 / source auth blocker 顯式治理**。
