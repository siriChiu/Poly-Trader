# ISSUES.md — Current State Only

_最後更新：2026-04-15 21:56 UTC — Heartbeat #fast（本輪修正 `support_progress` 歷史承接：fast label 不再把上一輪 fast summary 誤去重，且可從 legacy `governance_contract` 回填 route/minimum support，讓 q35 exact support 由假 `no_recent_comparable_history` 改為真實 `regressed_under_minimum`。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 追 q35 current-live exact support（13/50 → 50/50）；
  2. 觀察 `support_progress` 是否從 `no_recent_comparable_history` 轉成 `accumulating` 或 `stalled_under_minimum`；
  3. 維持 q15 standby route truthfulness。
- **Success gate**
  1. next run 至少留下 1 個與 **q35 exact support** 或 **support_progress blocker governance** 直接相關的 patch / artifact / verify；
  2. `governance_contract` 與 `support_progress` 必須仍存在且語義正確；
  3. `q35_scaling_audit.deployment_grade_component_experiment.entry_quality_ge_0_55=true`、`allowed_layers_gt_0=true`；
  4. `live_predict_probe.allowed_layers = 1` 且 `q35_discriminative_redesign_applied = true`。
- **Fallback if fail**
  - 若 governance contract 或 support_progress 消失，回查 probe / summary persistence；
  - 若 q35 exact support 在可比 heartbeat 仍長期停在 `<50` 且 `support_progress.stalled_under_minimum=true`，升級成 `#PROFILE_GOVERNANCE_STALLED` blocker；
  - 若 current live row 離開 q35，改追 active lane。

### 本輪承接結果
- **已處理**
  - `scripts/hb_leaderboard_candidate_probe.py`
    - 修正 `support_progress` 歷史承接：同為 `fast` 的前一輪 summary 不再被 heartbeat label 去重誤吃掉；
    - 舊 summary 若只把 `support_governance_route / minimum_support_rows` 放在 `governance_contract`，現在也能回填成可比歷史；
    - 本輪 machine-read 結果已由假 `no_recent_comparable_history` 改成真實 `regressed_under_minimum`。
  - `tests/test_hb_leaderboard_candidate_probe.py`
    - 新增 regression test，鎖住「重用前一輪 fast summary」與 legacy governance fallback 行為。
  - `ARCHITECTURE.md`
    - 已同步補上 support-progress 歷史承接約束，避免下輪再退回假不可比歷史。
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **42 passed**
  - `source venv/bin/activate && HB_RUN_LABEL=fast python scripts/hb_leaderboard_candidate_probe.py` → **通過**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast` → **通過**
- **本輪 machine-read 結論**
  - `leaderboard_feature_profile_probe.alignment.governance_contract.verdict = dual_role_governance_active`
  - `support_governance_route = exact_live_bucket_present_but_below_minimum`
  - `support_progress.status = regressed_under_minimum`
  - `support_progress.current_rows = 11 / previous_rows = 13 / minimum_support_rows = 50 / gap = 39 / delta_vs_previous = -2`
- **本輪明確不做**
  - 不把 leaderboard ranking 直接切到 production profile；exact support 未達標。
  - 不把 q15 standby route 寫成 current-live closure；current row 仍是 q35。
  - 不先處理 `fin_netflow` auth blocker；它仍是 source blocker，但不是本輪主 closure。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_leaderboard_candidate_probe.py`
    - `support_progress` 現在會保留上一輪同 label=`fast` 的 summary 作比較基線；
    - candidate history 會從 legacy `governance_contract` 回填 `support_governance_route / minimum_support_rows`；
    - 避免 q35 exact support regression 被誤判成 `no_recent_comparable_history`。
  - `tests/test_hb_leaderboard_candidate_probe.py`
    - 新增 `test_summarize_support_progress_reuses_previous_fast_summary`。
  - `ARCHITECTURE.md`
    - 補上 support-progress 歷史承接與 legacy comparability contract。
