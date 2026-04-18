# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 06:02 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat + collect 本輪成功推進資料面**：DB 更新到 `Raw=31064 / Features=22482 / Labels=62538`；`240m / 1440m` freshness 仍屬於 lookahead 預期，不是管線停滯。
- **operator surfaces 本輪再次驗證有效**：browser `/lab` 與 `/execution/status` 都看到 `circuit_breaker_active`、q15 support `0/50`、venue blockers、`bull|CAUTION` spillover，console `0 errors`。
- **current-state issue governance 已產品化**：`scripts/issues.py` 現在會把 canonical breaker / support issue 與等價 auto issue 去重合併；`issues.json` 回到 current-state-only，不再雙寫同一個 blocker。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker，且在 operator surface 清楚可見
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=236`
- `allowed_layers=0`

**成功標準**
- `/lab`、`/execution/status`、`hb_predict_probe.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：把 q15 `0/50` exact support shortage 持續維持為可 machine-read 的 support-aware governance
**目前真相**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_progress.status=stalled_under_minimum`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**成功標準**
- probe / API / Strategy Lab / docs 都一致承認 `0/50 + stalled_under_minimum + exact_live_lane_proxy_available`；
- breaker path 下也不再把 support metadata 遮蔽成空值或 stale 舊數字。

### 目標 C：把 broader `bull|CAUTION` toxic pocket 轉成正式 patch
**目前真相**
- exact live lane：`0 rows`
- broader spillover：`bull|CAUTION 200 rows / WR=0.0% / quality=-0.295 / pnl=-1.09%`
- recent pathology：`100x0` constant-target bull tail
- 主要 shifts：`feat_4h_dist_bb_lower / feat_4h_bb_pct_b / feat_4h_dist_swing_low`

**成功標準**
- 有一個可重跑的 gate / calibration / training patch，直接對應 `bull|CAUTION` toxic pocket；
- 對應 patch 能用 probe、drilldown、pytest、browser surface 重跑驗證，而不是只停在報告。

### 目標 D：持續保留 venue blockers，直到 runtime artifact 真正 closure
**目前真相**
- `binance=config enabled + public-only`
- `okx=config disabled + public-only`
- `live exchange credential / order ack lifecycle / fill lifecycle` 都尚未驗證

**成功標準**
- 即使 breaker 未來解除，`/lab` 與 `/execution/status` 仍會保留 venue blockers，直到 credentials / ack / fill 各自都有 runtime proof。

---

## 下一步
1. **維持 breaker-first truth 與 blocker split surface**
   - 驗證：`python scripts/hb_predict_probe.py`、browser `/lab`、browser `/execution/status`
2. **維持 q15 support metadata 在 breaker path 下仍然可 machine-read**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、targeted pytest
3. **把 `bull|CAUTION` 200-row toxic pocket 落成 runtime patch**
   - 驗證：`data/live_decision_quality_drilldown.json`、targeted pytest、browser `/lab` 的 `🧬 Live lane / spillover 對照`
4. **持續保留 venue blockers，直到 credentials / ack / fill 有 runtime closure**
   - 驗證：browser `/lab`、browser `/execution/status`、execution artifacts

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + stalled_under_minimum` 在 breaker path 下仍完整暴露於 probe / API / UI / docs
- `bull|CAUTION` spillover pathology 有可重跑、可驗證的 patch，而不只是 drilldown 報告
- Strategy Lab / Execution Status 保持：**blocker truth 清楚、venue blockers 保留、runtime console 無錯誤**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
