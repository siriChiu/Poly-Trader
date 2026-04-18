# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 06:49 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat + collect 本輪成功推進資料面**：DB 更新到 `Raw=31067 / Features=22485 / Labels=62564`；`240m / 1440m` freshness 仍屬 expected horizon lag，不是管線停滯。
- **exact-vs-spillover 對照已產品化補強**：`model/predictor.py` 在 exact live lane `0 rows` 時，會以 `current_live_row_gate_inputs` 當 reference 產生 spillover 4H feature contrast；`/lab` 與 `/execution/status` browser verify 已看到 top 4H shifts，不再只有空白 exact-lane 對照。
- **本輪驗證完成**：`PYTHONPATH=. pytest tests/test_api_feature_history_and_predictor.py -q` `59 passed`、`PYTHONPATH=. pytest tests/test_frontend_decision_contract.py -q` `12 passed`、`cd web && npm run build` 成功、browser `/lab` / `/execution/status` 無 JS exception。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker，且在 operator surface 清楚可見
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=237`
- `allowed_layers=0`

**成功標準**
- `/lab`、`/execution/status`、`hb_predict_probe.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：把 q15 `0/50` exact support shortage 持續維持為可 machine-read 的 support-aware governance
**目前真相**
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `support_progress.status=no_recent_comparable_history`
- `leaderboard_selected_profile=core_only`
- `train_selected_profile=core_plus_macro`
- `governance_contract=dual_role_governance_active`

**成功標準**
- probe / API / Strategy Lab / docs 都一致承認 `0/50 + exact_bucket_missing_exact_lane_proxy_only + gap_to_minimum=50`；
- breaker path 下也不再把 support metadata 遮蔽成空值或 stale 舊數字。

### 目標 C：把 broader `bull|CAUTION` toxic pocket 轉成正式 patch
**目前真相**
- exact live lane：`0 rows`
- broader spillover：`bull|CAUTION 200 rows / WR=0.0% / quality=-0.2947 / pnl=-1.09%`
- `feature_shift_reference=current_live_row_gate_inputs` 已就位，operator 現在看得到 spillover 與 current live row 的 4H shift 差異

**成功標準**
- 有一個可重跑的 gate / calibration / training patch，直接對應 `bull|CAUTION` toxic pocket；
- 對應 patch 能用 probe、drilldown、pytest、browser surface 重跑驗證，而不是只停在對照卡與報告。

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
- `q15 support 0/50 + gap_to_minimum=50` 在 breaker path 下仍完整暴露於 probe / API / UI / docs
- `bull|CAUTION` spillover pathology 有可重跑、可驗證的 patch，而不只是 diagnostics 對照
- Strategy Lab / Execution Status 保持：**blocker truth 清楚、venue blockers 保留、runtime console 無 JS exception**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
