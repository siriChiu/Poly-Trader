# ISSUES.md — Current State Only

_最後更新：2026-04-16 03:24 UTC_

只保留目前仍有效的問題；不保留歷史敘事。

---

## Step 0.5 承接（把上輪結論當本輪輸入）
- 已先對照上輪 carry-forward：`current live bucket / q35 support gate / blocker 語義 / dual-role governance`。
- 本輪先重讀並重跑：`data/live_predict_probe.json`、`data/q35_scaling_audit.json`、`data/leaderboard_feature_profile_probe.json`。
- 承接結果：**current live bucket 仍是 `CAUTION|structure_quality_caution|q35`**，但 support 不是回升，而是**停滯在 4 / 50**；因此本輪主 blocker 仍是 q35 exact support，不是 profile parity，也不是 q15。
- 本輪新增 patch 已落地：`scripts/issues.py` + `scripts/auto_propose_fixes.py` 現在會把 `next_actions` 正規化為單行 `action`，避免 auto-propose 對 current-state issues 輸出空白治理箭頭。

---

## 系統現況
- heartbeat collect 實際前進：**Raw +1 / Features +1 / Labels +24**
- 目前 DB：**Raw / Features / Labels = 21803 / 13232 / 43733**
- canonical 1440m 全樣本：**12697 rows / simulated_pyramid_win = 0.6467**
- 全庫 canonical label 平均：**simulated_pyramid_win = 0.5828**
- Global IC = **17 / 30**；TW-IC = **28 / 30**
- regime-aware IC：**Bear 5/8、Bull 6/8、Chop 4/8**
- 最新 train：`feature_profile = core_plus_macro`，`train_accuracy = 0.6457`，`cv_accuracy = 0.6978`，`cv_std = 0.1161`，`cv_worst = 0.5445`
- current live path：**bull / CAUTION / q35**
- live signal：**HOLD**
- live entry-quality：**0.5956（C）**
- `allowed_layers_raw = 1 → allowed_layers = 0`
- runtime / deployment blocker：`under_minimum_exact_live_structure_bucket`
- current live exact support：**4 / 50**（本輪 **持平**，未恢復累積）
- q35 redesign 狀態：**runtime 已跨 floor，但 deployment 仍被 support gate 擋住**
  - `q35_discriminative_redesign_applied = true`
  - `entry_quality_ge_0.55 = true`
  - `allowed_layers_gt_0 = true`
  - 但 final `allowed_layers = 0`，因 exact support 未達 minimum
- governance contract：`dual_role_governance_active`
  - leaderboard global winner：`core_only`
  - production/runtime profile：`core_plus_macro`
- recent drift primary window = **100**，alerts = `constant_target`, `regime_concentration`, `regime_shift`
- sparse-source blocker：`fin_netflow = auth_missing`

---

## Step 1 事實分類

### 已改善
1. **資料管線仍在前進**：本輪新增 `+1 raw / +1 features / +24 labels`，label freshness 維持正常 lookahead 狀態。
2. **q35 runtime 分數比上輪更高**：`entry_quality 0.5541 → 0.5956`，證明 redesign runtime lane 仍有效。
3. **auto-propose 治理輸出修復**：既有 current-state issues 的 `next_actions` 不再顯示成空白 action，heartbeat 可直接 machine-read / human-read 下一步。

### 惡化
1. **沒有新的 exact support 補進 q35 current lane**：current live exact support 仍是 **4 / 50**，沒有從 blocker 狀態往 deployment-grade 前進。
2. **recent drift 病態仍強**：最近 100 筆 canonical rows 仍是 `bull 100% + constant_target`，不能拿來當 deployment 證據。

### 卡住不動
1. **主 blocker 仍是 q35 exact support under minimum**。
2. **dual-role governance 仍存在**：global winner `core_only`，runtime 仍需 `core_plus_macro`。
3. **sparse-source auth blocker** 仍在背景，尚未進主線修復。

---

## Open Issues

### P0. recent canonical 100-row 視窗仍是 distribution pathology
**現象**
- `primary_window = 100`
- `win_rate = 1.0000`
- `dominant_regime = bull (100%)`
- alerts = `constant_target`, `regime_concentration`, `regime_shift`
- feature diagnostics：`frozen=3`, `compressed=27`, `unexpected_frozen=1 (feat_vix)`

**影響**
- 任何直接使用最近 bull pocket 的 calibration / deployment 結論都會失真。
- q35 live lane 的高勝率只能視為病態分布下的局部證據，不是 deployment closure。

**本輪 patch / 證據**
- 已刷新 `data/recent_drift_report.json`。
- auto-propose 已把 drift 病態保留為最高優先 current-state issue。

**下一步**
- 先做 recent canonical rows 的 feature variance / distinct-count / target-path drill-down。
- 在 drift 未解除前，維持 current live decision-quality guardrails。

### P1. current live q35 exact support 停滯在 4 / 50，仍是主 blocker
**現象**
- `current_live_structure_bucket = CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows = 4`
- `minimum_support_rows = 50`
- `gap_to_minimum = 46`
- 本輪狀態：**stalled_under_minimum**（不是 closure，也不是已恢復累積）

**影響**
- q35 現在仍是 current-live blocker。
- 只要 support 未補滿，runtime lane 即使跨 floor，也不能升級成 deployment-ready。

**本輪 patch / 證據**
- 已重跑 `scripts/hb_predict_probe.py`：
  - `entry_quality = 0.5956`
  - `allowed_layers_raw = 1`
  - final `allowed_layers = 0`
  - `deployment_blocker = under_minimum_exact_live_structure_bucket`
