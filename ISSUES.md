# ISSUES.md — Current State Only

_最後更新：2026-04-19 14:52 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **fast heartbeat + collect 成功**：`Raw=31104 (+1) / Features=22522 (+1) / Labels=62619 (+2)`；`240m / 1440m` freshness 仍屬 lookahead 的 expected lag，資料管線不是 frozen。
- **canonical current-live 唯一 deployment blocker 仍是 circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=261`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`allowed_layers=0`、`runtime_closure_state=circuit_breaker_active`。
- **current live bucket 維持 `CAUTION|base_caution_regime_or_bias|q15`**：`regime=chop`、`gate=CAUTION`、`entry_quality=0.4388 (D)`；exact support 仍是 **0/50**，`support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`、`gap_to_minimum=50`、`support_progress.status=stalled_under_minimum`、`escalate_to_blocker=true`。
- **recent canonical 250 rows 仍是 distribution pathology**：`win_rate=0.0000`、`dominant_regime=bull(100%)`、`avg_pnl=-0.0103`、`avg_quality=-0.2854`、`tail_streak=250x0`；主 shifts 為 `feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`。
- **本輪產品化 patch 已鎖住 Strategy Lab Gate 摘要 contract**：`server/routes/api.py` 現在固定輸出 `regime_gate_summary`，且 `_decorate_strategy_entry()` 會在 legacy strategy results 已有完整 trade log 時自動回填 gate 摘要；browser `/lab` 已重新顯示 auto strategy 的非零 Gate 摘要（`catboost`: `ALLOW 0 / CAUTION 39 / BLOCK 0`），不再回退成 `0/0/0` 假空白。
- **auto strategy leaderboard 已重掃並維持 6 筆真實候選可載入**：`rule_baseline / logistic_regression / xgboost / lightgbm / catboost / random_forest` 各 1 筆最新 auto candidate 可在 Strategy Lab workspace 載入；目前修好的問題是 workspace UX，不是 canonical model leaderboard 已 closure。
- **canonical model leaderboard 仍是 placeholder-only**：`leaderboard_count=0`、`comparable_count=0`、`placeholder_count=4`；治理 split 仍是 `global_profile=core_only` vs `train_selected_profile=core_plus_macro`，這是治理分工，不是 stale parity drift。
- **venue readiness 仍只有 public metadata proof**：`binance=config enabled + public-only`、`okx=config disabled + public-only`；`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證。
- **fin_netflow 仍是 source_auth_blocked**：`COINGLASS_API_KEY` 缺失；forward archive 持續前進，但 `archive_window_coverage_pct=0.0%`。

---

## Open Issues

### P0. canonical circuit breaker remains the only current-live deployment blocker
**現況**
- `deployment_blocker=circuit_breaker_active`
- `recent_window=50`
- `current_recent_window_wins=0`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=15`
- `streak=261`
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
- `avg_quality=-0.2854`
- `alerts=['constant_target','regime_concentration','regime_shift']`
- `tail_streak=250x0`
- top feature shifts：`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`

**風險**
- 這個 recent canonical tail 仍是 breaker 的根因；若只看 broader history、profile split 或 venue blockers，會掩蓋 current pathological slice。

**下一步**
- 以 recent canonical rows 為主做 feature variance / distinct-count / target-path drilldown，避免把 blocker 誤寫成 generic profile parity。
- 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`。

### P1. q15 exact support is still missing under breaker (0/50)
**現況**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_governance_route=exact_live_lane_proxy_available`
- `support_progress.status=stalled_under_minimum`

**風險**
- 如果 probe / docs / UI 把 `0/50 + missing_exact_lane_proxy_only + stalled_under_minimum` 藏掉，operator 會誤判 q15 support 已接近 closure。

**下一步**
- 維持 `0/50 + exact_bucket_missing_exact_lane_proxy_only + stalled_under_minimum + escalate_to_blocker=true` 在 probe / API / UI / docs / `issues.json` 一致 machine-read。
- 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`。

