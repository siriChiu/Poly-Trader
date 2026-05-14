# ISSUES.md — Current State Only

_最後更新：2026-05-14 22:14:19 CST_

只保留目前有效問題；每輪 heartbeat 必須覆寫 current-state truth，不保留歷史流水帳。

---

## 當前主線事實

- **fast heartbeat #1223 已完成 collect + diagnostics refresh**
  - `Raw=33213 / Features=24400 / Labels=66395`
  - `simulated_pyramid_win=56.79%`
  - 歷史覆蓋：`2y_backfill_ok=True`；`raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`
- **唯一 current-live deployment blocker：exact q15 support 未滿**
  - `deployment_blocker=under_minimum_exact_live_structure_bucket`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q15`
  - `support_route_verdict=exact_bucket_present_but_below_minimum`
  - `support_governance_route=exact_live_bucket_present_but_below_minimum`
  - `support=20/50` / `gap=30` / `allowed_layers=0` / `signal=HOLD`
  - `support_progress.status=semantic_rebaseline_under_minimum`；`stagnant_run_count=5`；`escalate_to_blocker=True`
  - `legacy_supported_reference=53/50@20260419b` 只能作 reference：semantic identity 不吻合 current support identity（`calibration_window / entry_quality_label / regime_label` mismatch），不得宣稱 same-identity regression 或 deployable closure。
- **high-conviction Top-K OOS gate 已有離線候選，但 runtime support 擋住部署**
  - `high_conviction_topk.generated_at=2026-05-14T13:24:12.792185+00:00` / `freshness=fresh` / `age_min≈46.9` / `stale_after_min=60`
  - `deployable_count=0` / `risk_qualified_count=6` / `runtime_blocked_candidate_count=6`
  - nearest candidate：`logistic_regression / current_full / all / top_2pct`，`oos_roi=0.9324` / `win_rate=0.8621` / `profit_factor=19.8864` / `max_drawdown=0.022` / `worst_fold=0.2068` / `trades=58`
  - candidate tier：`runtime_blocked_oos_pass`；`oos_gate_passed=True` / `blocked_only_by_live_guardrails=True`；不得部署直到 exact current bucket support ≥ 50 且 live guardrails clear。
- **本輪產品化 patch：leaderboard probe 已升級為 operator-ready runtime-blocked evidence**
  - `scripts/hb_model_leaderboard_api_probe.py` 現在輸出 compact `high_conviction_topk` 摘要、`nearest_deployable_candidate`、current support context、support progress 與 legacy semantic evidence。
  - Probe 會移除龐大的 same-identity history，並在未等待 refresh 時把 `initial_state=None`，避免 cron/operator report 被重複 payload 淹沒。
  - 新 regression test：`tests/test_hb_model_leaderboard_api_probe.py::test_run_probe_compacts_support_history_and_high_conviction_topk`。
- **recent canonical diagnostics 仍需監控**
  - `latest_window=100` / `win_rate=45.0%` / `dominant_regime=chop(100.0%)` / `avg_quality=+0.0873` / `avg_pnl=-0.0017` / `alerts=regime_concentration,regime_shift`
- **source / venue blockers 仍開啟**
  - `fin_netflow=source_auth_blocked/auth_missing`；`nest_pred=source_tls_verify_failed/tls_verify_required_no_insecure_fallback`。
  - Venue runtime proof 仍缺：live exchange credential、order ack lifecycle、fill lifecycle。不得把 metadata OK 當成 venue-ready。

---

## Open Issues

### P0 — current live bucket q15 exact support under minimum blocks deployment
- 目前真相：`CAUTION|structure_quality_caution|q15` exact support `20/50`，gap `30`。
- 產品要求：Dashboard / Strategy Lab / Execution / `/api/models/leaderboard` / probes / docs 都必須把這個 blocker 放在第一層；proxy rows、neighbor rows、legacy 53/50 reference 都不得取代 current exact support。
- 下一步：累積或回填同一 `support_identity` 的 exact bucket rows；若 semantic identity 不吻合，只能標 reference-only。

### P0 — high-conviction Top-K 候選只能 shadow / paper，不可 live deploy
- 目前真相：6 個 OOS/risk-qualified candidates 全部 `runtime_blocked_oos_pass`，部署列為 0。
- 產品要求：Top-K UI/API 排序可顯示 nearest candidate，但必須同時顯示 `model_gate_failures=[]` 與 `live_gate_failures=[support_route_not_deployable, deployment_blocker_active]`，避免把高 ROI 誤讀成可交易。
- 下一步：維持 matrix freshness < 60min；exact support ≥ 50 且 live guardrails clear 後才允許升級部署候選。

### P0 — TW-IC 低於門檻，需繼續當 drift blocker 監控
- 目前真相：`#1223=13/30 -> #1222=13/30 -> #1221=12/30`，低於 `<14/30` threshold。
- 下一步：持續跑 recent drift report；優先檢查 recent label balance、regime concentration、constant-target guardrails，不把 drift 診斷泛化成模型調參。

### P1 — source auth / TLS blockers
- `fin_netflow`：缺 `COINGLASS_API_KEY`，coverage 仍為 0%。
- `nest_pred`：Polymarket Gamma TLS chain 失敗，政策是 `tls_verify_required_no_insecure_fallback`；不得 disable TLS verification。
- 下一步：修 trusted CA / proxy root 或走 verified network path；配置 API key 後用 forward archive 補足 snapshot。

### P1 — venue readiness proof 未閉環
- 目前真相：OKX/Binance runtime proof 不足；credential、order ack、fill lifecycle 尚無 production-grade 證據。
- 下一步：維持 fail-closed；Dashboard / Execution / Lab 必須顯示 per-venue proof_state、blockers、operator_next_action、verify_next。

---

## Current Priority

1. **守住 q15 exact current-live support blocker：20/50 gap=30。**
2. **讓 high-conviction Top-K 成為可拒單部署治理，不是 ROI-only 交易訊號。**
3. **保持 probe/API/UI/docs 對 runtime-blocked OOS pass candidate 的共同語言：離線過、runtime 未過。**
4. **持續監控 TW-IC/recent drift/source/venue blockers，不降低安全閘門。**

---

## 本輪驗證證據

- `PYTHONPATH=. python /tmp/hb_probe_check.py`：probe compact output 344 lines；`deployable_count=0` / `risk_qualified_count=6` / `runtime_blocked_candidate_count=6`；support `20/50 gap=30`；`history_in_progress=False`。
- `PYTHONPATH=. python -m pytest tests/test_hb_model_leaderboard_api_probe.py -q`：`6 passed`。
- `PYTHONPATH=. python -m pytest tests/test_model_leaderboard.py -k high_conviction_topk -q`：`6 passed, 41 deselected`。
- `PYTHONPATH=. python -m pytest tests/test_frontend_decision_contract.py -k high_conviction_topk_gate_contract -q`：`1 passed, 75 deselected`。
