# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-30 09:20:10 CST_

---

## 心跳 #1144 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=32497 / Features=23915 / Labels=65599`；歷史覆蓋確認：`2y_backfill_ok=True` / `raw_start=2024-04-13T22:00:00+00:00` / `features_start=2024-04-14T07:00:00+00:00` / `labels_start=2024-04-14T07:00:00+00:00`；`simulated_pyramid_win=56.73%`。
- 即時部署阻塞點：`deployment_blocker=under_minimum_exact_live_structure_bucket`。
- q15 current-live bucket truth：`current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=9/50` / `gap=41` / `support_route_verdict=exact_bucket_present_but_below_minimum` / `support_governance_route=exact_live_bucket_present_but_below_minimum` / `support_route_deployable=false`。
- support progress：`status=semantic_rebaseline_under_minimum` / `regression_basis=legacy_or_different_semantic_signature` / `legacy_supported_reference=53/50@20260419b`。
- latest recent-window diagnostics：`latest_window=100` / `win_rate=24.0%` / `dominant_regime=chop(87.0%)` / `avg_quality=-0.0602` / `avg_pnl=-0.0043` / `alerts=regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=current_full_no_bull_collapse_4h` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split` / `payload_source=latest_persisted_snapshot`。
- high-conviction OOS Top-K：`rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidates=6`；最接近部署候選 `logistic_regression top_2pct` OOS 過關但因 live support blocker 仍 `not_deployable`。
- 本輪產品化修補：`/api/models/leaderboard` 在 cached payload path 也會重新載入 high-conviction Top-K summary 並套用 fresh `live_predict_probe.json` overlay；runtime 驗證已從 stale `exact_live_lane_proxy_available` 收斂為 fresh `exact_live_bucket_present_but_below_minimum`，`support=9/50` / `gap=41` / `support_route_deployable=false`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`source_auth_blocked` / `auth_missing`；venue proof 仍缺 credential / order ack / fill lifecycle；metadata smoke venue rows 已帶 proof_state / blockers / operator_next_action / verify_next。

### R｜感受直覺
- 這輪最需要防止的誤讀，是把 OOS 表現最好的 Top-K 候選或 stale proxy governance route 誤讀成已可部署；fresh q15 current-live truth 仍是 `9/50`，不是 deployment closure。
- `Strategy Lab` 是 operator 最容易看到 winner 的地方，所以 cached leaderboard 不能保留舊 live support context；否則「研究 winner」會比「即時阻塞點」更醒目。

### I｜意義洞察
1. **OOS 過關 ≠ current-live deployable**：high-conviction Top-K 可以指出最接近部署候選，但 deployment gate 必須由 fresh live support overlay 決定。
2. **cached payload 也是產品風險面**：即使 leaderboard 用 stale-while-revalidate 提升 UX，也不能讓 cached support_context 覆蓋 live predict probe 的 current blocker truth。
3. **support truth ≠ deployment closure**：`support=9/50` 且 `support_route_verdict=exact_bucket_present_but_below_minimum` 只代表治理前進，還不能把 reference-only patch 升級成 runtime patch。
4. **docs overwrite sync 的角色是護欄**：ISSUES / ROADMAP / ORID 必須跟 runtime API、live probe、drilldown 同輪收斂，避免 operator-facing truth 分裂。

### D｜決策行動
- **Owner**：Strategy Lab / leaderboard runtime governance lane。
- **Action completed this round**：修補 `server/routes/api.py`，讓 `api_model_leaderboard()` 在回 cached payload 前 always refresh `high_conviction_topk` summary；新增 `tests/test_model_leaderboard.py::test_api_model_leaderboard_refreshes_cached_high_conviction_live_support_overlay` 鎖住 stale cache 不可把 support route 誤升級成 deployable/proxy truth。
- **Verify completed this round**：`python -m pytest tests/test_model_leaderboard.py -q` → `43 passed`；runtime helper `/api/models/leaderboard` → `support_governance_route=exact_live_bucket_present_but_below_minimum` / `support_route_deployable=False` / `support=9/50` / `gap=41`；browser `/lab` raw-token probe → probed raw deployment/support tokens not visible.
- **Next gate**：繼續維持 current-live exact-support blocker；若 cached leaderboard、Strategy Lab、或 docs 再把 stale proxy route / reference-only patch / high-conviction winner 顯示成 deployable，就升級為 P0 runtime truth regression。
- **Artifacts**：`server/routes/api.py`、`tests/test_model_leaderboard.py`、`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`data/live_predict_probe.json`、`data/high_conviction_topk_oos_matrix.json`。
