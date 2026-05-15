# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-05-15 23:18:43 CST_

---

## 心跳 #1252 ORID

### O｜客觀事實
- Heartbeat #1252 fast diagnostics 完成：`Raw=33285 / Features=24472 / Labels=66532`，`simulated_pyramid_win_rate=56.81%`，latest raw timestamp `2026-05-15 15:02:20.860934`。
- 最新 probe：`signal=HOLD`，`allowed_layers=0`，`deployment_blocker=under_minimum_exact_live_structure_bucket`。
- Current-live bucket：`BLOCK|structure_quality_block|q00`；support `32/50`，gap `18`；`support_route_verdict=exact_bucket_present_but_below_minimum`；`support_governance_route=exact_live_bucket_present_but_below_minimum`；`support_route_deployable=false`。
- Support progress：`status=stalled_under_minimum`，`stagnant_run_count=4`，`stalled_support_accumulation=true`，`escalate_to_blocker=true`。
- Recent drift primary window：`500`，`win_rate=67.6%`，`dominant_regime=chop(75.4%)`，alerts=`regime_shift`。
- q35 audit：`reference_only_current_bucket_outside_q35`；q35 不是當前 live lane。
- Reference patch：`core_plus_macro_plus_all_4h` 仍是 `reference_only_non_current_live_scope`；來源 `bull|CAUTION`，current live 為 `bear|BLOCK`。
- 本輪 patch 已把 live DQ drilldown 的 support truth 提升到 top-level JSON fields，並用 tests 鎖定；targeted verification `170 passed`，harness `PASS`。

### R｜感受直覺
- 最大風險不是模型沒有候選，而是 operator 把「OOS 表現好」或「reference patch 存在」誤讀成部署已放行。
- q00 exact support 已連續停在 `32/50`；如果只藏在 nested blocker，Dashboard / Lab / docs 很容易再次漂移。

### I｜意義洞察
1. **Support truth 必須成為產品 API 合約**：bucket / rows / minimum / gap / governance route 不能只存在於 nested `deployment_blocker_details`。
2. **Reference-only 是安全功能，不是弱點**：q35 audit 與 bull|CAUTION patch 可以提供治理方向，但不能取代 current-live q00 exact rows。
3. **Operator-safe copy 是防錯護欄**：machine JSON 可保留 raw enum；runtime closure summary / operator markdown 必須使用繁中人類語意，避免 enum soup 被當成操作指令。
4. **下一個真 gate 是 support harvest / replay**：若 q00 exact rows 不增加，high-conviction top-k 只能停在 runtime-blocked OOS pass。

### D｜決策行動
- **Decision**：本輪不推 live exposure；維持 `under_minimum_exact_live_structure_bucket` 為唯一 current-live deployment blocker。
- **Patch**：`scripts/live_decision_quality_drilldown.py` promoted current-live support fields to top-level artifact；`tests/test_live_decision_quality_drilldown.py` / `tests/test_server_startup.py` 鎖定 top-level support contract 與 operator-safe copy。
- **Verify**：
  - `python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_predict_probe.py tests/test_runtime_closure_copy.py tests/test_server_startup.py tests/test_frontend_decision_contract.py -q` → `170 passed`。
  - `python scripts/heartbeat_harness_check.py --format text` → `RESULT: PASS`。
  - `python scripts/hb_predict_probe.py` + `python scripts/live_decision_quality_drilldown.py` → refreshed live artifacts。
- **Next gate**：補滿 q00 exact support `32/50 → 50/50`；若停滯持續，建立 support harvest/replay；同時保持 top-k candidates、q35 audit、reference patch 都 fail-closed / reference-only。
