# ISSUES.md — Current State Only

_最後更新：2026-04-20 00:06:40 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 fast heartbeat 已完成閉環**：`Raw=31149 / Features=22567 / Labels=62712`；本輪 collect 實際新增 `+1 raw / +2 features / +21 labels`，資料管線不是 frozen。
- **canonical current-live blocker 仍只有 breaker**
  - `deployment_blocker=circuit_breaker_active`
  - `recent 50 wins=1/50`
  - `required_recent_window_wins=15`
  - `additional_recent_window_wins_needed=14`
  - `streak=30`
  - `allowed_layers=0`
  - `runtime_closure_state=circuit_breaker_active`
- **current live q35 support 仍不足，patch 只能 reference-only**
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
  - `current_live_structure_bucket_rows=1 / minimum_support_rows=50 / gap_to_minimum=49`
  - `support_route_verdict=exact_bucket_present_but_below_minimum`
  - `recommended_patch=core_plus_macro_plus_all_4h`
  - `recommended_patch_status=reference_only_until_exact_support_ready`
  - `reference_source=bull_4h_pocket_ablation.bull_collapse_q35`
- **recent canonical 250 rows 仍是 distribution pathology**
  - `win_rate=0.0040 (1/250)`
  - `dominant_regime=bull(100%)`
  - `avg_pnl=-0.0091`
  - `avg_quality=-0.2724`
  - `avg_drawdown_penalty=0.3647`
  - `alerts=['label_imbalance','regime_concentration','regime_shift']`
  - `tail_streak=30x0`
  - top shifts=`feat_eye`、`feat_local_top_score`、`feat_rsi14`
  - new compressed=`feat_vwap_dev`
- **leaderboard / governance 仍健康**
  - `leaderboard_count=6 / comparable_count=6 / placeholder_count=0`
  - top row=`rule_baseline / core_only / scan_backed_best`
  - `governance_contract=dual_role_governance_active`
  - `current_closure=global_ranking_vs_support_aware_production_split`
- **venue / source blockers 仍開啟**
  - venue：Binance / OKX 仍缺 `live exchange credential`、`order ack lifecycle`、`fill lifecycle`
  - source：`fin_netflow=source_auth_blocked`，根因仍是 `COINGLASS_API_KEY` 缺失
- **本輪產品化 patch：execution surfaces 的初次載入不再假裝 blocker unavailable**
  - `Dashboard.tsx`、`ExecutionConsole.tsx`、`ExecutionStatus.tsx`、`StrategyLab.tsx` 在第一次 `/api/status` 尚未返回前，現在統一顯示 `同步中 / 正在同步 /api/status`。
  - 修掉初始首屏把 `current live blocker / metadata freshness / reconciliation` 誤渲染成 `unavailable / none / unknown` 的假陰性 UX。
  - 這個 patch 直接強化 breaker-first truth：operator 在頁面剛打開時，不會被錯誤的「目前沒有 blocker」或「metadata unavailable」誤導。
- **本輪驗證已完成**
  - `pytest tests/test_frontend_decision_contract.py -q` → `19 passed`
  - `cd web && npm run build` → `tsc + vite build pass`
  - browser 首屏重查 `/`、`/execution/status`、`/lab`：初次載入已看到 `同步中` loading copy，而不是 `unavailable / none / unknown`
  - `curl http://127.0.0.1:8000/api/status`：仍回傳 breaker-first current-live truth、q35 `1/50` support、reference-only patch、venue blockers

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=1`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=14`
- `streak=30`
- `allowed_layers=0`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若 `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 任一 surface 把 q35 support、reference-only patch 或 venue blockers 排到 breaker release math 前面，operator 會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth across UI / probe / drilldown / docs；任何前端初次載入也不得回退成 `unavailable` 假陰性。
- 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`。

### P0. recent canonical 250 rows remains a distribution pathology
**現況**
- `recent_window=250`
- `win_rate=0.0040`
- `dominant_regime=bull`
- `dominant_regime_share=1.0000`
- `avg_pnl=-0.0091`
- `avg_quality=-0.2724`
- `avg_drawdown_penalty=0.3647`
- `alerts=['label_imbalance','regime_concentration','regime_shift']`
- `tail_streak=30x0`
- top feature shifts=`feat_eye`、`feat_local_top_score`、`feat_rsi14`
- new compressed=`feat_vwap_dev`

**風險**
- 若 heartbeat 把 blocker generic 化成 leaderboard / venue 話題，就會繼續錯過真正的 pathological slice。

**下一步**
- 直接沿 recent canonical rows 做 target-path / feature-shift / scope-pathology root-cause；不要把主敘事轉成 generic leaderboard 或 venue 問題。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. q35 support-aware patch must stay visible but reference-only until exact support is ready
**現況**
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=1 / minimum_support_rows=50`
- `gap_to_minimum=49`
- `support_route_verdict=exact_bucket_present_but_below_minimum`
- `recommended_patch=core_plus_macro_plus_all_4h`
- `recommended_patch_status=reference_only_until_exact_support_ready`

**風險**
- 若任何 surface 把這個 artifact-backed patch 誤讀成已可部署的 current truth，就會再次製造 current-live split-brain。

**下一步**
- 維持 patch visibility，但永遠排在 breaker-first blocker 後；exact support 未達門檻前，只能當治理 / 訓練參考。
- 驗證：browser `/`、browser `/lab`、`python scripts/live_decision_quality_drilldown.py`、`data/bull_4h_pocket_ablation.json`。

### P1. venue readiness is still unverified
**現況**
- `binance=config enabled + public-only + metadata OK`
- `okx=config disabled + public-only + metadata OK`
- 缺的 runtime proof：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成摘要字串或在初次載入時短暫消失，使用者會被誤導成已可實盤。

**下一步**
- 維持 per-venue blockers 在 `/`、`/execution`、`/execution/status`、`/lab` 顯式可見，直到三項 runtime proof 都被真實 artifact 支撐。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow=source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2620`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先把 `auth_missing` 轉成成功 snapshot，再評估是否需要額外歷史 backfill。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`、下輪 heartbeat source blockers。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +2 features / +21 labels`。
- **leaderboard placeholder-only / split-brain**：不是；目前 `count=6 / comparable_count=6 / placeholder_count=0`，治理語義穩定。
- **bull pocket fast-mode timeout**：不是 current issue；fast heartbeat 已能在 cron-safe 預算內完成。
- **execution surfaces 首屏短暫顯示 unavailable / none / unknown**：不是 current issue；本輪已修成 `同步中 / 正在同步 /api/status` loading contract。

---

## Current Priority
1. **維持 breaker-first truth across `/` / `/execution` / `/execution/status` / `/lab` / probe / drilldown / docs**
2. **持續鑽 recent canonical 250-row pathology，而不是 generic 化 blocker**
3. **維持 q35 `1/50 + reference_only_until_exact_support_ready` 的 patch visibility，不可誤升級成 deployable truth**
4. **保留 per-venue blockers 與 CoinGlass auth blocker，可見直到真實 closure**
