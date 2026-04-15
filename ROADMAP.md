# ROADMAP.md — Current Plan Only

_最後更新：2026-04-15 05:02 UTC — Heartbeat #1005（本輪已把 q35/bias50 問題從 **bull cohort segmentation 候選** 正式收斂成 **exact-lane formula review**：current `feat_4h_bias50` 已回到 exact-lane p90 內，predictor / q35 audit 也已對這類 row 套用 `exact_lane_elevated_within_p90` 保守非零分數，live `entry_quality` 因而由 `0.4826 → 0.5238`，但仍未跨過 `0.55` trade floor。）_

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
  - `data/q35_scaling_audit.json`
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `issues.json`
  - numbered summary：`data/heartbeat_1005_summary.json`

### 本輪新完成：q35 exact-lane formula review 已落地到 runtime
- `model/q35_bias50_calibration.py`
  - 支援 `overall_verdict=bias50_formula_may_be_too_harsh`
  - 支援 `segmented_calibration.status=formula_review_required`
  - 新增 conservative segment：`exact_lane_elevated_within_p90`
- `scripts/hb_q35_scaling_audit.py`
  - 當 current `bias50` 已回到 exact-lane p90 內時，不再繼續走 broader bull segmentation 語義
  - 會改寫成：
    - `overall_verdict = bias50_formula_may_be_too_harsh`
    - `segmented_calibration.status = formula_review_required`
    - `segmented_calibration.recommended_mode = exact_lane_formula_review`
    - `segmented_calibration.runtime_contract_status = piecewise_runtime_active`
- `tests/test_api_feature_history_and_predictor.py`
  - 已鎖住 exact-lane formula-review calibration regression
- `tests/test_hb_parallel_runner.py`
  - 已鎖住 formula-review runtime-active regression
- `ARCHITECTURE.md`
  - 已同步 q35 contract 的 exact-lane formula-review 分支

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_parallel_runner.py -q` → **50 passed**
- `source venv/bin/activate && python scripts/hb_q35_scaling_audit.py` → **通過**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 1005` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#1005）：
  - Raw / Features / Labels = **21578 / 13007 / 43185**
  - simulated_pyramid_win = **0.5785**
- label freshness 正常：
  - 240m lag 約 **3.2h**
  - 1440m lag 約 **23.4h**

### IC / drift / live contract
- Global IC：**19/30**
- TW-IC：**20/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 6/8**
- drift primary window：**100**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**bull 100%**
- live predictor：
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.5238 (D)**
  - allowed layers：**0**
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - chosen scope：**`regime_label+entry_quality_label`**（sample_size=197）
  - expected win rate：**0.9848**
  - expected pyramid quality：**0.6713**

### 本輪新結論：q35 主線已從 segmented calibration 轉成 exact-lane formula review
- `data/q35_scaling_audit.json`
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `structure_scaling_verdict = q35_structure_caution_not_root_cause`
  - `segmented_calibration.status = formula_review_required`
  - `segmented_calibration.recommended_mode = exact_lane_formula_review`
  - `segmented_calibration.runtime_contract_status = piecewise_runtime_active`
  - `piecewise_runtime_preview.segment = exact_lane_elevated_within_p90`
  - current `feat_4h_bias50 = 3.2478`
  - exact lane：`p75 = 3.0207`、`p90 = 3.4106`、`current_bias50_percentile = 0.8763`
  - runtime bias50 score：**0.1334**（legacy 為 0）
  - live entry quality：**0.5238**（仍低於 `trade_floor=0.55`）
  - `required_bias50_cap_for_floor = 1.2965`
- **治理結論**：
  - 不能直接把 current q35 lane 放寬；
  - 也不能再把問題寫成「runtime 還沒吃到校準公式」；
  - 下一步必須直接拆解剩餘 **0.0262 trade-floor gap**。

### 模型 / shrinkage / bull exact-supported 對齊
- global recommended profile：**`core_only`**
- production bull profile：**`core_plus_macro_plus_4h_structure_shift`**
- train selected profile：**`core_plus_macro_plus_4h_structure_shift`**
- leaderboard selected profile：**`core_plus_macro_plus_4h_structure_shift`**
- dual profile state：**`aligned`**
- support blocker state：**`exact_live_bucket_supported`**
- proxy boundary verdict：**`exact_bucket_supported_proxy_not_required`**
- `profile_split.verdict = dual_role_required`
- `global_profile_role = global_shrinkage_winner`
- `production_profile_role = bull_exact_supported_production_profile`

### Source blocker
- `fin_netflow` 仍是 **auth_missing**
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵

---

## 當前主目標

### 目標 A：拆解剩餘 `entry_quality` **0.0262 trade-floor gap**
目前已確認：
- q35 exact-supported 已恢復；
- train / leaderboard parity 已對齊；
- q35 runtime 公式已不再是缺失；
- current live row 仍是 `CAUTION / D / 0-layer`；
- q35 audit 已明確回答：
  - **不是 q35 structure scaling root cause**
  - **目前是 bias50 formula may be too harsh**
  - **exact-lane conservative runtime score 已上線**

下一步主目標：
- **釐清剩餘 gap 的主因到底是 bias50 最後一哩，還是 nose / structure_quality / 其他 component**；
- 在拿到新的 verify 前，**不放寬 gate / floor**。

### 目標 B：把 q35 audit 的 machine-readable governance 從「需要校準」升級成「知道還差哪個 component」
目前已確認：
- `overall_verdict = bias50_formula_may_be_too_harsh`
- `segmented_calibration.status = formula_review_required`
- `segmented_calibration.runtime_contract_status = piecewise_runtime_active`
- `piecewise_runtime_preview.applied = true`

