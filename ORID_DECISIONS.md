# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-05-14 22:14:19 CST_

---

## 心跳 #1223 產品化 ORID

### O｜客觀事實
- fast heartbeat #1223 已刷新：`Raw=33213 / Features=24400 / Labels=66395`；`simulated_pyramid_win=56.79%`；2y coverage OK。
- Current-live blocker 是 `under_minimum_exact_live_structure_bucket`：`CAUTION|structure_quality_caution|q15` exact support `20/50`，gap `30`，`allowed_layers=0`，`signal=HOLD`。
- `support_progress.status=semantic_rebaseline_under_minimum`；legacy `53/50@20260419b` 因 `calibration_window / entry_quality_label / regime_label` mismatch 只能 reference-only。
- High-conviction Top-K matrix fresh；`deployable_count=0`、`risk_qualified_count=6`、`runtime_blocked_candidate_count=6`。
- Nearest candidate：`logistic_regression/current_full/all/top_2pct`，`oos_roi=0.9324`、`win_rate=0.8621`、`profit_factor=19.8864`、`max_drawdown=0.022`、`worst_fold=0.2068`、`trades=58`；OOS/model gate 過，但 blocked only by live guardrails。
- 本輪 patch：`scripts/hb_model_leaderboard_api_probe.py` 產品化 compact runtime-blocked Top-K summary，加入 `high_conviction_topk`、`nearest_deployable_candidate`、support progress、legacy semantic evidence；移除巨量 history 與非必要 duplicate `initial_state`。
- 驗證：probe compact facts 344 lines；`tests/test_hb_model_leaderboard_api_probe.py` 6 passed；`tests/test_model_leaderboard.py -k high_conviction_topk` 6 passed；`tests/test_frontend_decision_contract.py -k high_conviction_topk_gate_contract` 1 passed。

### R｜感受直覺
- 目前最大產品風險不是沒有候選，而是 operator 把高 ROI / 高 win-rate OOS row 誤讀成可 live trade。
- Probe/cron 摘要若充滿重複 payload 與長 history，會掩蓋真正的 `20/50 gap=30` blocker；這會讓產品治理失焦。

### I｜意義洞察
1. **OOS pass 不等於可部署**：Top-K candidate 已有研究價值，但 current exact support 未滿時只能 shadow/paper。
2. **Legacy support 需要 semantic identity 才能關 blocker**：不同 `calibration_window / entry_quality_label / regime_label` 的 53/50 不可替代 current `20/50`。
3. **產品化 evidence 必須可讀且可 machine-read**：compact probe 讓 cron report 同時保留數字、路由、候選、blocker，不再把關鍵 truth 埋在 artifact 深層。

### D｜決策行動
- **決策**：維持 live deployment fail-closed；把 high-conviction Top-K 當作「研究→影子驗證」gate，而不是交易許可。
- **Patch**：提交 probe compact runtime-blocked Top-K contract + regression test。
- **下一輪 gate**：補同一 support identity 的 exact q15 rows 到 ≥50，或保持 blocker；持續確認 `/api/models/leaderboard`、Strategy Lab、probe、docs 都把 OOS/model pass 與 live/runtime block 分開呈現。
- **如果失敗**：若 `deployable_count>0` 但 exact support 仍 <50，或 UI/API 未顯示 live gate failures，立即升級為 P0 deployment governance regression。
