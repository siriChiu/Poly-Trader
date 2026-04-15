# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 00:40 UTC — Heartbeat #747（本輪已完成 **global shrinkage winner vs production bull profile 的 machine-readable split**：fast heartbeat / leaderboard probe 現在會明確輸出 `profile_split`、`global_profile_role`、`production_profile_role`，把 `core_only` 與 `core_plus_macro_plus_4h_structure_shift` 的分工固定成治理契約。）_

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
  - numbered summary：`data/heartbeat_747_summary.json`

### 本輪新完成：profile split machine-readable governance
- `scripts/hb_leaderboard_candidate_probe.py`
  - alignment 新增：
    - `profile_split.global_profile`
    - `profile_split.global_profile_role`
    - `profile_split.production_profile`
    - `profile_split.production_profile_role`
    - `profile_split.split_required`
    - `profile_split.verdict`
    - `profile_split.reason`
- `scripts/hb_parallel_runner.py`
  - `feature_ablation.profile_role`
  - `bull_4h_pocket_ablation.production_profile_role`
  - `leaderboard_candidate_diagnostics.profile_split`
- `tests/test_hb_parallel_runner.py`
  - 已鎖住上述欄位，避免 heartbeat 之後又退回只有 profile 名稱、沒有治理語義。

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py -q` → **11 passed**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 747` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#747）：
  - Raw / Features / Labels = **21438 / 12867 / 43061**
  - simulated_pyramid_win = **0.5766**
- label freshness 正常：
  - 240m lag 約 **3.1h**
  - 1440m lag 約 **23.2h**

### IC / drift / live contract
- Global IC：**19/30**
- TW-IC：**25/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 5/8**
- drift primary window：**100**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**bull 98.0%**
- live predictor：
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.3726 (D)**
  - allowed layers：**0**
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `execution_guardrail_applied = false`
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=90**
  - exact live lane：**single bucket / no toxic split / rows=90 / win=1.0 / quality=0.7033**
  - chosen calibration scope：**`regime_label+entry_quality_label`**（sample_size=103）
  - entry-quality decomposition：
    - `base_quality = 0.3450`
    - `structure_quality = 0.4553`
    - `trade_floor_gap = -0.1774`
    - `feat_4h_bias50` normalized score = **0.0**
    - `feat_ear` normalized score = **0.9621**（健康）

### 模型 / shrinkage / bull exact-supported 對齊
- global recommended profile：**`core_only`**
- production bull profile：**`core_plus_macro_plus_4h_structure_shift`**
- train selected profile：**`core_plus_macro_plus_4h_structure_shift`**
- leaderboard selected profile：**`core_plus_macro_plus_4h_structure_shift`**
- dual profile state：**`aligned`**
- support blocker state：**`exact_live_bucket_supported`**
- proxy boundary verdict：**`exact_bucket_supported_proxy_not_required`**
- **新治理結論**：
  - `profile_split.verdict = dual_role_required`
  - `global_profile_role = global_shrinkage_winner`
  - `production_profile_role = bull_exact_supported_production_profile`

### Source blocker
- `fin_netflow` 仍是 **auth_missing**
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵

---

## 當前主目標

### 目標 A：判定 q35 current lane 的低 entry-quality 是公式過嚴，還是正確 hold-only 語義
目前已確認：
- q35 exact-supported 已恢復；
- train / leaderboard parity 已解且仍對齊；
- exact live lane 沒有 toxic sub-bucket；
- `allowed_layers_reason = entry_quality_below_trade_floor` 且 `execution_guardrail_applied = false`；
- component-level root cause 已可 machine-read：
  - `feat_4h_bias50` 幾乎完全拖垮 base quality；
  - `nose / pulse` 偏弱；
  - 4H structure 只達 q35、`structure_quality=0.4553`。

下一步主目標：
- **驗證 `feat_4h_bias50` 與 q35 4H structure scaling 是否過度懲罰 bull current lane**；
- 若證據不支持放寬，就正式把這類 q35 current row 定義成 hold-only / no-layer 語義。

### 目標 B：把 global winner 與 production winner 的雙軌治理持續固定下來
目前已確認：
- global best：`core_only`
- production bull best：`core_plus_macro_plus_4h_structure_shift`
- 並且這兩者已 machine-read：
  - `global_profile_role = global_shrinkage_winner`
  - `production_profile_role = bull_exact_supported_production_profile`
  - `profile_split.verdict = dual_role_required`

下一步主目標：
- **確保這組 dual-role semantics 在 summary / probe / docs 持續零漂移**；
- 避免未來又把它誤寫成 parity regression 或未解 blocker。

