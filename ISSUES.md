# ISSUES.md — Current State Only

_最後更新：2026-04-20 09:23:03 CST_

只保留目前有效問題；heartbeat 與本輪 patch 後的 current-state truth 必須覆蓋同步，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 heartbeat 已修復 `/execution` 首屏 initial-sync loading contract**
  - `web/src/pages/ExecutionConsole.tsx` 現在會在 `/api/status`、`/api/execution/overview`、`/api/execution/runs` 尚未完成首次同步前，統一顯示 `同步中 / 正在向 ... 取得 ...` loading copy。
  - 首屏不再先渲染 `尚未提供 blocker 摘要`、`unknown`、`尚未取得 bot profile cards`、`尚未建立 stateful run` 等假陰性文案；待資料到齊後再切回真實 runtime truth。
  - 驗證：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/execution` 首屏 + 3 秒後 re-check。
- **canonical current-live blocker 仍是 breaker-first truth**
  - `deployment_blocker=circuit_breaker_active` / `streak=191` / `recent_window_wins=0/50` / `additional_recent_window_wins_needed=15`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q00` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
- **recent canonical pathological slice 仍是 recent 100 rows**
  - `window=100` / `win_rate=0.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=-0.2363` / `avg_pnl=-0.0095`
  - `alerts=constant_target,regime_concentration,regime_shift` / `tail_streak=100x0`
- **support-aware patch 仍必須維持 reference-only**
  - `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready`
  - `reference_scope=bull|CAUTION` / `reference_source=bull_4h_pocket_ablation.bull_collapse_q35`
- **venue / source blocker 仍開啟**
  - venue：`live exchange credential / order ack lifecycle / fill lifecycle` 仍缺 runtime-backed proof
  - `fin_netflow`：`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `COINGLASS_API_KEY` 仍缺
- **leaderboard / governance 仍維持 dual-role contract**
  - `leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active`

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
- 目前真相：`deployment_blocker=circuit_breaker_active` / `streak=191` / `recent 50 wins=0/50` / `additional_recent_window_wins_needed=15`
- current-live bucket：`bucket=CAUTION|base_caution_regime_or_bias|q00` / `rows=0/50` / `gap=50` / `support_route_verdict=exact_bucket_unsupported_block`
- 下一步：維持 breaker release math 作為唯一 current-live 主 blocker；在 breaker 未解除前，不要把 q15/q35 support 或 floor-gap 升級成主敘事。
- 驗證：browser `/`、browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`

### P0. recent canonical pathological slice still dominates the breaker root cause
- 目前真相：`window=100` / `win_rate=0.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=-0.2363` / `avg_pnl=-0.0095`
- 病態切片：`alerts=constant_target,regime_concentration,regime_shift` / `tail_streak=100x0` / `top_shift_features=feat_local_bottom_score,feat_local_top_score,feat_dist_swing_high`
- 下一步：持續沿 recent pathological slice 追 target-path、adverse streak、top feature shifts；不要退回 generic leaderboard / venue 摘要。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`

### P1. support-aware patch must stay visible but reference-only
- 目前真相：`recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`
- live truth：current bucket 仍是 `q00` 且 exact support `0/50`，所以 patch 只能作治理 / 訓練參考，不得包裝成 deployable truth。
- 驗證：`/api/status`、`/execution/status`、`/lab`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`

### P1. venue readiness is still unverified
- 目前真相：`binance=config enabled + public-only + metadata OK` / `okx=config disabled + public-only + metadata OK`
- 缺口：`live exchange credential / order ack lifecycle / fill lifecycle`
- 下一步：在 Dashboard、Execution、Execution Status、Strategy Lab 持續明示 per-venue blockers，直到拿到 runtime-backed proof。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`

### P1. fin_netflow remains source_auth_blocked because COINGLASS_API_KEY is missing
- 目前真相：`quality_flag=source_auth_blocked` / `latest_status=auth_missing`
- 下一步：補上 `COINGLASS_API_KEY`，讓 forward snapshots 從 `auth_missing` 轉成成功資料，再觀察 coverage 是否開始前進。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`

### P1. leaderboard recent-window contract must remain stable and cron-safe
- 目前真相：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active`
- 下一步：守住 `/api/models/leaderboard` 與 Strategy Lab 的 bounded walk-forward / recent-two-year contract，不回退 placeholder-only 或模糊 backtest window。
- 驗證：browser `/lab`、`curl http://127.0.0.1:8001/api/models/leaderboard`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`

---

## Current Priority
1. **維持 breaker-first truth 與 current live bucket visibility across API / UI / docs**
2. **持續沿 recent canonical pathological slice 追根因，不把 root cause generic 化**
3. **守住 reference-only patch、leaderboard dual-role governance、venue/source blockers 可見性**
4. **守住 `/, /execution, /execution/status, /lab` 首屏 initial-sync contract，避免回到 `unknown / unavailable / 尚未提供 blocker 摘要` 假陰性**
