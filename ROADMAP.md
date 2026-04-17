# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 12:40 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- heartbeat 本輪實際推進資料：`Raw=30591 (+1) / Features=22009 (+1) / Labels=61736 (+1)`
- `scripts/hb_collect.py` 成功完成 collect / feature / label 閉環
- canonical 診斷刷新：`Global IC=14/30`、`TW-IC=29/30`
- `recent_drift_report.py` 已重新確認最近 500 筆是 bull-only distribution pathology，不是 collector 停擺
- circuit breaker release math 已打通到 runtime contract：
  - `model/predictor.py`
  - `scripts/hb_predict_probe.py`
  - `scripts/live_decision_quality_drilldown.py`
  - Dashboard `ConfidenceIndicator`
- Dashboard 在 breaker 狀態下已能直接顯示「還差幾勝解除 blocker」，不再誤顯示 support/floor-cross 卡片
- 驗證通過：
  - `python -m pytest tests/test_api_feature_history_and_predictor.py::test_circuit_breaker_uses_simulated_target_column tests/test_hb_predict_probe.py tests/test_live_decision_quality_drilldown.py tests/test_frontend_decision_contract.py -q` → `20 passed`
  - runtime probes：
    - `python scripts/hb_predict_probe.py`
    - `python scripts/live_decision_quality_drilldown.py`
    - `python scripts/hb_circuit_breaker_audit.py`

---

## 主目標

### 目標 A：把 canonical 1440m circuit breaker 做成真正可操作的 runtime blocker
重點：
- 本輪已補齊 release math contract 與 Dashboard 顯示
- 下一步不是關 breaker，而是把所有 runtime / API / UI surface 都鎖成同一個 canonical 1440m truth

成功標準：
- `/api/predict/confidence`、Dashboard、drilldown、heartbeat summary 都顯示同一組：
  - `current_recent_window_wins`
  - `required_recent_window_wins`
  - `additional_recent_window_wins_needed`
  - `current_streak`
- 不再把 support / component patch / q15 floor-cross 誤說成 breaker release progress

### 目標 B：完成 Binance execution lifecycle single source of truth
重點：
- 現在已有 lifecycle visibility contract
- 下一步要把 partial fill / cancel / restart replay 從「可見缺口」推進到「有真 artifact、可回放、可驗證」

成功標準：
- `/api/status.execution_reconciliation.lifecycle_contract` 能顯示 partial fill / cancel / restart replay artifact 已觀察到
- Dashboard / Strategy Lab 對同一筆 order 顯示一致 lifecycle replay verdict

### 目標 C：持續治理 recent bull-only pathology 與 sparse-source blockers
重點：
- breaker 解除前後都要防止 polluted recent slice 被當成 deployment readiness
- sparse-source 要持續分流 auth-blocked / archive-gap / snapshot-only

成功標準：
- live calibration / leaderboard 不再把 bull-only pocket 當 readiness 證據
- `fin_netflow` auth 問題被獨立追蹤，其他 sparse source 不再混成 generic coverage 問題

---

## 下一步
1. 驗證 `/api/predict/confidence` 與 Dashboard 在 live runtime 中都已顯示 **breaker release math**，並把同一份數據同步進 heartbeat summary
2. 以 Binance 為第一 venue，補齊 **partial fill / cancel / restart replay artifact**，把 execution reconciliation 從 visibility 推到 replay closure
3. breaker 解除後，立刻重驗 **recent bull-only pathology** 是否仍在污染 live calibration / decision-quality

---

## 成功標準
- circuit breaker 不再只是抽象 blocker，而是 **可量化、可追 release progress、可在 UI 直接判讀** 的 runtime contract
- execution lifecycle 不只可見，而是 **可 replay、可驗證、可對同一 order 給一致 verdict**
- live calibration 不再被 recent bull-only window 或 sparse-source maturity 假象誤導