### 目標 C：維持 exact-supported contract 與 live semantics 零漂移
本輪已完成：
- exact live lane single-bucket verdict 持續與 docs / heartbeat summary 對齊；
- `allowed_layers_reason` 持續打通 probe / drilldown / heartbeat summary；
- `entry_quality_components` 與 `profile_split` 都已同步打通 probe / heartbeat summary。

下一步主目標：
- 繼續確保：
  - `train_selected_profile = leaderboard_selected_profile`
  - `dual_profile_state = aligned`
  - `support_blocker_state = exact_live_bucket_supported`
  - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
  - `decision_quality_exact_live_lane_bucket_verdict = no_exact_lane_sub_bucket_split`
  - `allowed_layers_reason` / `entry_quality_components` / `profile_split` 不再遺失或漂移

### 目標 D：維持 source auth blocker 與 bull live gate 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 bull q35 runtime semantics 敘事

---

## 接下來要做

### 1. 驗證 q35 lane 的 bias50 / structure scaling 是否過嚴
要做：
- 直接針對 live q35 current row 與 exact live lane / same-regime spillover 比對：
  - `feat_4h_bias50`
  - `feat_nose`
  - `feat_pulse`
  - `feat_ear`
  - `feat_4h_bb_pct_b`
  - `feat_4h_dist_bb_lower`
  - `feat_4h_dist_swing_low`
- 目標不是先放寬 gate，而是明確決定：
  - 公式應調整；或
  - q35 就應維持 hold-only / no-layer 語義。

### 2. 維持 profile split 的 machine-readable governance
要做：
- 確保所有關鍵 surface 持續同時看得到：
  - `global_profile_role = global_shrinkage_winner`
  - `production_profile_role = bull_exact_supported_production_profile`
  - `profile_split.verdict = dual_role_required`
- 不再把這組差異只留在人工解讀層。

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
  - `entry_quality_components`
  - `profile_split`
- 任何一路徑若再漂移，都視為 regression。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 bull live path 問題。

---

## 暫不優先

以下本輪後仍不排最前面：
- 直接放寬 q35 runtime gate
- 直接調低 `trade_floor`
- 重新追已解的 train / leaderboard parity blocker
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸已不是 parity 漂移，而是 **q35 current row 的 scaling 判定題**；另外，profile split 已完成治理語義化，不需要再把它當 blocker 追打。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **bias50 / q35 structure scaling / hold-only verdict** 直接相關的真 patch / run / verify。
2. `profile_split / global_profile_role / production_profile_role / train_selected_profile / leaderboard_selected_profile / dual_profile_state / support_blocker_state / proxy_boundary_verdict / allowed_layers_reason / entry_quality_components` 在 artifact / docs / summary 間持續零漂移。
3. 若 current live bucket 仍是 q35 且 rows ≥ 50，必須明確解釋 `CAUTION / D / 0-layer` 是正確保守治理還是公式過嚴，而不是只報現象。
4. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 驗證 `feat_4h_bias50` 與 q35 4H structure scaling 是否過度懲罰 bull current lane；
  2. 若證據不支持放寬，正式把這類 q35 current row 定義成 hold-only lane；
  3. 維持 `profile_split` 與 `fin_netflow` blocker 的零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **bias50 scaling / q35 structure scaling / hold-only verdict** 直接相關的 patch / artifact / verify；
  2. `profile_split / global_profile_role / production_profile_role / train_selected_profile / leaderboard_selected_profile / dual_profile_state / support_blocker_state / proxy_boundary_verdict / allowed_layers_reason / entry_quality_components` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 q35 exact-supported 仍成立，必須同輪說清楚 runtime 不放行到底是「公式過嚴」還是「hold-only lane 正確治理」。

- **Fallback if fail:**
  - 若 `profile_split` / `global_profile_role` / `production_profile_role` 再次缺失，視為 governance regression；
  - 若 exact-lane verdict 又回退，視為 live diagnostic regression；
  - 若 scaling audit 仍做不出結論，下一輪必須新增更直接的 lane-level 審計 artifact，而不是只重述 trade floor 現象；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若新增 scaling / hold-only contract）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_747_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/feature_group_ablation.json`
     - `data/bull_4h_pocket_ablation.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若 `allowed_layers_reason = entry_quality_below_trade_floor`、`execution_guardrail_applied = false`、`entry_quality_components.trade_floor_gap < 0`、`entry_quality_components.base_components` 仍顯示 `feat_4h_bias50` 為最大拖累、`profile_split.verdict = dual_role_required`、`global_profile = core_only`、`production_profile = core_plus_macro_plus_4h_structure_shift`、`support_blocker_state = exact_live_bucket_supported` 同時成立，下一輪不得再只重述 trade floor 現象；必須直接推進 **bias50 scaling / q35 structure scaling / hold-only verdict**。
