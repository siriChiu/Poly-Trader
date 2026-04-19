# ISSUES.md — Current State Only

_最後更新：2026-04-19 16:24 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast collect + direct probe refresh 成功**：`Raw=31111 (+2) / Features=22529 (+2) / Labels=62632 (+8)`；`240m / 1440m` freshness 仍屬 lookahead 的 expected lag，資料管線不是 frozen。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=264`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 維持 `CAUTION|base_caution_regime_or_bias|q15`**：`regime=chop`、`gate=CAUTION`、`entry_quality=0.4124 (D)`；exact support 仍是 **0/50**，`support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`、`support_progress.status=stalled_under_minimum`、`gap_to_minimum=50`、`remaining_gap_to_floor=0.1376`、`best_single_component=feat_4h_bias50`。
- **recent canonical 250 rows 仍是 distribution pathology**：`win_rate=0.0000`、`dominant_regime=bull(100%)`、`avg_pnl=-0.0103`、`avg_quality=-0.2862`、`tail_streak=250x0`；主 shifts 為 `feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`。
- **support-aware patch 仍是 reference-only**：`recommended_patch=core_plus_macro`、`recommended_patch_status=reference_only_until_exact_support_ready`、`spillover_regime_gate=bull|CAUTION`、`spillover_rows=199`、`support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`、`gap_to_minimum=50`。
- **canonical model leaderboard 已從 placeholder-only 轉成可比較 rows**：`/api/models/leaderboard` 現為 `count=6 / comparable_count=6 / placeholder_count=0`，`evaluation_fold_window=latest_bounded_walk_forward`、`evaluation_max_folds=4`；browser `/lab` 已顯示真實模型排行，且 Strategy Lab 明確標示「排行榜回測固定使用最近兩年」。
- **venue readiness 仍只有 public metadata proof**：`binance=config enabled + public-only + metadata OK`、`okx=config disabled + public-only + metadata OK`；`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證。
- **fin_netflow 仍是 source_auth_blocked**：`COINGLASS_API_KEY` 缺失；forward archive 已累積 `2582` snapshots，但 `archive_window_coverage_pct=0.0%`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `streak=264`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `allowed_layers=0`
- `runtime_closure_state=circuit_breaker_active`

**風險**
- 若任何 surface 再把 q15 support、venue blockers 或 spillover artifact 排到 breaker 前面，operator 會失去唯一 current-live blocker 真相。

**下一步**
- 維持 breaker-first truth 在 `/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`。

### P0. recent canonical 250 rows remains a distribution pathology
**現況**
- `recent_window=250`
- `win_rate=0.0000`
- `dominant_regime=bull`
- `dominant_regime_share=1.0000`
- `avg_pnl=-0.0103`
- `avg_quality=-0.2862`
- `alerts=['constant_target','regime_concentration','regime_shift']`
- `tail_streak=250x0`
- top feature shifts：`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`

**風險**
- 這個 recent canonical tail 仍是 breaker 的根因；若只看 broader history、model ranking 或 venue blockers，會掩蓋 current pathological slice。

**下一步**
- 以 recent canonical rows 為主做 feature variance / distinct-count / target-path drilldown，避免把 blocker 誤寫成 generic leaderboard 或 venue 議題。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. q15 exact support is still stalled under breaker (0/50)
**現況**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_governance_route=exact_live_lane_proxy_available`
- `support_progress.status=stalled_under_minimum`
- `remaining_gap_to_floor=0.1376`
- `best_single_component=feat_4h_bias50`

**風險**
- 如果 probe / docs / UI 把 `0/50 + missing exact lane + stalled_under_minimum` 藏掉，operator 會誤判 q15 support 已接近 closure。

**下一步**
- 維持 `0/50 + exact_bucket_missing_exact_lane_proxy_only + stalled_under_minimum + gap_to_minimum=50` 在 probe / API / UI / docs / `issues.json` 一致 machine-read。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P1. support-aware `core_plus_macro` patch must stay visible but reference-only
**現況**
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`
- `spillover_regime_gate=bull|CAUTION`
- `spillover_rows=199`
- `reference_source=live_scope_spillover`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `gap_to_minimum=50`

**風險**
- 若 `recommended_patch` 消失或被升級成 deployable，operator 會失去唯一 support-aware 治理方向，或被誤導成 runtime 已可放行。

**下一步**
- 維持 `recommended_patch` 在 `/api/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致；只允許 `reference-only`，直到 exact support 達標。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`。

### P1. leaderboard recent-window contract is delivered; keep it stable and cron-safe
**現況**
- `/api/models/leaderboard`: `count=6`、`comparable_count=6`、`placeholder_count=0`
- `evaluation_fold_window=latest_bounded_walk_forward`
- `evaluation_max_folds=4`
- top model（目前 API）=`random_forest / core_only`
- browser `/lab` 已顯示真實模型排行，且明示「排行榜回測固定使用最近兩年」

**風險**
- 若 payload 回退到 full-history placeholder 或重算超出 cron 預算，canonical model surface 會再次退回不可比較狀態。

**下一步**
- 維持 `/api/models/leaderboard`、Strategy Lab 工作區與模型排行都使用 latest bounded walk-forward + 兩年預設區間，不可回退成 placeholder-only 或短窗過擬合。
- 驗證：browser `/lab`、browser `fetch('/api/models/leaderboard')`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`。

### P1. venue readiness is still unverified
**現況**
- `binance`: `config enabled + public-only + metadata OK`
- `okx`: `config disabled + public-only + metadata OK`
- 缺的 runtime proof：`live exchange credential`、`order ack lifecycle`、`fill lifecycle`

**風險**
- breaker 未來解除後，若 venue blockers 被弱化成摘要字串或完全消失，使用者會被誤導成已可實盤。

**下一步**
- 持續保留 per-venue blockers，但它們必須永遠位於 breaker-first current blocker 之後。
- 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`data/execution_metadata_smoke.json`。

### P1. fin_netflow source_auth_blocked remains open
**現況**
- `fin_netflow=source_auth_blocked`
- `latest_status=auth_missing`
- blocker 根因：`COINGLASS_API_KEY is missing`
- `forward_archive_rows=2582`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`、下輪 heartbeat source blockers。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+2 raw / +2 features / +8 labels`。
- **240m / 1440m freshness lag**：不是 blocker；目前仍屬 lookahead horizon 的 expected lag。
- **canonical model leaderboard placeholder-only**：不是 current issue；`/api/models/leaderboard` 已恢復 `6` 筆 comparable rows，browser `/lab` 可見真實模型排行。
- **Strategy Lab 排行榜回測區間語義不明**：不是 current regression；UI 已明示「排行榜回測固定使用最近兩年」，且預設區間會落在最近 730 天。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 q15 / venue / spillover 雜訊**
2. **把 recent canonical 250 rows pathology 當成 breaker 根因持續鑽深，不被 broader history 或 leaderboard 勝負稀釋**
3. **把 q15 `0/50` 與 reference-only `core_plus_macro` patch 一起維持 machine-read，可見且不可被升級成 deployable**
4. **守住已恢復的 canonical leaderboard comparable rows 與 Strategy Lab 兩年回測 contract，不讓它回退成 placeholder-only 或短窗假樂觀**
5. **持續保留 per-venue blockers 與 source auth blockers，可見直到 credentials / ack / fill / CoinGlass auth 真正 closure**
