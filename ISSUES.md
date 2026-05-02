# ISSUES.md — Current State Only

_最後更新：2026-05-02 09:14:43 CST_

只保留目前有效問題；本檔是 heartbeat current-state overwrite，不保留歷史流水帳。

---

## 當前產品事實（Heartbeat #1166）

- **fast heartbeat #1166 已完成 collect + diagnostics refresh**：`Raw=32559 / Features=23977 / Labels=65737`，`simulated_pyramid_win=56.77%`，兩年歷史覆蓋 `ok=True`（raw 起點 `2024-04-13T22:00:00+00:00`）。
- **current-live deployment 仍 fail-closed**：`signal=ABSTAIN` / `allowed_layers=0` / `deployment_blocker=under_minimum_exact_live_structure_bucket` / `execution_guardrail_reason=under_minimum_exact_live_structure_bucket`。
- **current-live q35 bucket support 未達部署門檻**：`current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35`，exact rows `20/50`，gap `30`，`support_route_verdict=exact_bucket_present_but_below_minimum`，`support_governance_route=exact_live_bucket_present_but_below_minimum`。
- **recent canonical diagnostics**：`window=1000` / `win_rate=44.9%` / `dominant_regime=bull(69.3%)` / `alerts=regime_shift`；這是監控與根因線索，不得覆蓋 current-live exact-support blocker。
- **high-conviction Top-K OOS gate 已有 runtime-blocked winner，但沒有 deployable row**：`rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidate_rows=6`；nearest candidate=`logistic_regression top_2pct`，`oos_roi=0.9324`、`win_rate=86.21%`、`profit_factor=19.8864`、`max_drawdown=0.022`、`worst_fold=0.2068`、`trades=58`，但 live support 只有 `20/50`，所以仍 `not_deployable`。
- **本輪產品化 patch**：`/api/models/leaderboard.high_conviction_topk` 的 compact rows 現在保留 row-level `signal / allowed_layers / execution_guardrail_reason / source_live_probe_generated_at / live_truth_source_artifact`；Strategy Lab 高信心 Top-K 列表直接顯示即時訊號、可用層與阻塞原因，避免 operator 只看到 ROI/win-rate 而誤判可部署。

---

## Open Issues

### P0 — q35 current-live exact support 仍不足，部署必須 fail-closed
- 現況：`CAUTION|base_caution_regime_or_bias|q35` exact support `20/50`，gap `30`。
- Runtime truth：`ABSTAIN`、`allowed_layers=0`、`deployment_blocker=under_minimum_exact_live_structure_bucket`。
- 成功條件：同分桶 support 達最低樣本門檻前，Dashboard / Strategy Lab / Execution Console / `/api/trade` 都不得顯示或執行 buy/add exposure。
- 下一步：持續累積 exact bucket rows；若 rows 沒成長，檢查 label horizon、feature pipeline 與 current bucket coverage。

### P0 — high-conviction Top-K 只能作影子驗證，不能升級 deployable
- 現況：OOS/風控已有 6 個 runtime-blocked candidate，但 `deployable_rows=0`。
- Nearest candidate：`logistic_regression top_2pct` 已通過 OOS/風控門檻，仍因 live support `20/50` + blocker active 而 `runtime_blocked_oos_pass`。
- 本輪閉環：API compact row 與 Strategy Lab UI 已補 row-level `signal=ABSTAIN`、`allowed_layers=0`、`execution_guardrail_reason=under_minimum_exact_live_structure_bucket`。
- 下一步：保持 matrix freshness + live support overlay；任何 high ROI winner 只有在 OOS、drawdown、worst-fold、live support、venue readiness 全通過時才能標 deployable。

### P1 — q35 scoring redesign 只能是 score-only 線索，不能當 deployment closure
- 現況：q35 scaling audit 指出 `bias50_formula_may_be_too_harsh`；base-stack redesign 可把 score 跨 floor，但 runtime 仍 `allowed_layers=0`。
- 下一步：若要調整 q35 formula，必須同時保留 exact-support gate 與 execution guardrail，不可把 `entry_quality` 改善誤當 live-ready。

### P1 — sparse-source / venue readiness 仍未達 production proof
- Sparse source：`blocked_sparse_features=8`；`fin_netflow` 仍 `source_auth_blocked`，`COINGLASS_API_KEY` 缺失，archive window coverage `0.0%`。
- Venue：Binance/OKX 仍缺 `live exchange credential / order ack lifecycle / fill lifecycle` runtime-backed proof。
- 下一步：補 CoinGlass auth；為 Binance/OKX 建立最小 runtime proof（credential check、order ack dry-run/沙盒、fill lifecycle/reconciliation artifact）。

### P1 — leaderboard / docs governance 必須保持 current-state overwrite
- 現況：leaderboard dual-role governance active；current-state markdown 已同步到 HB #1166 truth。
- 下一步：下輪 heartbeat 若 `high_conviction_topk_oos_matrix.json` stale 或 markdown 與 live artifacts 不一致，直接視為 governance blocker。

---

## 驗證證據（本輪已跑）

- `source venv/bin/activate && PYTHONPATH=. python scripts/hb_parallel_runner.py --fast --fast-refresh-candidates --hb 1166`
- `source venv/bin/activate && PYTHONPATH=. python -m pytest tests/test_model_leaderboard.py -k high_conviction_topk -q` → `3 passed, 41 deselected`
- `source venv/bin/activate && PYTHONPATH=. python -m pytest tests/test_frontend_decision_contract.py -k high_conviction_topk_gate_contract -q` → `1 passed, 75 deselected`
- Runtime probe（API loader）→ `deployable_count=0`、`runtime_blocked_candidate_count=6`、nearest row=`ABSTAIN / allowed_layers=0 / under_minimum_exact_live_structure_bucket / 20/50 / gap=30`
- `cd web && npm run build` → TypeScript + Vite build 成功

---

## 下一輪 Gate

1. **Exact-support gate**：q35 current-live bucket rows 必須從 `20/50` 往上累積；未達前 buy/add exposure 繼續 fail-closed。
2. **Top-K gate**：保持 `/api/models/leaderboard.high_conviction_topk` 與 Strategy Lab 顯示 row-level runtime truth；不得把 `runtime_blocked_oos_pass` 誤標 deployable。
3. **Venue gate**：補 Binance/OKX runtime proof，否則仍不可 production trade。
4. **Source gate**：補 CoinGlass auth，否則 ETF flow / liquidation sparse source 覆蓋仍是 product blocker。
