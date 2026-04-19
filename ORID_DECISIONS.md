# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-20 03:39:09 CST_

---

## 心跳 #20260420-docsync ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=31170 / Features=22587 / Labels=62865`；`simulated_pyramid_win=57.23%`。
- current-live blocker：`deployment_blocker=circuit_breaker_active` / `streak=171` / `recent_window_wins=0/50` / `additional_recent_window_wins_needed=15`。
- q15 same-bucket truth：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15` / `support=0/50` / `gap=50` / `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`。
- recent pathological slice：`window=100` / `win_rate=0.0%` / `dominant_regime=bull(100.0%)` / `avg_quality=-0.2202` / `avg_pnl=-0.0083` / `alerts=constant_target,regime_concentration,regime_shift`。
- leaderboard / governance：`leaderboard_count=6` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro` / `governance_contract=dual_role_governance_active` / `current_closure=global_ranking_vs_support_aware_production_split`。
- source / venue blockers：`blocked_sparse_features=8`；fin_netflow=`quality_flag=source_auth_blocked` / `latest_status=auth_missing` / `forward_archive_rows=2641` / `archive_window_coverage_pct=0.0`；venue proof 仍缺 credential / order ack / fill lifecycle。
- 本輪產品化 patch：heartbeat runner 現在會在 `auto_propose_fixes.py` 後自動 overwrite sync `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`，避免 markdown docs 落後最新 machine-readable artifacts。

### R｜感受直覺
- 這輪最危險的產品問題不是數字不夠，而是 heartbeat 原本只會提醒 docs stale，卻不會自己完成 docs overwrite；這會讓 repo current-state 與 live artifacts 再次 split-brain。
- breaker-first truth 沒變，但如果 markdown docs 還停在舊的 streak / 舊的 q15 rows，operator 看到的仍然是假 current state。

### I｜意義洞察
1. **closed-loop heartbeat 不能只更新 issues.json**：current-state markdown docs 也必須自動跟上，否則心跳在治理層仍然是不完整的。
2. **真正主 blocker 仍是 breaker + pathological slice**：docs automation 只是把 current truth 對齊，不是把 venue / q15 patch 提前升級成主敘事。
3. **把 docs overwrite 內建進 runner 才符合 productization**：這能把 current-state 治理從人工補寫，升級成 cron-safe contract。

### D｜決策行動
- **Owner**：heartbeat runner / current-state governance lane
- **Action**：在 `auto_propose_fixes.py` 之後直接 overwrite sync `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`，讓 docs 跟 `issues.json / live artifacts` 同輪收斂。
- **Artifacts**：`scripts/hb_parallel_runner.py`、`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`。
- **Verify**：`pytest tests/test_hb_parallel_runner.py -q`（或 targeted docs-sync tests）、`python scripts/hb_parallel_runner.py --fast --hb <run>`、確認不再出現 docs stale warning。
- **If fail**：只要 docs 再次落後 `issues.json / live probe / drilldown`，就把 heartbeat 升級回 current-state governance blocker，因為這代表 cron 還沒有真正完成 docs overwrite 閉環。
