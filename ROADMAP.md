# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 10:20 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- q15 live lane 的 **exact-support truth contract** 已進入 predictor runtime guardrail：
  - `model/predictor.py` 新增 `q15 exact-supported runtime support override`
  - 當 q15 audit 已 exact-supported 且 discrimination 保持正向時，不再把 current live row 誤判成 `unsupported_exact_live_structure_bucket`
- regression 已鎖住：
  - q15 exact-supported runtime support replay
  - predictor structure-bucket guardrail 不可再回退成假 blocker
- 驗證完成：
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_api_feature_history_and_predictor.py -q` → **46 passed**
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_hb_predict_probe.py tests/test_q15_support_audit.py tests/test_live_decision_quality_drilldown.py tests/test_frontend_decision_contract.py -q` → **29 passed**
  - `source venv/bin/activate && python scripts/hb_predict_probe.py` → **deployment_blocker=null**、`current_live_structure_bucket_rows=79`
  - `source venv/bin/activate && python scripts/live_decision_quality_drilldown.py` → **support blocker 不再是 runtime 主因**
  - `source venv/bin/activate && python scripts/hb_q15_support_audit.py` → **exact_bucket_supported / preserves_positive_discrimination=true**

---

## 主目標

### 目標 A：讓 q15 patch readiness 真正落到 live predictor
重點：
- support blocker 已解除，下一步不再是證明 q15 support，而是讓 `feat_4h_bias50` patch 真正被 predictor consume
- 唯一可接受的成功證據是 `hb_predict_probe.py` 最終 JSON 出現：
  - `q15_exact_supported_component_patch_applied=true`
  - `entry_quality>=0.55`
  - `allowed_layers=1`
  - `deployment_blocker=null`

### 目標 B：鎖住 q15 audit ↔ probe refresh 的單一真相鏈
重點：
- standalone audit 已能量測 `preserves_positive_discrimination=true`
- 下一步是避免 live probe 內嵌 refresh 再把這條 truth 漏掉
- 驗證標準是 **fresh audit、fresh probe、fresh drilldown 三者同時一致**

### 目標 C：q15 runtime patch 關閉後，再回到 execution productization 主線
重點：
- execution reconciliation / recovery
- Dashboard / Strategy Lab runtime truth 對齊
- Binance / OKX venue readiness

---

## 下一步
1. 直接審查 `scripts/hb_predict_probe.py` 的 q15 audit refresh / replay 消費鏈，確保 standalone audit 的 machine-read truth 能真正驅動 predictor patch；驗證以 `hb_predict_probe.py + hb_q15_support_audit.py + pytest`
2. 一旦 q15 patch 真落地，重新驗證 `entry_quality>=0.55`、`allowed_layers=1`、`deployment_blocker=null`、`signal/guardrail/runtime_closure` 一致；驗證以 `hb_predict_probe.py + live_decision_quality_drilldown.py + pytest`
3. q15 runtime closure 完成後，再切回 execution reconciliation / venue readiness；驗證以 `/api/status`、Dashboard runtime surface、相關 pytest/runtime evidence

---

## 成功標準
- q15 不再停在「support ready 但 predictor 沒消費」的半成品狀態
- live probe 與 standalone audit 對 q15 readiness 的 machine-read 結論完全一致
- `allowed_layers` 從 0 推進到 1，且不引入新的 deployment_blocker / execution_guardrail 漂移
