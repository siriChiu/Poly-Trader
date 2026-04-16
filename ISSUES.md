# ISSUES.md — Current State Only

_最後更新：2026-04-17 07:48 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪主線是 **把 q15 lane 從 exact-supported 研究態推進到可驗證 deployment patch 態，先修正 audit truth，再把 positive discrimination 證據 machine-readable 化。**

本輪已完成的直接產品化前進：
- `scripts/hb_q15_support_audit.py` 現在會在 **exact-supported** 時把 `support_governance_route / exact_bucket_root_cause / recommended_action` 對齊為 current-live truth，不再沿用舊的 under-minimum/stale bull-pocket 敘事。
- q15 audit 現在會從 exact-lane bucket diagnostics 自動計算 `positive_discrimination_evidence`，把 `preserves_positive_discrimination=true` 與比較證據寫入 `data/q15_support_audit.json`。
- `docs/analysis/q15_support_audit.md` 已同步顯示：q15 lane 不只是 exact-supported，還已有 **verified_exact_lane_bucket_dominance**，避免文件繼續把可驗證 lane 寫成「尚未量測」。
- regression tests 已鎖住兩個 contract：
  1. exact-supported 時不得回填 stale support blocker
  2. q15 component experiment 必須輸出 positive discrimination 證據

目前 runtime / governance 真相：
- live path：`bull / CAUTION / D`
- current live bucket：`CAUTION|structure_quality_caution|q15`
- q15 support：`77 / 50` → **exact-supported**
- support route：`exact_live_bucket_supported`
- execution guardrail：**none**（`execution_guardrail_reason=null`）
- deployment blocker：**none**
- current blocker：`entry_quality_below_trade_floor`
- current entry quality：`0.3238`
- trade floor：`0.55`
- remaining gap to floor：`0.2262`
- best single component：`feat_4h_bias50`
- bias50 fully-relaxed counterfactual：`entry≈0.5916 / layers≈1 / required_bias50_cap≈-1.9065`
- exact-lane discrimination evidence：`q15 win/pnl/quality > q35`（Δwin=+0.1463 / Δquality=+0.1367 / Δpnl=+0.0029）

驗證：
- `source venv/bin/activate && python -m pytest tests/test_q15_support_audit.py tests/test_hb_predict_probe.py tests/test_live_decision_quality_drilldown.py tests/test_frontend_decision_contract.py tests/test_api_feature_history_and_predictor.py -q` → **65 passed**
- `source venv/bin/activate && python scripts/hb_predict_probe.py && python scripts/live_decision_quality_drilldown.py && python scripts/hb_q15_support_audit.py` → q15 artifacts 重新刷新
- `data/q15_support_audit.json` → `support_governance_route=exact_live_bucket_supported`, `exact_bucket_root_cause=exact_bucket_supported`, `preserves_positive_discrimination=true`
- `docs/analysis/q15_support_audit.md` → 已顯示 `verified_exact_lane_bucket_dominance`

---

## Open Issues

### P0. q15 已 exact-supported 且 discrimination 已驗證，但 current live row 仍未跨過 trade floor
**現況**
- support blocker 已解除，positive discrimination 也已 machine-read 驗證
- runtime 現在卡的是純 `entry_quality_below_trade_floor`
- `feat_4h_bias50` 仍是唯一可單點跨 floor 的 component

**風險**
- 如果沒有把 bias50 patch 做成真正 runtime/pytest/probe 閉環，q15 lane 會停在「研究上可行、產品上仍 0 layers」的半成品狀態。

**下一步**
- 實作 q15 exact-supported 的 `feat_4h_bias50` 保守 patch
- 必須同時驗證：`allowed_layers > 0`、`execution_guardrail` 不回歸、Dashboard / drilldown / probe 對同一條 q15 live row 保持一致

### P0. hb_predict_probe 內嵌的 q15 audit 摘要仍可能落後於 audit 重跑後的新 truth
**現況**
- 本輪 runner 先跑 `hb_predict_probe.py`，再跑 `hb_q15_support_audit.py`
- 因此 probe payload 內嵌的 `q15_support_audit` 區塊仍可能是上一輪摘要，而 `data/q15_support_audit.json` 已是新 truth

**風險**
- 主要 audit artifact 已正確，但 probe 內嵌摘要若被直接引用，仍可能讓使用者看到舊 blocker 敘事。

**下一步**
- 讓 probe 在需要時 refresh 或只引用最新 q15 audit summary
- 驗證 probe / q15 audit / drilldown 三者對 `support_route` 與 `preserves_positive_discrimination` 完全一致

### P1. exact-supported q15 deployment verify 還缺真正 runtime floor-cross evidence
**現況**
- 目前只證明 `bias50` 在 counterfactual 下可把 q15 lane 推到 `entry≈0.5916 / layers≈1`
- 尚未把這個 counterfactual 落成 predictor/runtime patch

**風險**
- 若沒有實際 runtime patch，q15 lane 仍然只是 artifact closure，不是產品 closure。

**下一步**
- 先做最小 bias50 patch，再以 pytest + live probe + q15 audit 驗證它是真正 deployment 前進

---

## Not Issues
- 不是 q15 exact support 不足：**已達 77 / 50**
- 不是 `unsupported_exact_live_structure_bucket`：**已解除**
- 不是 `preserves_positive_discrimination` 完全未量測：**本輪已驗證並持久化證據**

---

## Current Priority
1. 把 q15 lane 從 **exact-supported + discrimination-verified + 0 layers** 推進到 **runtime floor-cross closure**
2. 修掉 probe 內嵌 q15 audit 摘要與獨立 q15 artifact 之間的 freshness 風險
3. 用 pytest + live probe + q15 audit 證明 bias50 patch 是真正 deployment 前進，而不是只更新報告
