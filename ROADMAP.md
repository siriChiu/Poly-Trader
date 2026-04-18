# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 05:16 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat + collect 本輪成功推進資料面**：DB 更新到 `Raw=31062 / Features=22480 / Labels=62495`，`240m / 1440m` freshness 正常，代表 heartbeat 仍具備真實資料閉環能力。
- **Strategy Lab live deployment sync 已完成 blocker split**：`/lab` 現在把 `current live blocker` 與 `venue blockers` 分開顯示；瀏覽器驗證看到 `circuit_breaker_active` 與 venue readiness blockers 並列，沒有被單一文字牆混掉。
- **breaker path 下的 q15 support-aware governance 已同步到 probe / API / UI**：`hb_predict_probe.py`、`/api/status`、`/lab` 現在都保留 `support_route_verdict`、`support_progress`、`minimum_support_rows`、`gap_to_minimum`；targeted pytest、frontend contract tests、browser verify 都已通過。
- **Strategy Lab hover 百分比修正仍維持有效**：本輪瀏覽器再次驗證 `/lab` hover 顯示 `64.3% / 33.9% / 84.5%`，沒有回退到 `6425%` 類型的錯誤百分比。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker，且在 operator surface 清楚可見
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=235`
- `allowed_layers=0`

**成功標準**
- `/lab`、`/execution/status`、`hb_predict_probe.py`、docs 全部一致把 breaker 視為唯一 current-live deployment blocker；
- 未解除前，不再讓 q15 support 或 spillover 蓋過 breaker 主語義。

### 目標 B：把 q15 `0/50` exact support shortage 維持為可 machine-read 的 support-aware governance，而不是被 breaker 蓋掉
**目前真相**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_progress.status=stalled_under_minimum`
- `support_progress.delta_vs_previous=0`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**成功標準**
- probe / API / Strategy Lab / docs 都一致承認 `0/50 + stalled_under_minimum + exact_live_lane_proxy_available`；
- breaker path 下也不再把 support metadata 遮蔽成空值或 stale 舊數字。

### 目標 C：把 broader `bull|CAUTION` toxic pocket 轉成正式 patch
**目前真相**
- exact live lane：`0 rows`
- broader spillover：`bull|CAUTION 200 rows / WR=0.0% / quality=-0.295 / pnl=-1.10%`
- recent pathology：`100x0` constant-target bull tail
- 主要 shifts：`feat_4h_dist_bb_lower / feat_4h_bb_pct_b / feat_4h_dist_swing_low`

**成功標準**
- 有一個可重跑的 gate / calibration / training patch，直接對應 `bull|CAUTION` toxic pocket；
- 對應 patch 能用 probe、drilldown、pytest、browser surface 重跑驗證，而不是只停在報告。

### 目標 D：持續保留 venue blockers，直到 runtime artifact 真正 closure
**目前真相**
- `live exchange credential 尚未驗證`
- `order ack lifecycle 尚未驗證`
- `fill lifecycle 尚未驗證`

**成功標準**
- 即使 breaker 未來解除，`/lab` 與 `/execution/status` 仍會保留 venue blockers，直到 credentials / ack / fill 各自都有 runtime proof。

---

## 下一步
1. **維持 breaker-first truth 與 blocker split surface**
   - 驗證：`venv/bin/python scripts/hb_predict_probe.py`、瀏覽器 `/lab`、瀏覽器 `/execution/status`
2. **維持 q15 support metadata 在 breaker path 下仍然可 machine-read**
   - 驗證：`venv/bin/python scripts/hb_q15_support_audit.py`、`venv/bin/python scripts/hb_predict_probe.py`、targeted pytest
3. **把 `bull|CAUTION` 200-row toxic pocket 落成 runtime patch**
   - 驗證：`data/live_decision_quality_drilldown.json`、targeted pytest、瀏覽器 `/lab` 的 `🧬 Live lane / spillover 對照`
4. **持續保留 venue blockers，直到 credentials / ack / fill 有 runtime closure**
   - 驗證：瀏覽器 `/lab`、瀏覽器 `/execution/status`、execution artifacts

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + stalled_under_minimum` 在 breaker path 下仍完整暴露於 probe / API / UI / docs
- `bull|CAUTION` spillover pathology 有可重跑、可驗證的 patch，而不只是 drilldown 報告
- Strategy Lab 保持：**current live blocker 與 venue blockers 分離、hover 百分比正確、browser runtime 無 console error**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
