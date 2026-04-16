# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 07:33 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- q15 live lane 已達 **exact support 77 / 50**，`support_route_verdict=exact_bucket_supported`
- q15 heartbeat artifact 已補上 freshness 自癒：`hb_q15_support_audit.py` 會在 probe 較新時自動刷新 `live_decision_quality_drilldown`
- q15 audit 已停止從 stale drilldown 回填舊 blocker；current live truth 現在正確顯示 `execution_guardrail_reason=null`
- current q15 artifact 已對齊成同一份 truth：`allowed_layers=0` 是因為 `entry_quality_below_trade_floor`，不是 support blocker
- q15 artifact freshness / fallback regression tests 已補齊並通過

驗證完成：
- `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_frontend_decision_contract.py tests/test_q15_support_audit.py tests/test_live_decision_quality_drilldown.py -q` → **65 passed**
- `source venv/bin/activate && python scripts/hb_predict_probe.py && python scripts/live_decision_quality_drilldown.py && python scripts/hb_q15_support_audit.py` → current q15 artifacts 全部刷新
- `data/q15_support_audit.json` → `execution_guardrail_reason=null`, `remaining_gap_to_floor=0.2262`, `best_single_component=feat_4h_bias50`

---

## 主目標

### 目標 A：完成 q15 exact-supported bias50 deployment verify
重點：
- support 已收斂，不再花主時間追 support rows
- 直接驗證 `feat_4h_bias50` patch 能否把 current q15 row 安全推過 floor
- 必須把 `preserves_positive_discrimination` 變成 machine-readable verified evidence

### 目標 B：維持 q15 live artifact 單一真相
重點：
- `hb_predict_probe.py`
- `live_decision_quality_drilldown.py`
- `hb_q15_support_audit.py`
- Dashboard / Strategy Lab / API
以上都必須對同一條 q15 live lane 輸出一致 blocker 與 layer reason

### 目標 C：把 q15 的 exact-supported closure 變成 runtime 證據
重點：
- `allowed_layers` 必須真的 > 0 才算前進
- 不能用 stale artifact、proxy semantics、或數學 counterfactual 冒充 deployment closure
- fast heartbeat 與 pytest 必須共同證明 patch 沒有帶來 contract regression

---

## 下一步
1. 實作 `feat_4h_bias50` 的 q15 exact-supported component patch
2. 補 `preserves_positive_discrimination` 驗證，確認不是 unsafe floor-cross
3. 重跑 probe + drilldown + q15 audit + regression tests，確認 q15 lane 真正從 `0 layers` 前進到可部署狀態

---

## 成功標準
- q15 current live row 不再卡在 `entry_quality_below_trade_floor`
- `allowed_layers > 0` 且 `execution_guardrail_reason` / `deployment_blocker` 不回歸
- `preserves_positive_discrimination` 有明確 machine-readable 證據
- probe / drilldown / q15 audit / Dashboard / Strategy Lab 對同一條 q15 lane 不出現語義漂移
