# ISSUES.md — Current State Only

_最後更新：2026-04-17 07:19 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪主線是 **把 q15 lane 從「support accumulation blocker」推進到「exact-supported deployment verify」**，同時補回 API / backtest 的產品契約回歸。

本輪已完成的直接產品化前進：
- `scripts/hb_q15_support_audit.py` 現況已確認 **q15 exact bucket support = 77 / 50**，support route = `exact_bucket_supported`。
- `scripts/hb_predict_probe.py` 現在證明 live path 已不再卡 support blocker；目前卡的是 **entry floor**，不是 exact support。
- `/api/features` 重新輸出所有 feature 的 `raw_*` 欄位，且 `timestamp` 回到穩定 UTC `Z` 格式，避免 Dashboard / FeatureChart / probe contract 漂移。
- `/backtest` decision-quality 聚合 helper 已補回，回測 API 再次穩定輸出 canonical `decision_contract / avg_expected_* / avg_decision_quality_score`。

目前 runtime / governance 真相：
- live path：`bull / CAUTION / D`
- current live bucket：`CAUTION|structure_quality_caution|q15`
- q15 support：`77 / 50` → **exact-supported**
- support route：`exact_bucket_supported`
- floor-cross legality：`legal_component_experiment_after_support_ready`
- best single component：`feat_4h_bias50`
- current entry quality：`0.3238`
- trade floor：`0.55`
- remaining gap to floor：`0.233`
- current allowed layers：`0`
- current blocker 已從「support 不足」轉成「entry_quality_below_trade_floor」

驗證：
- `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_frontend_decision_contract.py -q` → **51 passed**
- `source venv/bin/activate && python scripts/hb_q15_support_audit.py` → `support_route_verdict=exact_bucket_supported`, `current_rows=77`, `component_experiment_verdict=exact_supported_component_experiment_ready`
- `source venv/bin/activate && python scripts/hb_predict_probe.py` → live row `bull / CAUTION / q15`, `allowed_layers=0`, `best_single_component=feat_4h_bias50`

---

## Open Issues

### P0. q15 support 已達標，但 current live row 仍卡在 entry floor
**現況**
- exact support 已達 `77 / 50`
- `feat_4h_bias50` 是唯一可單點跨 floor 的最佳 component
- 目前 `entry_quality=0.3238 < 0.55`，所以 runtime 仍不允許 layers

**風險**
- 若下一輪沒有做 exact-supported component patch + verify，系統會停在「治理已關閉，但產品仍無法部署」的半收斂狀態。

**下一步**
- 針對 `feat_4h_bias50` 做 **exact-supported component experiment**
- 必須同時驗證：`allowed_layers > 0`、`execution guardrail` 不回歸、`preserves_positive_discrimination` 有實證

### P0. API / backtest product contract 曾出現回歸，必須持續鎖住
**現況**
- `/api/features` 一度遺失 `raw_*` keys
- `/backtest` 一度遺失 `_compute_strategy_decision_quality_profile()` helper，導致 canonical DQ contract 退化
- 本輪已修回並以 pytest 鎖住

**風險**
- 若這類 contract 再次漂移，Dashboard / Strategy Lab / heartbeat artifact 會重新各說各話。

**下一步**
- exact-supported q15 patch 一律必須帶 `tests/test_api_feature_history_and_predictor.py`、`tests/test_hb_predict_probe.py`、`tests/test_frontend_decision_contract.py` 一起回歸

### P1. exact-supported deployment verify 尚未完成 runtime 放行證據
**現況**
- 本輪證明 support blocker 已解除
- 但尚未實作並驗證「support ready 之後，如何安全把 q15 row 推過 trade floor」的正式 patch

**風險**
- 如果只更新 audit / docs，不做 runtime patch，heartbeat 仍然只是治理描述，不是產品 closure。

**下一步**
- 做 bias50 exact-supported patch
- 用 `hb_predict_probe.py` + fast heartbeat + pytest 驗證 live contract 真正前進

---

## Not Issues
- 不是 q15 exact support 還不足：**已達 77 / 50**
- 不是 `/api/features` raw history contract 仍缺：本輪已修復 `raw_*` payload
- 不是 `/backtest` decision-quality contract 仍缺：本輪已恢復 canonical helper 與 response fields

---

## Current Priority
1. 把 q15 lane 從 **exact-supported** 真正推進到 **entry floor crossed with verified discrimination**
2. 讓 `/api/features`、`/backtest`、Dashboard、Strategy Lab 繼續共用同一套 canonical contract
3. exact-supported patch 落地後，立即用 fast heartbeat + probe 驗證是否真的產生可部署前進
