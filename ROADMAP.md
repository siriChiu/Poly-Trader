# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 12:47 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- 修補 `model/q35_bias50_calibration.py`：q35 bias50 segmented calibration 現在只允許套用在 `CAUTION|structure_quality_caution|q35`
- 修掉 q35 calibration 洩漏到 q15 lane 的 runtime-contract bug，避免 q15 exact-supported patch 被錯誤放大
- 新增 regression test：`test_piecewise_q35_bias50_calibration_ignores_non_q35_structure_bucket`
- 驗證 q15 exact-supported patch 仍維持預期行為：`entry_quality=0.5501`、`entry_quality_label=C`、`allowed_layers=1`
- 驗證通過：
  - `python -m pytest tests/test_api_feature_history_and_predictor.py::test_live_decision_profile_applies_q15_exact_supported_bias50_patch tests/test_api_feature_history_and_predictor.py::test_piecewise_q35_bias50_calibration_ignores_non_q35_structure_bucket -q` → `2 passed`
  - `python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_live_decision_quality_drilldown.py tests/test_frontend_decision_contract.py -q` → `66 passed`
- runtime probes 重新刷新：
  - `python scripts/hb_predict_probe.py`
  - `python scripts/live_decision_quality_drilldown.py`
  - `python scripts/hb_circuit_breaker_audit.py`
- runtime 最新 truth：仍是 `CIRCUIT_BREAKER`，canonical 1440m release gap = `14 wins`

---

## 主目標

### 目標 A：把 canonical 1440m circuit breaker 當成唯一 live blocker truth
重點：
- 本輪已確認 q15/q35 lane 修補不會覆蓋 canonical breaker
- 下一步要直接處理 aligned 1440m recent-50 tail pathology，而不是再做局部 lane 美化

成功標準：
- `/api/predict/confidence`、Dashboard、drilldown、heartbeat summary 全都顯示同一組 breaker release math
- breaker 未解除前，所有 lane patch / support artifact 都不能被表述成 deploy-ready
- 找出 recent 50 = `1/50` 的可執行 root-cause artifact

### 目標 B：完成 Binance execution lifecycle replay closure
重點：
- 目前還停在 lifecycle visibility / reconciliation contract
- 下一步要補 partial fill / cancel / restart replay artifact，建立 recovery 可驗證證據

成功標準：
- `/api/status.execution_reconciliation.lifecycle_contract` 可展示真實 partial fill / cancel / restart replay artifact
- Dashboard / Strategy Lab / `/api/status` 對同一筆 order 顯示一致 lifecycle replay verdict

### 目標 C：持續硬化 lane-boundary contract
重點：
- 本輪證明 q15/q35 runtime override 之間確實可能發生跨 lane 污染
- 下一步要把所有 runtime override 都收斂成明確 structure-bucket / scope guard

成功標準：
- q15 / q35 / broader-scope override 都有明確 lane guard
- 每個 override 都有 regression test 保證不會污染其他 lane
- live runtime sizing / entry quality / support verdict 不再出現跨-lane 漂移

---

## 下一步
1. 為 canonical 1440m breaker 補 tail-path root-cause artifact，直接解釋 recent 50 為何只剩 `1/50`
2. 以 Binance 為第一 venue，完成 partial fill / cancel / restart replay artifact 與 UI/API 同步顯示
3. 清查其餘 runtime override 是否仍有跨-lane leakage，補齊 lane-boundary regression tests

---

## 成功標準
- breaker 在解除前都維持 **單一 canonical truth**，不會被局部 lane patch 稀釋
- execution lifecycle 具備 **可 replay、可驗證、可恢復** 的 artifact，而非只有狀態可見
- q15 / q35 / runtime override 全部具備 **硬邊界 lane contract**，不再互相污染
