# ISSUES.md — Current State Only

_最後更新：2026-04-17 10:20 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪已把 **q15 live lane 的 exact-support truth contract** 從假性 blocker 中拉回產品 runtime：
- `model/predictor.py` 新增 **q15 exact-supported runtime support override**，當 current live row 已符合 q15 exact-supported component patch 條件時，不再因 calibration baseline 尚未重播而被誤判成 `unsupported_exact_live_structure_bucket`。
- 新增 regression test，鎖住：**q15 audit 已 exact-supported + preserves positive discrimination 時，structure-bucket guardrail 必須回放 exact support，而不是把 runtime 打回假 blocker。**
- 驗證：
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_api_feature_history_and_predictor.py -q` → **46 passed**
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_hb_predict_probe.py tests/test_q15_support_audit.py tests/test_live_decision_quality_drilldown.py tests/test_frontend_decision_contract.py -q` → **29 passed**
  - `source venv/bin/activate && python scripts/hb_predict_probe.py` → **deployment_blocker 已清空**、`current_live_structure_bucket_rows=79`、`support_route_verdict=exact_bucket_supported`
  - `source venv/bin/activate && python scripts/live_decision_quality_drilldown.py` → **deployment_blocker=null**、`allowed_layers_reason=entry_quality_below_trade_floor`
  - `source venv/bin/activate && python scripts/hb_q15_support_audit.py` → **exact_bucket_supported + exact_supported_component_experiment_ready + preserves_positive_discrimination=true**

目前 runtime / product 真相：
- live path：`bull / CAUTION / q15`
- q15 exact support：`79 / 50` → **exact-supported**
- support blocker：**已解除**（不再是 runtime 主 blocker）
- live runtime：
  - `signal=HOLD`
  - `entry_quality=0.3027`（`D`）
  - `allowed_layers=0`
  - `allowed_layers_reason=entry_quality_below_trade_floor`
- q15 audit：
  - `best_single_component=feat_4h_bias50`
  - `required_score_delta=0.8243`
  - `machine_read_answer.allowed_layers_gt_0=true`
  - `preserves_positive_discrimination=true`

---

## Open Issues

### P0. q15 support 假 blocker 已修，但 patch 啟用鏈仍未真正進入 live predictor
**現況**
- standalone `hb_q15_support_audit.py` 已明確給出 `exact_supported_component_experiment_ready`
- 但 `hb_predict_probe.py` 最終 live output 仍是 baseline：`q15_exact_supported_component_patch_applied=false`
- 目前 live blocker 已從「support 不足」收斂成單一問題：**patch activation / audit-consumption 沒有真正落到 predictor live path**

**風險**
- 產品會從「假 support blocker」進步到「support 已 ready、但 patch 沒消費」的半成品狀態
- Dashboard / Strategy Lab / probe 將持續看到相互矛盾的 q15 readiness 敘事

**下一步**
- 直接審查 `model/predictor.py::_maybe_apply_q15_exact_supported_component_patch()` 與 `scripts/hb_predict_probe.py` 的 in-process q15 audit refresh path
- 目標是讓 `hb_predict_probe.py` 最終 JSON 真正出現：
  - `q15_exact_supported_component_patch_applied=true`
  - `entry_quality>=0.55`
  - `allowed_layers=1`
  - 且 **deployment_blocker 仍保持 null**

### P0. q15 live lane 的 floor-cross research 已 ready，但 runtime 仍停在 trade-floor 前
**現況**
- `hb_q15_support_audit.py`：`best_single_component=feat_4h_bias50`、`required_score_delta=0.8243`
- `live_decision_quality_drilldown.py`：`remaining_gap_to_floor=0.2473`
- live predictor 目前仍輸出 `entry_quality_below_trade_floor`

**風險**
- support contract 雖然修好了，但 operator 仍拿不到任何 deployment capacity
- q15 將停在「governance-ready / support-ready / floor-cross-ready」卻沒有 runtime closure 的狀態

**下一步**
- 以 q15 patch activation 為唯一主線，要求 live predictor 真正吃到 bias50 counterfactual
- 驗證必須同時滿足：
  - `hb_predict_probe.py`
  - `live_decision_quality_drilldown.py`
  - `hb_q15_support_audit.py`
  - 以及對應 pytest

### P1. q15 audit 的 standalone truth 與 hb_predict_probe 內嵌 refresh 仍有收斂風險
**現況**
- standalone q15 audit 已能量測 `preserves_positive_discrimination=true`
- 但 live probe 的內嵌 q15 audit 消費鏈仍未可靠地把這份 truth 轉成 runtime patch 啟用

**風險**
- 之後若再改 q15 patch / drilldown / audit refresh，容易再次出現「standalone artifact 正確、live probe 還是錯」的 split-brain

**下一步**
- 把 `hb_predict_probe.py` 的 refresh/consume 路徑納入單一 regression 契約
- 之後每次改 q15 patch 路徑，都必須以 **live probe final JSON** 作為唯一 runtime 真相

---

## Not Issues
- 不是 q15 exact support 不足：**目前 `79 / 50`，已 exact-supported**
- 不是 q15 support blocker 還在：**`deployment_blocker` 已從 live probe / drilldown 清空**
- 不是 q15 component research 缺失：**`feat_4h_bias50` 與 `required_score_delta=0.8243` 已 machine-read**
- 目前主因是：**q15 patch readiness 已成立，但 live predictor 尚未真正吃到這條 ready path**

---

## Current Priority
1. 讓 **q15 exact-supported component patch 真正進入 live predictor**（驗證：probe 最終 patch=true、layers=1、blocker=null）
2. 鎖住 **standalone audit ↔ live probe refresh** 的單一真相鏈（驗證：pytest + fresh probe + fresh audit 一致）
3. q15 runtime patch 落地後，再切回 execution reconciliation / Binance-OKX venue readiness 主線