- **Tests（已通過）**
  - `python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **42 passed**
- **Runtime verify（已通過）**
  - `HB_RUN_LABEL=fast python scripts/hb_leaderboard_candidate_probe.py` → support_progress 變成 **`regressed_under_minimum`**，不再是假 `no_recent_comparable_history`
  - `python scripts/hb_parallel_runner.py --fast` → **通過**，`heartbeat_fast_summary.json` / `leaderboard_feature_profile_probe.json` 已同步刷新

### 資料 / 新鮮度 / canonical target
- Heartbeat #fast：
  - Raw / Features / Labels：**21788 / 13217 / 43581**
  - canonical target `simulated_pyramid_win`：**0.5806**
  - 240m labels：**21934 rows / target_rows 13012 / freshness=expected_horizon_lag**
  - 1440m labels：**12562 rows / target_rows 12562 / freshness=expected_horizon_lag**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / drift
- Global IC：**18/30 pass**
- TW-IC：**26/30 pass**
- drift primary window：**250**
  - alerts：`label_imbalance`, `regime_concentration`, `regime_shift`
  - interpretation：**distribution_pathology**
  - dominant_regime：**bull 100.0%**
  - win_rate：**0.8920**

### Live contract / q35 / q15 / governance
- **q35 current-live path（runtime 仍健康，但 exact support 回落）**
  - structure bucket：**`CAUTION|structure_quality_caution|q35`**
  - `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`
  - `deployment_grade_component_experiment.verdict = runtime_patch_crosses_trade_floor`
  - `entry_quality=0.5588` / `allowed_layers=1` / `q35_discriminative_redesign_applied=true`
  - `live_predict_probe.decision_quality_calibration_scope = regime_label`
- **profile governance（語義正確，但 current-live exact support 更差）**
  - leaderboard：`core_plus_4h`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `governance_contract.verdict = dual_role_governance_active`
  - `governance_contract.treat_as_parity_blocker = false`
  - `support_governance_route = exact_live_bucket_present_but_below_minimum`
  - current live q35 exact bucket：**11 / 50**（上一輪 fast 為 **13 / 50**）
  - `support_progress.status = regressed_under_minimum`
  - `support_progress.delta_vs_previous = -2`
- **q15 support（仍為 standby）**
  - `q15_support_audit.scope_applicability.status = current_live_not_q15_lane`
  - `support_route.verdict = exact_bucket_present_but_below_minimum`
  - `floor_cross_legality.verdict = floor_crossed_but_support_not_ready`
  - q15 只能維持 governance reference / standby route，不能寫成 current-live closure。

### Source blockers
- `fin_netflow`：**auth_missing / coverage 0.0% / archive_window_coverage 0.0%**
- 其他 blocked sparse features 仍以 `archive_required / snapshot_only` 為主

---

## 目前有效問題

### P1. current live bull q35 exact support 由 13/50 再退到 11/50，dual-role governance 仍不能關閉
**現象**
- `support_governance_route = exact_live_bucket_present_but_below_minimum`
- `live_current_structure_bucket_rows = 11 / minimum_support_rows = 50`
- `live_current_structure_bucket_gap_to_minimum = 39`
- `support_progress.status = regressed_under_minimum`
- `support_progress.previous_rows = 13 / delta_vs_previous = -2`

**判讀**
- 真正 blocker 仍是 **q35 exact support 不足，而且本輪確認是回落，不是歷史不可比**。
- dual-role governance 仍是正確語義；但 current-live support 既未累積也未持平，下一輪必須優先追 root cause（lane/bucket 切換或 artifact 退化）。

---

### P1. q15 route 仍是 standby governance，不可誤寫成 current-live closure
**現象**
- `q15_support_audit.scope_applicability.status = current_live_not_q15_lane`
- `support_route.verdict = exact_bucket_present_but_below_minimum`
- `floor_cross_legality.legal_to_relax_runtime_gate = false`

**判讀**
- q15 仍不是 active lane。
- 即使 floor 已跨過，也不能用 proxy / standby route 解除 current-live blocker。

---

### P1. sparse-source blocker 仍存在，`fin_netflow` 仍是 auth blocker
**現象**
- `fin_netflow`: `auth_missing`, `coverage=0.0%`, `archive_window_coverage_pct=0.0%`

**判讀**
- 仍是 source blocker。
- 但優先級低於 current-live q35 exact support regression 與 q15 truthful governance。

---

## 本輪已清掉的問題

### RESOLVED. `support_progress` 把上一輪 fast summary 誤當重複，導致 q35 regression 被錯報成 `no_recent_comparable_history`
**修前**
- `HB_RUN_LABEL=fast` 時，probe 會把前一輪 `heartbeat_fast_summary.json` 直接去重；
- 舊 summary 若把 `support_governance_route / minimum_support_rows` 放在 `governance_contract`，也不會被拿來做 comparability；
- 結果 q35 exact support 明明已經從 13 回落，machine-read 卻仍報 `no_recent_comparable_history`。

**本輪 patch + 證據**
- `scripts/hb_leaderboard_candidate_probe.py`
  - 同 label=`fast` 的前一輪 summary 現在可重用；
  - 會從 legacy `governance_contract` 回填 `support_governance_route / minimum_support_rows`；
- `tests/test_hb_leaderboard_candidate_probe.py`
  - 新增 fast-summary reuse regression；
- `python -m pytest ...` → **42 passed**
- `HB_RUN_LABEL=fast python scripts/hb_leaderboard_candidate_probe.py` → `support_progress.status = regressed_under_minimum`, `previous_rows = 13`, `delta_vs_previous = -2`

**狀態**
- **已修復**：support progression 目前已能正確承接上一輪 fast history。
- **尚未關閉的 blocker**：current q35 exact support 仍只有 **11 / 50**，且本輪是回落，不是累積。

---

## 本輪決策（收斂版）

### 策略後果表
| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 只在文件手寫「q35 support 退回 11/50」 | 改動小 | machine-read 仍錯，下一輪會再次誤判 | 治標 | 只做人工閱讀 | ❌ 不建議 |
| 修 `support_progress` 歷史承接與 legacy governance fallback | 直接把 q35 regression 轉成可治理訊號，下一輪能判斷是回落 / 停滯 / 累積 | 需要補測試與 contract 文件 | 治本 | 現在主 blocker 已從語義分歧收斂成 support readiness | ✅ 推薦 |
| 直接把 leaderboard 切到 production profile | 可能快速消除 split 表象 | exact support 未達標，會把 blocker 假裝成 closure | 治標 | exact bucket 已充分支持且治理已翻轉 | ❌ 本輪不建議 |

### 效益前提驗證
| 情境 | 效益 |
|---|---|
| 前一輪 fast summary 真的可被重用，且 legacy route/minimum 可回填 | ✅ 前提成立，本輪已落地，q35 regression 已 machine-read 化 |
| 仍把 dual-role governance 當 parity drift 主 blocker | ❌ 前提不成立，會偏離真正的 q35 exact support 問題 |
| exact support 未達標就直接切 leaderboard=production | ❌ 前提不成立，會把治理 blocker 假裝成 closure |

### 本輪要推進的 3 件事
1. 修正 `support_progress` 歷史承接，讓 fast heartbeat 能比較前一輪 fast summary。 ✅
2. 讓 legacy governance fields 也能餵給 `support_progress` comparability。 ✅
3. 重新把主 blocker 聚焦到 **q35 exact support regression 11/50**。 ✅

### 本輪不做
- 不把 leaderboard ranking 直接切到 production profile；
- 不把 q15 standby route 拉回主 closure；
- 不先做 sparse-source auth 修復。

---

## Next gate

- **Next focus:**
  1. 追 q35 current-live exact support regression 的 root cause（11/50 為何低於前一輪 13/50）；
  2. 確認下一輪 `support_progress` 是否繼續回落、轉成持平停滯、或重新恢復累積；
  3. 維持 q15 standby route truthfulness，不得把 inactive q15 lane 寫成 current-live closure。

- **Success gate:**
  1. 下一輪至少留下 1 個與 **q35 exact support regression / blocker governance** 直接相關的 patch / artifact / verify；
  2. `leaderboard_feature_profile_probe.alignment.support_progress` 必須持續 machine-read 顯示 `previous_rows / delta_vs_previous / status`；
  3. `governance_contract` 必須仍維持 `treat_as_parity_blocker=false`，直到 exact support 真正翻轉；
  4. `live_predict_probe` 仍維持 `entry_quality>=0.55`、`allowed_layers=1`、`q35_discriminative_redesign_applied=true`。

- **Fallback if fail:**
  - 若 `support_progress` 又退回 `no_recent_comparable_history`，直接回查 `hb_leaderboard_candidate_probe.py` 的 fast-history / governance fallback contract；
  - 若 q35 exact support 再連續回落或連續停在 `<50`，下一輪升級成 `#PROFILE_GOVERNANCE_STALLED` blocker；
  - 若 current live row 離開 q35，依 `scope_applicability` 改追 active lane，不得硬守 q35。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 support-progress comparability contract 再擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_fast_summary.json` 的 `leaderboard_candidate_diagnostics.support_progress`，確認是否仍為 `regressed_under_minimum / stalled_under_minimum / accumulating`；
  2. 再讀：
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
  3. 若 `support_governance_route = exact_live_bucket_present_but_below_minimum`：
     - `support_progress.status = accumulating` → 繼續追 exact support 累積；
     - `support_progress.status = stalled_under_minimum` → 升級 `#PROFILE_GOVERNANCE_STALLED` 評估；
     - `support_progress.status = regressed_under_minimum` → 先查 current bucket / route / exact rows 為何回落，再決定是否升級 blocker；
     - `support_progress.status = no_recent_comparable_history` → 視為 regression，先回查 probe 歷史承接 contract。
