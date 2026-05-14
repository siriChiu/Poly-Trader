# ROADMAP.md — Current Plan Only

_最後更新：2026-05-14 22:14:19 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成 / 本輪前進

- **fast heartbeat #1223 diagnostics refresh 完成**：`Raw=33213 / Features=24400 / Labels=66395`；`simulated_pyramid_win=56.79%`；2y coverage OK。
- **current-live blocker 已收斂到 q15 exact support shortage**：`CAUTION|structure_quality_caution|q15` support `20/50`，gap `30`；`deployment_blocker=under_minimum_exact_live_structure_bucket`。
- **本輪 patch：leaderboard heartbeat probe productized**
  - `scripts/hb_model_leaderboard_api_probe.py` 會輸出 compact `high_conviction_topk`、`nearest_deployable_candidate`、current support context、support progress、legacy semantic evidence。
  - Probe 不再在未等待 refresh 時重複巨大 `initial_state`；same-identity history 留在 source artifact，不灌進 operator summary。
  - 新測試鎖住 runtime-blocked Top-K probe contract。
- **high-conviction Top-K gate 已能分離 OOS/model pass 與 live/runtime block**
  - 目前 `deployable_count=0` / `risk_qualified_count=6` / `runtime_blocked_candidate_count=6`。
  - nearest candidate 離線風控達標（LR top_2pct：ROI 0.9324、win rate 0.8621、PF 19.8864、MDD 0.022、trades 58），但 `blocked_only_by_live_guardrails=True`，只能 shadow/paper。

---

## 主目標

### 目標 A：q15 exact current-live support closure
**目前真相**
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q15`
- `support=20/50` / `gap=30`
- `support_route_verdict=exact_bucket_present_but_below_minimum`
- `support_governance_route=exact_live_bucket_present_but_below_minimum`
- `allowed_layers=0` / `signal=HOLD`
- Legacy `53/50@20260419b` 因 semantic identity mismatch 只能 reference-only。

**成功標準**
- Exact current support ≥ 50，且 `support_identity` 完全吻合 current live bucket。
- Probe/API/UI/docs 同步顯示 bucket、rows、minimum、gap、governance route。
- 不用 proxy/neighbor/legacy rows 關閉 blocker。

### 目標 B：High-conviction Top-K 從研究輸出變成可拒單部署 gate
**目前真相**
- Matrix fresh：`generated_at=2026-05-14T13:24:12.792185+00:00`；`stale_after=60m`。
- 0 deployable，6 risk-qualified runtime-blocked candidates。
- nearest candidate：`logistic_regression/current_full/all/top_2pct`，OOS/risk gate 過，但 live support blocker 未過。

**成功標準**
- `/api/models/leaderboard.high_conviction_topk`、Strategy Lab、heartbeat probe 都同時顯示：model gate、live gate、support gap、runtime closure state、nearest candidate。
- 若矩陣過期、exact support 未滿、release guardrail 未 clear、venue proof 未滿，候選維持 `paper_shadow_only` / `not_deployable`。

### 目標 C：Execution / Venue readiness fail-closed
**目前真相**
- `/api/trade` 買入/加倉在 deployment blocker active 時必須 409；減倉/賣出保留風險降低路徑。
- Venue proof 仍缺 credential、order ack lifecycle、fill lifecycle。

**成功標準**
- Dashboard / Execution / Lab 顯示 per-venue proof_state、blockers、operator_next_action、verify_next。
- 不用 metadata OK 替代 runtime-ready proof。

### 目標 D：Source blockers 與 drift 監控
**目前真相**
- TW-IC recent chain 低於門檻：`#1223=13/30 -> #1222=13/30 -> #1221=12/30`。
- `fin_netflow=auth_missing`；`nest_pred=tls_verify_failed` 且 TLS verification 必須維持 required。

**成功標準**
- recent drift report 持續輸出 target-path diagnostics。
- Source auth/TLS blockers 在 API/UI/docs 不消失；不採用 insecure fallback。

---

## 下一輪 gate

1. **Exact-support accumulation gate**
   - 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`data/q15_support_audit.json`。
   - Blocker 升級條件：current bucket rows/gap 從 top-level surfaces 消失，或 legacy/reference rows 被誤宣稱 deployable。

2. **Top-K runtime-blocked UX/API gate**
   - 驗證：`PYTHONPATH=. python scripts/hb_model_leaderboard_api_probe.py`、`python -m pytest tests/test_hb_model_leaderboard_api_probe.py -q`、`python -m pytest tests/test_model_leaderboard.py -k high_conviction_topk -q`、`python -m pytest tests/test_frontend_decision_contract.py -k high_conviction_topk_gate_contract -q`。
   - Blocker 升級條件：OOS/risk pass candidate 未顯示 live gate blocker，或 `deployable_count` 在 exact support 未滿時 > 0。

3. **Venue/source fail-closed gate**
   - 驗證：`data/execution_metadata_smoke.json`、`/execution/status`、`/lab`、source coverage artifacts。
   - Blocker 升級條件：TLS verification 被弱化、auth_missing 被隱藏、venue runtime proof 未滿卻顯示 ready。

---

## 成功標準

- current live q15 truth 維持：**20/50 gap=30**，未滿前 live deployment 必須 fail-closed。
- high-conviction Top-K 能清楚呈現：**OOS/model gate pass，但 runtime support/live guardrails block**。
- Operator summary 精簡、可讀、可 machine-read，不再被巨量 history 或重複 initial payload 淹沒。
- ISSUES / ROADMAP / ORID 保持 current-state only。