- 已重跑 `scripts/hb_leaderboard_candidate_probe.py`：
  - `live_current_structure_bucket_rows = 4`
  - `support_progress.status = stalled_under_minimum`
- 已完成 fast heartbeat 並刷新 `data/heartbeat_fast_summary.json`。

**下一步**
- 每輪先確認 current live bucket 是否仍是 q35；若切換，立即重寫 blocker。
- support 未增加前，禁止把 q35 redesign 當 deployment closure。

### P1. q35 redesign 已證明能跨 floor，但仍只能算 support-blocked runtime patch
**現象**
- `entry_quality = 0.5956`
- `trade_floor = 0.55`
- `allowed_layers_raw = 1`
- `allowed_layers = 0`
- `deployment_blocker = under_minimum_exact_live_structure_bucket`

**影響**
- 問題不再是「floor 沒過」，而是「exact support 不夠，runtime 必須繼續 guardrail」。
- 若文件只報 `entry_quality` 而不報 blocker，會製造假 closure。

**本輪 patch / 證據**
- 已重跑 `data/q35_scaling_audit.json` 與 `data/live_predict_probe.json`，兩者都確認 runtime redesign 已跨 floor。
- `scripts/issues.py` / `scripts/auto_propose_fixes.py` patch 已讓 governance action 不再空白，current-state blocker 可直接被讀出。
- 驗證：`python -m pytest tests/test_issues_tracker.py tests/test_auto_propose_fixes.py tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **62 passed**。

**下一步**
- 維持 q35 redesign 為已驗證 runtime candidate。
- 但在 exact support ≥ 50 前，禁止把它升級成 deployment closure。

### P1. model stability / profile split 仍需治理，但不是本輪主 blocker
**現象**
- `cv_accuracy = 0.6978`
- `cv_std = 0.1161`
- `cv_worst = 0.5445`
- global winner = `core_only`
- production/runtime = `core_plus_macro`
- governance = `dual_role_governance_active`

**影響**
- 這仍是治理 split，不是 parity drift。
- 在 q35 support 未達標前，不能把 leaderboard global winner 當 runtime closure。

**本輪證據**
- 已重跑 `scripts/hb_leaderboard_candidate_probe.py`，split 仍存在。
- `blocked_candidate_profiles[0].blocker_reason = under_minimum_exact_live_structure_bucket`。

**下一步**
- 保持 dual-role governance 明寫。
- support 未補滿前，不先把 profile split 升級成主 blocker。

### P2. sparse-source blocker 仍存在
**現象**
- `fin_netflow = auth_missing`
- blocked sparse features = **8**

**影響**
- 不是本輪 current-live blocker，但仍限制 feature maturity 與 coverage 擴張。

**下一步**
- 待 q35 support/runtime blocker 收斂後再處理。

---

## Not Issues
- **q15 current-live blocker**：本輪不活躍；q15 仍只作 standby / research route
- **q35 redesign 本身**：不是失敗項；真正 blocker 是 exact support 未達 minimum
- **dual_role_governance_active**：不是 parity blocker
- **circuit breaker**：本輪未觸發

---

## Current Priority
1. 以 **current live q35 bucket** 為主追 exact support / deployment blocker
2. 明確區分「q35 redesign 已跨 floor」與「q35 lane 已可部署」
3. 保持 drift 病態解讀與 dual-role governance 明寫
4. 最後才處理 sparse-source auth/archive

---

## Next Gate Input
- **Next focus**：`q35 current live bucket support`, `q35 redesign deployment legality`, `recent canonical pathology drill-down`
- **Success gate**：
  - current live q35 exact support **高於本輪 4 / 50**
  - live probe 維持 `entry_quality >= 0.55`、`allowed_layers_raw > 0`，且 blocker 仍正確標成 `under_minimum_exact_live_structure_bucket`（直到 support 達標）
  - recent pathology drill-down 能指出一個可驗證 root cause（feature freeze/compression 或 narrow-scope pathology），並留下 patch / verify 證據
- **Fallback if fail**：
  - 若 q35 support 下一輪仍停在 4 或再回落：升級為明確 governance blocker
  - 若 live bucket 再切換：立即重寫 issue / roadmap，停止沿用 q35 敘事
  - 若 drift 仍只報數字沒有 root-cause patch：升級為 `#HEARTBEAT_EMPTY_PROGRESS` 類治理失敗
- **Carry-forward input for next heartbeat**：
  1. 先確認 current live bucket 是否仍是 `CAUTION|structure_quality_caution|q35`；若已切換，立刻改寫 blocker，不可沿用 q35 敘事。
  2. 先讀 `data/live_predict_probe.json`、`data/q35_scaling_audit.json`、`data/leaderboard_feature_profile_probe.json`、`data/recent_drift_report.json`，確認 q35 lane 是否仍 active、exact support 是否仍低於 50、drift 是否仍是 100-row bull pathology。
  3. 先檢查 live blocker 語義是否仍是 `under_minimum_exact_live_structure_bucket`；若退回其他 blocker 名稱，先修語義 / probe / candidate diagnostics，再談 closure。
  4. 只有在 q35 exact support 實質增加時，才把 q35 redesign 往 deployment 驗證推進；否則明確維持 support-blocked state，不可只報告跨 floor 分數。
  5. 直接檢查 recent pathology 的 frozen / compressed 特徵（至少 `feat_vix`, `feat_body`, `feat_ear`, `feat_tongue`, `feat_atr_pct`），留下一個 root-cause patch 或明確 blocker。