# ROADMAP.md — Current Plan Only

_最後更新：2026-05-15 23:18:43 CST_

本檔只保留目前產品化計畫；不保留歷史流水帳。

---

## 已完成（本輪）
- Heartbeat #1252 fast diagnostics 完成：`Raw=33285 / Features=24472 / Labels=66532`，`simulated_pyramid_win_rate=56.81%`。
- 重新跑 `hb_predict_probe.py` 與 `live_decision_quality_drilldown.py`，確認 current-live blocker 仍是 `under_minimum_exact_live_structure_bucket`。
- Patch：`scripts/live_decision_quality_drilldown.py` 現在把 current-live exact-support contract 提升到 top-level JSON：
  - `current_live_structure_bucket`
  - `current_live_structure_bucket_rows`
  - `exact_live_structure_bucket_rows`
  - `minimum_support_rows`
  - `current_live_structure_bucket_gap_to_minimum`
  - `support_governance_route`
  - `support_route_deployable`
  - `support_progress`
- Test guardrail：`tests/test_live_decision_quality_drilldown.py` 鎖定上述 top-level fields；`tests/test_server_startup.py` 鎖定 operator-facing runtime closure summary 使用繁中 humanized labels，避免 raw enum 外洩。
- 驗證：targeted runtime/test suite **170 passed**；heartbeat harness **PASS**。

---

## 主目標 A：current-live exact-support blocker 閉環
**目前真相**
- Current live：`bear / BLOCK / BLOCK|structure_quality_block|q00`。
- Deploy：`signal=HOLD`，`allowed_layers=0`，`deployment_blocker=under_minimum_exact_live_structure_bucket`。
- Support：`32/50`，缺口 `18`，`support_route_verdict=exact_bucket_present_but_below_minimum`，`support_governance_route=exact_live_bucket_present_but_below_minimum`。
- Progress：`stalled_under_minimum`，`stagnant_run_count=4`，`escalate_to_blocker=true`。

**成功標準**
- 同一 support identity exact rows 達 `>=50`。
- `/api/status`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、Dashboard、Strategy Lab、Execution Status 都能直接讀到 bucket / rows / minimum / gap / governance route。
- 買入 / 加倉在 blocker 未解除前保持 fail-closed；減倉 / 賣出風險降低路徑保留。

---

## 主目標 B：研究候選轉產品 gate，不跳過 runtime support
**目前真相**
- High-conviction top-k matrix fresh；`deployable_rows=0`，`risk_qualified_rows=6`，`runtime_blocked_candidates=6`。
- 最接近部署候選離線條件強，但仍因 q00 exact support `32/50` 被擋下。

**成功標準**
- Strategy Lab / leaderboard 顯示「runtime-blocked OOS pass」而不是 deployable。
- Gate 順序固定：OOS/ROI/風控 → current-live support → venue/runtime readiness。

---

## 主目標 C：reference-only truth 與 operator-safe copy
**目前真相**
- `core_plus_macro_plus_all_4h` patch 來自 `bull|CAUTION`，current live 是 `bear|BLOCK` q00，狀態必須是 `reference_only_non_current_live_scope`。
- q35 audit：`reference_only_current_bucket_outside_q35`，不是本輪 current-live blocker。

**成功標準**
- Operator-facing copy 不洩漏 raw backend enum；machine JSON 保留 raw fields。
- Reference patch / q35 audit 不可被當成 current-live deploy closure。

---

## 主目標 D：venue / source readiness
**目前真相**
- OKX 缺 live credential、order ack lifecycle、fill lifecycle proof。
- `fin_netflow` 缺 `COINGLASS_API_KEY`；`nest_pred` 有 TLS trust failure；`claw` 系列仍有 auth/coverage blockers。

**成功標準**
- Venue readiness 需要 `runtime_ready=true` 且無 blocker。
- TLS verification 不可關閉；auth 缺失不可用假資料補洞。

---

## 下一輪 gate
1. **Support accumulation gate**：把 q00 exact rows 從 `32/50` 推進；若 stagnation 持續，建立 support harvest/replay 任務。
2. **Surface contract gate**：檢查 `/api/status` / `/lab` / `/execution/status` 是否直接顯示 top-level bucket rows / gap / support_progress。
3. **Deployability gate**：若 top-k candidate 離線過關但 support 未滿，仍標為 `runtime_blocked_oos_pass`。
4. **Runtime proof gate**：OKX credential + ack + fill proof 未完成前，不開 live readiness。

---

## 必跑驗證
- `python scripts/hb_predict_probe.py`
- `python scripts/live_decision_quality_drilldown.py`
- `python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_predict_probe.py tests/test_runtime_closure_copy.py tests/test_server_startup.py tests/test_frontend_decision_contract.py -q`
- `python scripts/heartbeat_harness_check.py --format text`
