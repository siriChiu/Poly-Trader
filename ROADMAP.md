# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 07:19 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- q15 support route 已從 `under_minimum_exact_live_structure_bucket` 推進到 **`exact_bucket_supported`**
- `scripts/hb_q15_support_audit.py` 現在確認 current q15 exact bucket = **77 / 50**
- `scripts/hb_predict_probe.py` 已證明 live q15 row 的 blocker 不再是 support shortage，而是 **entry floor gap**
- `/api/features` 已恢復 `raw_*` feature payload 與穩定 UTC `timestamp` contract
- `/backtest` 已恢復 canonical decision-quality aggregation helper，API 再次穩定輸出 `decision_contract + avg_expected_* + avg_decision_quality_score`
- `tests/test_api_feature_history_and_predictor.py`、`tests/test_hb_predict_probe.py`、`tests/test_frontend_decision_contract.py` 本輪回歸全綠

驗證完成：
- `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_frontend_decision_contract.py -q` → **51 passed**
- `source venv/bin/activate && python scripts/hb_q15_support_audit.py` → `exact_bucket_supported`, `current_rows=77`
- `source venv/bin/activate && python scripts/hb_predict_probe.py` → current live `bull / CAUTION / q15`, `allowed_layers=0`, `best_single_component=feat_4h_bias50`

---

## 主目標

### 目標 A：完成 q15 exact-supported component deployment verify
重點：
- support 已達標，下一步不是再追 support rows
- 直接驗證 `feat_4h_bias50` exact-supported component patch 能否把 current q15 row 安全推過 trade floor
- 必須同時保住 positive discrimination，不可只把 floor 硬推過去

### 目標 B：維持 live / API / backtest / frontend 的 canonical contract 同步
重點：
- `/api/features` 必須保留 `raw_*` 與 UTC timestamp
- `/backtest` 必須保留 canonical decision-quality summary
- Dashboard / Strategy Lab / heartbeat artifact 必須繼續消費同一套 live truth

### 目標 C：把 exact-supported governance 變成 runtime 證據，而不是只停在 audit
重點：
- `hb_predict_probe.py`
- fast heartbeat
- frontend/runtime regression tests
三者都必須能證明 current q15 lane 有實際產品化前進，而不是只有文件說 support ready

---

## 下一步
1. 對 `feat_4h_bias50` 實作 q15 exact-supported component patch
2. 用 `hb_predict_probe.py` 驗證 `allowed_layers` 是否真的從 0 推進，且 guardrail 理由仍正確
3. 重跑 fast heartbeat 與回歸測試，確認 q15 lane 的 deployment closure 沒有造成 contract regression

---

## 成功標準
- q15 current live row 不再卡在 `entry_quality_below_trade_floor`
- `allowed_layers > 0` 且沒有引入新的 deployment / execution blocker
- `preserves_positive_discrimination` 有明確驗證證據
- `/api/features`、`/backtest`、Dashboard、Strategy Lab、heartbeat artifact 對同一條 q15 live lane 不出現語義漂移