### P1. support-aware `core_plus_macro` patch must stay visible but reference-only
**現況**
- `actual_live_spillover_scope=bull|BLOCK`
- `reference_patch_scope=bull|CAUTION`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`
- `reference_source=bull_4h_pocket_ablation.bull_collapse_q35`
- `current_live_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `gap_to_minimum=50`

**風險**
- 若 `recommended_patch` 消失或被升級成 deployable，operator 會失去唯一 support-aware 治理方向，或被誤導成 runtime 已可放行。

**下一步**
- 維持 `recommended_patch` 在 `/api/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 一致；只允許 `reference-only`，直到 exact support 達標。
- 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、`pytest tests/test_frontend_decision_contract.py -q`。

### P1. canonical model leaderboard is still placeholder-only
**現況**
- `leaderboard_count=0`
- `comparable_count=0`
- `placeholder_count=4`
- `leaderboard_warning=目前 4 個模型都沒有產生任何交易`
- `global_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`
- **本輪已完成的 prerequisite 修復**：Strategy Lab workspace Gate 摘要已恢復非零，auto candidate 可正常載入；剩餘問題只在 canonical model leaderboard。

**風險**
- 即使 Strategy Lab workspace 已可載入真實 auto candidates，若 canonical model leaderboard 仍沒有 comparable rows，使用者仍可能把 placeholder #1 誤讀成 deployment ranking。

**下一步**
- 保留 placeholder-only warning，同時持續把 current live governance / support blocker 與 model ranking 分離；下一輪要推進 canonical comparable rows，而不是讓 workspace 再回退成 Gate 摘要全零。
- 驗證：`python scripts/hb_leaderboard_candidate_probe.py`、browser `/lab`。

### P1. venue readiness is still unverified
**現況**
- `binance`: `config enabled + public-only`
- `okx`: `config disabled + public-only`
- metadata smoke：`fresh / healthy`
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
- `forward_archive_rows=2575`
- `archive_window_coverage_pct=0.0%`

**風險**
- Feature coverage 會持續呈現假前進：archive 在長，但 live fetch 仍失敗，資料實際不可用。

**下一步**
- 配置 `COINGLASS_API_KEY`，先讓 ETF flow source 從 `auth_missing` 轉成成功 snapshot，再評估是否需要歷史 backfill。
- 驗證：`data/heartbeat_20260419w_summary.json` source blockers、`/api/features/coverage`。

---

## Not Issues
- **data pipeline frozen**：不是；本輪 collect 實際新增 `+1 raw / +1 features / +2 labels`。
- **240m / 1440m freshness lag**：不是 blocker；目前仍屬 lookahead horizon 的 expected lag。
- **Strategy Lab Gate 摘要全零**：不是 current regression；本輪已以 `regime_gate_summary` + legacy backfill contract 修復，browser `/lab` 已看到 `ALLOW 0 / CAUTION 39 / BLOCK 0`。
- **profile split (`core_only` vs `core_plus_macro`)**：不是 current parity drift；目前仍屬 `dual_role_governance_active` 的健康治理分工。

---

## Current Priority
1. **維持 breaker-first truth，讓 current-live blocker 始終是 release math，而不是 q15 / venue / spillover 雜訊**
2. **把 recent canonical 250 rows pathology 當成 breaker 根因持續鑽深，不被 broader history 稀釋**
3. **把 q15 `0/50` 與 reference-only `core_plus_macro` patch 一起維持 machine-read，可見且不可被升級成 deployable**
4. **把 canonical model leaderboard 從 placeholder-only 推向 comparable rows，同時守住本輪已修好的 Strategy Lab Gate 摘要與 auto candidate 載入 UX**
5. **持續保留 per-venue blockers 與 source auth blockers，可見直到 credentials / ack / fill / CoinGlass auth 真正 closure**