下一步主目標：
- heartbeat / probe / docs 必須明確回答：
  - `bias50` 還需提升多少才會越過 floor？
  - 如果不該再推 bias50，哪個 entry-quality component 才是下一個 root cause？

### 目標 C：把 global winner 與 production winner 的雙軌治理持續固定下來
目前已確認：
- global best：`core_only`
- production bull best：`core_plus_macro_plus_4h_structure_shift`
- 並且這兩者已 machine-read：
  - `global_profile_role = global_shrinkage_winner`
  - `production_profile_role = bull_exact_supported_production_profile`
  - `profile_split.verdict = dual_role_required`

下一步主目標：
- **確保這組 dual-role semantics 在 summary / probe / docs / next heartbeats 持續零漂移**

### 目標 D：維持 source auth blocker 與 bull live gate 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 q35 / formula review 敘事

---

## 接下來要做

### 1. 做剩餘 trade-floor gap 的 component attribution
要做：
- 用 current live row 的 `entry_quality_components` 明確量化：
  - bias50 若再微調，合理上限是多少；
  - nose / pulse / ear / structure_quality 哪一項最值得優先修；
- 目標不是「一定讓當前 row 放行」，而是**確認下一個該修的 root cause 是哪個 component**。

### 2. 維持 q35 audit 的 formula-review contract
要做：
- 確保所有關鍵 surface 持續同時看得到：
  - `q35_scaling_audit.overall_verdict`
  - `q35_scaling_audit.structure_scaling_verdict`
  - `q35_scaling_audit.segmented_calibration.status`
  - `q35_scaling_audit.segmented_calibration.recommended_mode`
  - `q35_scaling_audit.segmented_calibration.runtime_contract_status`
  - `q35_scaling_audit.piecewise_runtime_preview`
  - `q35_scaling_audit.counterfactuals.required_bias50_cap_for_floor`
- 不再把 q35 問題退回「runtime 還沒吃到公式」

### 3. 維持 profile split 與 exact-supported semantics 零漂移
要做：
- 持續檢查 artifact / probe / heartbeat summary / docs 的：
  - `train_selected_profile`
  - `leaderboard_selected_profile`
  - `dual_profile_state`
  - `profile_split`
  - `support_blocker_state`
  - `proxy_boundary_verdict`
  - `allowed_layers_reason`
  - `entry_quality_components`
  - `q35_scaling_audit`
- 任何一路徑若再漂移，都視為 regression

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 bull live path 問題

---

## 暫不優先

以下本輪後仍不排最前面：
- 直接放寬 q35 runtime gate
- 直接調低 `trade_floor`
- 把 current q35 row 當作應被立即放行的樣本
- 重新追已解的「runtime 是否已接上 q35 校準」問題
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸已不是「有沒有 q35 calibration」，而是 **exact-lane conservative score 已上線之後，剩餘 0.0262 floor gap 的真正來源是什麼**。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **剩餘 0.0262 trade-floor gap 根因拆解** 直接相關的真 patch / run / verify。
2. `q35_scaling_audit / piecewise_runtime_preview / live_predict_probe / profile_split / support_blocker_state / proxy_boundary_verdict` 在 artifact / docs / summary 間持續零漂移。
3. 若 current bull q35 row 仍是 `CAUTION / D / 0-layer`，必須再次明確說明它為何還沒跨過 floor，而且要指出**是哪個 component**阻擋，而不是退回只報 `formula_review_required`。
4. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 量化剩餘 `0.0262` trade-floor gap 的 component root cause；
  2. 維持 `q35_scaling_audit`、`profile_split`、`support_blocker_state`、`proxy_boundary_verdict` 的零漂移治理；
  3. 持續把 `fin_netflow` 當外部 source auth blocker 管理。

- **Success gate:**
  1. next run 必須留下至少一個與 **entry-quality 剩餘 gap attribution** 直接相關的 patch / artifact / verify；
  2. 若 current bull q35 lane 仍是 `CAUTION / D / 0-layer`，必須明確回答「bias50 還差多少、其他 components 是否更關鍵」；
  3. 若要主張 relax runtime gate，必須先用新的 patch + verify 證明它沒有破壞 `allowed_layers=0` guardrail，且 `entry_quality >= 0.55`。

- **Fallback if fail:**
  - 若 heartbeat 又把 q35 問題退回 `broader_bull_cohort_recalibration_candidate`，但 current 仍位於 exact-lane p90 內，視為 governance regression；
  - 若有人再次直接放寬 q35 gate 或下修 trade floor，卻沒有新的 calibration / attribution patch / verify，視為 contract regression；
  - 若 `profile_split` / exact-supported 狀態再漂移，視為 blocker；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 exact-lane formula review 再擴充成新 runtime 規則）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_1005_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/q35_scaling_audit.json`
     - `docs/analysis/q35_scaling_audit.md`
     - `data/feature_group_ablation.json`
     - `data/bull_4h_pocket_ablation.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若 `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`、`segmented_calibration.status = formula_review_required`、`piecewise_runtime_preview.applied = true`、`live_predict_probe.entry_quality = 0.5238 ± 誤差`、`allowed_layers_reason = entry_quality_below_trade_floor`、`support_blocker_state = exact_live_bucket_supported` 同時成立，下一輪不得再把焦點放回「有沒有 q35 calibration」；必須直接拆解剩餘 floor gap 的 component root cause。