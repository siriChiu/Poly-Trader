# ISSUES.md — Current State Only

_最後更新：2026-04-16 00:47 UTC_

只保留目前仍有效的問題；不保留歷史敘事。

---

## 系統現況
- heartbeat fast：Raw / Features / Labels = **21795 / 13224 / 43598**
- 本輪 collect 實際前進：**+1 raw / +1 feature / +3 labels**
- canonical target `simulated_pyramid_win` = **0.5808**
- Global IC = **18 / 30**；TW-IC = **25 / 30**
- current live path：`bull / CAUTION / q35`
- live signal：`HOLD`
- `entry_quality = 0.5544`，`entry_quality_label = C`，`allowed_layers = 1`
- q35 discriminative redesign：**已套用且 current row 對齊 live probe**
- current live exact support：**7 / 50**（`CAUTION|structure_quality_caution|q35`）
- q15 audit：**目前不是 active lane**，只能作 standby route readiness 參考
- governance contract：`dual_role_governance_active`
  - leaderboard global winner：`core_plus_4h`
  - train/runtime production profile：`core_plus_macro`
- 最新 train：`train_accuracy = 0.6457`，`cv_accuracy = 0.6978`，`cv_std = 0.1161`，`cv_worst = 0.5445`
- recent drift primary window = **250**，alerts = `label_imbalance`, `regime_concentration`, `regime_shift`
- source blocker：`fin_netflow = auth_missing`

---

## Open Issues

### P1. current live q35 exact support 仍低於 minimum（7 / 50）
**現象**
- `current_live_structure_bucket = CAUTION|structure_quality_caution|q35`
- `live_current_structure_bucket_rows = 7`
- `minimum_support_rows = 50`
- gap = **43**
- `support_progress.status = no_recent_comparable_history`
- q15 已不是 current-live lane，舊 q15 blocker 不可再當本輪主 blocker

**影響**
- 雖然 q35 runtime 已因 discriminative redesign 跨過 trade floor，**但 exact support 仍未達 deployment-grade**。
- 目前可宣告的是「runtime 語義改善已落地」，不能宣告「support blocker 已解除」。

**本輪 patch / 證據**
- 已重跑 fast heartbeat，current live bucket 從上一輪的 q15 轉為 **q35**。
- 已驗證 `data/q35_scaling_audit.json`：
  - `overall_verdict = bias50_formula_may_be_too_harsh`
  - `deployment_grade_component_experiment.verdict = runtime_patch_crosses_trade_floor`
- 已驗證 `data/live_predict_probe.json`：
  - `entry_quality = 0.5544`
  - `allowed_layers = 1`
  - `q35_discriminative_redesign_applied = true`
- 已驗證 `data/q15_support_audit.json`：`scope_applicability.status = current_live_not_q15_lane`

**下一步**
- 每輪先確認 current live bucket 是否仍是 q35；若切換，立即重寫 blocker
- 主追 `current_live_structure_bucket_rows` 是否從 **7 / 50** 持續累積
- 在 support 未達標前，q35 redesign 只算 runtime patch 成功，不算 deploy closure

### P1. 模型穩定度仍不足
**現象**
- `cv_accuracy = 0.6978`
- `cv_std = 0.1161`
- `cv_worst = 0.5445`
- `train_accuracy = 0.6457`

**影響**
- 平均表現尚可，但 dispersion 仍大，最差 fold 仍偏弱。
- 在 current exact support 未達標時，不能把單輪高分數當 deployment 訊號。

**本輪 patch / 證據**
- 已重跑 feature-group / bull-pocket / candidate probe artifacts，治理結論仍一致：
  - leaderboard 保留 `core_plus_4h`
  - production/runtime 保留 `core_plus_macro`
- 驗證：`data/leaderboard_feature_profile_probe.json` 仍為 `dual_role_governance_active`

**下一步**
- 優先比較 support-aware profile 與 global shrinkage winner 在 **current q35 bucket** 的 robustness
- 目標是壓低 `cv_std`、抬高 `cv_worst`，不是新增更多表層參數

### P1. recent regime drift 仍明顯（TW-IC 25 vs Global IC 18）
**現象**
- primary drift window = **250**
- dominant regime = **bull 100%**
- `interpretation = distribution_pathology`
- 最近 250 筆 `win_rate = 0.8920`，明顯高於 full sample `0.6432`

**影響**
- 近期 edge 高度依賴 bull concentration；若直接外推成全域 closure，會過度樂觀。
- 本輪 q35 current-live 改善，不能掩蓋近期 window 分布污染風險。

**本輪 patch / 證據**
- 已重跑 `recent_drift_report.py` 並刷新 `data/recent_drift_report.json`
- 驗證：drift report 仍明確標記 `label_imbalance + regime_concentration + regime_shift`

**下一步**
- 持續用 regime-aware 解讀 current q35 runtime 成果
- 若 q35 support 未同步累積，禁止把 recent bull pocket 當成 deployment 放行證據

### P2. sparse-source blocker 仍存在
**現象**
- `fin_netflow`：`auth_missing`
- blocked sparse features = **8**

**影響**
- 不是本輪主 blocker，但仍限制研究特徵成熟度與 coverage 擴張。

**下一步**
- 待 current q35 support / model stability 收斂後再處理

---

## Not Issues
- q15 support route **不是 current-live 主 blocker**；目前只保留為 standby route readiness 參考
- q35 discriminative redesign **不是 blocker**；本輪已驗證它讓 current row 跨過 trade floor
- circuit breaker：**未觸發**
- `dual_role_governance_active`：**不是 parity blocker**，目前是健康治理分工

---

## Current Priority
1. 以 **current live q35 bucket** 為主追 exact support / governance readiness
2. 維持 q35 runtime redesign 已落地，但不把它誤報成 deploy closure
3. 壓低 `cv_std`、抬高 `cv_worst`
4. 最後才處理 sparse-source auth/archive

---

## Next Gate Input
- **Next focus**：`q35 current live bucket support`, `q35 redesign 後的 deployment verify`, `model stability`
- **Success gate**：
  - current live q35 exact support 持續上升，不再停在 **7 / 50**
  - current live bucket 仍為 q35 時，live probe 維持 `entry_quality >= 0.55` 且 `allowed_layers > 0`
  - `cv_std` 下降或 `cv_worst` 提升
- **Fallback if fail**：
  - 若 support 仍停滯：升級成 governance blocker
  - 若 live bucket 再切換：立即重寫 issue 與 roadmap，停止沿用 q35 anchor
  - 若 runtime 再跌回 `entry_quality < 0.55`：重新審核 q35 redesign 是否只是假陽性 pocket
- **Carry-forward input for next heartbeat**：
  1. 先確認 current live bucket 是否仍是 `CAUTION|structure_quality_caution|q35`；若已切換，立刻改寫 blocker，不可沿用 q35 敘事。
  2. 先讀 `data/live_predict_probe.json`、`data/q35_scaling_audit.json`、`data/leaderboard_feature_profile_probe.json`：確認 q35 redesign 是否仍套用、support 是否仍低於 minimum、治理是否仍是 `dual_role_governance_active`。
  3. 只有在 q35 exact support 實質增加時，才把 runtime improvement 往 deployability 推進；否則明確升級 blocker。
