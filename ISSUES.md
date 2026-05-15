# ISSUES.md — Current State Only

_最後更新：2026-05-15 23:18:43 CST_

只保留目前有效產品化問題；本檔以 `heartbeat #1252`、最新 `hb_predict_probe.py`、`live_decision_quality_drilldown.py`、targeted tests 的結果覆寫。

---

## 當前主線事實
- **Heartbeat #1252 fast diagnostics 已完成**：`Raw=33285 / Features=24472 / Labels=66532`，`simulated_pyramid_win_rate=56.81%`，最新 raw timestamp `2026-05-15 15:02:20.860934`。
- **current-live deployment blocker**：`under_minimum_exact_live_structure_bucket`；目前 live row 為 `bear / BLOCK / BLOCK|structure_quality_block|q00`，`signal=HOLD`，`allowed_layers=0`。
- **exact-support truth**：`current_live_structure_bucket_rows=32 / minimum_support_rows=50 / gap=18`，`support_route_verdict=exact_bucket_present_but_below_minimum`，`support_governance_route=exact_live_bucket_present_but_below_minimum`，`support_route_deployable=false`。
- **support progress 已升級為停滯 blocker**：`status=stalled_under_minimum`，`stagnant_run_count=4`，`stalled_support_accumulation=true`，`escalate_to_blocker=true`；同一 support identity 仍未補滿 50 筆。
- **q35 audit 不是本輪主 blocker**：`q35_scaling_audit.overall_verdict=reference_only_current_bucket_outside_q35`；current live row 已離開 q35 lane，q35 只能作 reference-only calibration artifact。
- **reference patch 必須維持 reference-only**：`core_plus_macro_plus_all_4h` 來自 `bull|CAUTION` / `bull_4h_pocket_ablation.bull_collapse_q35`，但 current live 是 `bear|BLOCK` q00；不可升級為 current-live deploy patch。
- **recent diagnostics**：primary window `500`，`win_rate=67.6%`，`dominant_regime=chop(75.4%)`，`avg_quality=+0.3198`，`avg_pnl=+0.0069`，alerts=`regime_shift`。
- **本輪 patch**：`scripts/live_decision_quality_drilldown.py` 將 current-live support contract 提升到 top-level JSON：`current_live_structure_bucket(_rows) / exact_live_structure_bucket_rows / minimum_support_rows / current_live_structure_bucket_gap_to_minimum / support_governance_route / support_route_deployable / support_progress`，避免 API/docs/operator surfaces 只能從 nested blocker 猜測。
- **operator copy guardrail**：`tests/test_server_startup.py` 更新為鎖定 operator-facing summary 使用繁中 humanized labels，並禁止 raw backend enum（例如 `CAUTION|...`、`bull|ALLOW`）外洩到 runtime closure summary。

---

## Open Issues

### P0 — current-live q00 exact support under minimum（唯一 current-live deployment blocker）
- 現況：`BLOCK|structure_quality_block|q00` exact support `32/50`，缺口 `18`；`allowed_layers=0`，買入 / 加倉不可放行。
- 風險：support accumulation 已停滯（`stagnant_run_count=4`），若只顯示 nested blocker 或 reference patch，operator 容易誤判為部署閉環。
- 下一步：累積或回放同一 support identity 的 exact rows；在 `rows>=50` 且 runtime readiness 通過前，保持 fail-closed。

### P0 — high-conviction top-k OOS gate 仍被 current-live support 擋下
- 現況：`data/high_conviction_topk_oos_matrix.json` fresh；`deployable_rows=0`，`risk_qualified_rows=6`，`runtime_blocked_candidates=6`。
- nearest candidate：`logistic_regression / top_2pct`，`oos_roi=0.9324`，`win_rate=86.21%`，`profit_factor=19.8864`，`max_drawdown=0.022`，但仍因 q00 exact support `32/50` 為 `not_deployable`。
- 下一步：維持 Strategy Lab / leaderboard 為「runtime-blocked OOS pass」而非 deployable。

### P1 — support-aware patch reference-only outside current live scope
- 現況：`recommended_patch=core_plus_macro_plus_all_4h`，`status=reference_only_non_current_live_scope`，`reference_scope=bull|CAUTION`，current live=`bear|BLOCK`。
- 下一步：Dashboard / Lab / drilldown / docs 都要顯示「僅治理參考」，不得替代 q00 exact-support minimum rows。

### P1 — OKX / venue readiness still unverified
- 現況：OKX 只有 metadata/public proof；`live exchange credential / order ack lifecycle / fill lifecycle` 未具 runtime-backed proof。
- 下一步：維持 venue readiness fail-closed；UI 需要求 `runtime_ready=true` 且無 blocker 才可宣稱 readiness。

### P1 — sparse source blockers
- `fin_netflow`：`source_auth_blocked/auth_missing`，需要 `COINGLASS_API_KEY` 後才可恢復 ETF flow snapshots。
- `nest_pred`：`source_tls_verify_failed/tls_verify_failed`，必須修 TLS trust chain；不允許 insecure production fallback。
- `claw / claw_intensity`：仍有 auth/coverage blockers，保持 forward archive 可見但不可偽裝完整。

---

## 本輪驗證證據
- `python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_predict_probe.py tests/test_runtime_closure_copy.py tests/test_server_startup.py tests/test_frontend_decision_contract.py -q` → **170 passed**。
- `python scripts/heartbeat_harness_check.py --format text` → **RESULT: PASS**。
- `python scripts/hb_predict_probe.py` → generated `data/live_predict_probe.json`，確認 `deployment_blocker=under_minimum_exact_live_structure_bucket`、`support=32/50`、`gap=18`。
- `python scripts/live_decision_quality_drilldown.py` → generated `data/live_decision_quality_drilldown.json` + `docs/analysis/live_decision_quality_drilldown.md`，top-level support fields 已存在。

---

## Current Priority
1. 補滿或回放 current-live q00 exact support：`32/50 → 50/50`。
2. 維持 top-level support contract 在 probe / drilldown / API / docs 可 machine-read。
3. 保持 reference-only patch、q35 audit、top-k OOS candidate 不被誤升級為 deployable。
4. 繼續 venue/source readiness proof；沒有 credential / ack / fill proof 前保持 fail-closed。
