# ISSUES.md — Current State Only

_最後更新：2026-04-17 07:33 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪主線是 **把 q15 lane 的 live truth 對齊到同一份 current artifact，再往 exact-supported component deployment verify 推進**。

本輪已完成的直接產品化前進：
- `scripts/hb_q15_support_audit.py` 現在會在 probe 較新、drilldown 過期時自動重建 `live_decision_quality_drilldown`，避免 heartbeat artifact 繼續吃舊 snapshot。
- q15 audit 不再把 stale `execution_guardrail_reason` 從舊 drilldown / bull pocket 回填到 current-live 報告；現在會尊重 probe 的顯式 `null`，避免把已解除的 support blocker 誤報回來。
- current q15 artifact 已重新對齊：`support_route_verdict=exact_bucket_supported`、`execution_guardrail_reason=null`、`remaining_gap_to_floor=0.2262`。
- q15 artifact freshness / fallback 行為已用 pytest 鎖住，避免下一輪再出現「probe 已前進、audit 仍停在舊 blocker」的語義漂移。

目前 runtime / governance 真相：
- live path：`bull / CAUTION / D`
- current live bucket：`CAUTION|structure_quality_caution|q15`
- q15 support：`77 / 50` → **exact-supported**
- support route：`exact_bucket_supported`
- execution guardrail：**none**（`execution_guardrail_reason=null`）
- deployment blocker：**none**
- current blocker：`entry_quality_below_trade_floor`
- current entry quality：`0.3238`
- trade floor：`0.55`
- remaining gap to floor：`0.2262`
- best single component：`feat_4h_bias50`
- bias50 fully relaxed counterfactual：`entry≈0.5916 / layers≈1 / required_bias50_cap≈-1.9065`

驗證：
- `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_frontend_decision_contract.py tests/test_q15_support_audit.py tests/test_live_decision_quality_drilldown.py -q` → **65 passed**
- `source venv/bin/activate && python scripts/hb_predict_probe.py && python scripts/live_decision_quality_drilldown.py && python scripts/hb_q15_support_audit.py` → q15 / drilldown artifacts 同步刷新
- `data/q15_support_audit.json` → `execution_guardrail_reason=null`, `support_route_verdict=exact_bucket_supported`, `remaining_gap_to_floor=0.2262`
- `data/live_decision_quality_drilldown.json` → `deployment_blocker=null`, `allowed_layers_reason=entry_quality_below_trade_floor`, `current_live_structure_bucket_rows=77`

---

## Open Issues

### P0. q15 已 exact-supported，但 current live row 仍未跨過 trade floor
**現況**
- support blocker 已解除，runtime 現在卡的是純 `entry_quality_below_trade_floor`
- `feat_4h_bias50` 仍是唯一可單點跨 floor 的 component
- counterfactual 顯示 bias50 若完全放鬆可到 `entry≈0.5916 / layers≈1`

**風險**
- 如果直接放鬆 bias50 而不驗證 discrimination，可能把 q15 lane 從「可部署候選」推成「可跨 floor 但語義不安全」的假 closure。

**下一步**
- 對 `feat_4h_bias50` 做 **exact-supported component patch**
- 必須同時驗證：`allowed_layers > 0`、`execution_guardrail` 不回歸、`preserves_positive_discrimination` 有實證

### P0. q15 / drilldown / Dashboard / Strategy Lab 必須持續共用同一份 current-live truth
**現況**
- 本輪已修掉 q15 audit 對 stale drilldown blocker 的錯誤回填
- 但 exact-supported component patch 一旦上線，所有 surface 都必須一起看到同一個 q15 live 結論

**風險**
- 若 probe、drilldown、audit、frontend 任一處再次吃到舊 artifact，使用者會看到互相矛盾的 runtime 敘事。

**下一步**
- q15 component patch 一律帶 `tests/test_api_feature_history_and_predictor.py`、`tests/test_hb_predict_probe.py`、`tests/test_frontend_decision_contract.py`、`tests/test_q15_support_audit.py`、`tests/test_live_decision_quality_drilldown.py`
- patch 後必跑 probe + drilldown + q15 audit 三連刷新，確認 blocker 與 layer reason 全面同步

### P1. exact-supported deployment verify 仍缺 positive discrimination 證據
**現況**
- q15 support audit 只證明 `feat_4h_bias50` 在數學上可跨 floor
- `preserves_positive_discrimination` 仍是 `not_measured_requires_followup_verify`

**風險**
- 沒有 discrimination 證據就放行，會把「數學跨 floor」誤當成「產品可部署」。

**下一步**
- 補 exact-supported q15 component experiment 的 discrimination verify
- fast heartbeat / probe / pytest 必須一起證明它不是 unsafe floor-cross

---

## Not Issues
- 不是 q15 exact support 不足：**已達 77 / 50**
- 不是 runtime 仍卡 `unsupported_exact_live_structure_bucket`：**已解除**
- 不是 current artifact 仍停在舊 support blocker：**本輪已修正 freshness / fallback drift**

---

## Current Priority
1. 把 q15 lane 從 **exact-supported + floor gap** 推進到 **跨過 floor 且保住 discrimination**
2. 讓 probe / drilldown / q15 audit / frontend 在 q15 lane 上繼續維持單一 live truth
3. component patch 落地後，用 fast heartbeat + probe + pytest 證明是真正 deployment closure，而不是 artifact 假前進
