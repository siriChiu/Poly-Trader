# ISSUES.md — Current State Only

_最後更新：2026-05-15 04:08:07 CST_

只保留目前有效問題；本文件已按最新 heartbeat artifacts、runtime probe 與本輪產品化 patch 覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實

- **fast heartbeat #1232 已完成 collect + diagnostics refresh**
  - `Raw=33231 / Features=24418 / Labels=66426`；collect pipeline 本輪 `+2 raw / +2 features / +2 labels`，並補回 `1` 筆 OKX 4h continuity raw。
  - 歷史覆蓋仍達標：`2y_backfill_ok=True`；`simulated_pyramid_win=56.82%`。
  - runner 結果：`stats=2/2 passed`，`elapsed=13.1s`，`docs_sync.ok=True`，`auto_synced=True`。
- **唯一 current-live deployment blocker 仍是 exact-support 不足**
  - `deployment_blocker=under_minimum_exact_live_structure_bucket` / `signal=HOLD` / `allowed_layers=0` / `execution_guardrail_reason=under_minimum_exact_live_structure_bucket`。
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35` / `support=28/50` / `gap=22` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum`。
  - support progress：`status=stalled_under_minimum` / `delta_vs_previous=0` / `previous_rows=28` / `stagnant_run_count=5` / `stalled_support_accumulation=True` / `escalate_to_blocker=True` / `regression_basis=same_identity_same_semantic_signature`。
- **本輪產品化 patch 已落地：Dashboard support-stall visibility**
  - `ConfidenceIndicator` 現在直接顯示 support accumulation 停滯卡：目前樣本、最低門檻、缺口、連續停滯輪數、停滯原因與 operator action。
  - q35 current-live bucket 會明確提醒：分數重設 / base-stack redesign 仍是分數層治理參考，不能用 score-only floor-cross 替代 deployment closure。
  - `runtimeCopy` 已把 `stalled_under_minimum` / `stalled_support_accumulation` 中文化成「連續停滯 N 輪」而不是中性 `0` delta；Dashboard 型別已接受完整 `support_progress` 欄位。
- **high-conviction Top-K OOS gate 已是 fail-closed 實戰候選治理，不是 deploy 開關**
  - `data/high_conviction_topk_oos_matrix.json`：`rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidate_rows=6` / `artifact_freshness=fresh`。
  - nearest candidate：`logistic_regression / current_full / all / top_2pct`，`OOS ROI=0.9324` / `win_rate=86.21%` / `profit_factor=19.8864` / `max_drawdown=2.2%` / `worst_fold=0.2068` / `trades=58`，但仍 `not_deployable`，因 `support_route_not_deployable` + `deployment_blocker_active`。
- **source / venue blockers 仍開啟**
  - top source blockers：`fin_netflow(auth_missing, coverage=0.0%)` / `claw(auth_missing, coverage=14.7%)` / `claw_intensity(auth_missing, coverage=14.7%)` / `nest_pred(tls_verify_failed, coverage=16.3%)`。
  - venue readiness 仍缺 runtime-backed `live exchange credential / order ack lifecycle / fill lifecycle` proof；operator surfaces 必須繼續 fail-closed。

---

## Open Issues

### P0. current-live q35 exact support remains under minimum and remains the deployment blocker
- 目前真相：`CAUTION|base_caution_regime_or_bias|q35` only has `28/50` exact rows；`gap=22`；support 已連續 `5` 輪停在 `28`，且 `escalate_to_blocker=True`。
- 產品契約：任何 Dashboard / Strategy Lab / Execution / direct API 入口都不得把 proxy rows、reference-only patch、score-only floor-cross 或 breaker 舊敘事當成 deployment closure。
- 本輪補強：Dashboard confidence card 已把 support-stall blocker 直接操作員化，顯示停滯輪數與 q35 分數治理不可替代部署條件。
- 下一步：收集與目前 support identity 完全一致的 current-live exact rows；`rows >= 50` 前只能 shadow / observe / risk-off，不能 buy/add exposure。

### P0. high-conviction Top-K OOS gate must stay fail-closed until live support clears
- 目前真相：已有 OOS-pass candidate，但 `deployable_rows=0`；最接近部署候選只被 live guardrails 擋下，仍不可部署。
- 下一步：維持 Strategy Lab/API 以 nearest-deployable candidate 優先顯示，並持續把 `support_route_not_deployable` 與 `deployment_blocker_active` 列為 live gate failures。

### P1. q35 scoring/base-stack redesign remains score-layer only
- 目前真相：q35 audit 仍指出 `overall_verdict=bias50_formula_may_be_too_harsh`；redesign 可跨過 scoring floor，但 `allowed_layers=0` 且 current-live support 仍 `28/50`。
- 下一步：review q35 formula/base stack；任何分數改善都必須先通過 exact-support 與 execution guardrail，才能進入 deploy candidate。

### P1. leaderboard / governance dual-role contract must remain stable
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `payload_source=latest_persisted_snapshot`。
- 下一步：防止 Strategy Lab 回退到 placeholder-only 或把 global ranking 誤當 support-aware production profile。

### P1. model stability and IC drift still require governance, not blind model changes
- 目前真相：`cv_accuracy=0.6344` / `cv_std=0.0648` / `cv_worst=0.5695`；`TW-IC 23/30` vs `Global IC 19/30`，信號仍強依賴近期 regime。
- 下一步：只比較 support-aware / shrinkage / regime-gated profiles；不要把 current blocker 誤判成單純模型 parity 問題。

### P1. source and venue readiness blockers remain unresolved
- 目前真相：`fin_netflow` 仍因 `COINGLASS_API_KEY` 缺失 auth-blocked；`nest_pred` 仍是 TLS trust failure；OKX/Binance 仍缺實單 credential、order ack、fill lifecycle proof。
- 下一步：補 credentials / TLS trust / venue lifecycle proof；在 proof 完成前，UI/API 必須繼續顯示 blocker 並 fail-closed。

---

## Current Priority

1. **補足 current-live q35 exact support：28/50 → 50/50**。
2. **保持 support-stall blocker 在 Dashboard / Strategy Lab / Execution / docs 中直觀可見**，不得被 `0 delta` 或 score-only redesign 淡化。
3. **維持 Top-K OOS gate 的 fail-closed 分層**：OOS-pass ≠ deployable；live support gate 未過前只允許 observe/shadow。
4. **守住 venue/source proof blocker 與 leaderboard dual-role governance**。
