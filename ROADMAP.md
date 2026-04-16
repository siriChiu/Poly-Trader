# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 07:48 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- q15 live lane 已達 **exact support 77 / 50**，`support_route_verdict=exact_bucket_supported`
- q15 audit freshness / stale fallback 問題已修正，不再把舊 bull-pocket blocker 誤回填到 current artifact
- q15 support artifact 已對齊成單一 current truth：
  - `support_governance_route=exact_live_bucket_supported`
  - `exact_bucket_root_cause=exact_bucket_supported`
  - `recommended_action=保持 current_live_structure_bucket_rows >= minimum_support_rows...`
- q15 component experiment 已補上 **positive discrimination machine-readable evidence**：
  - `preserves_positive_discrimination=true`
  - status=`verified_exact_lane_bucket_dominance`
  - q15 對 q35 的 exact-lane Δwin / Δquality / Δpnl 均為正
- q15 audit regression tests 已擴充並通過，鎖住 exact-supported truth 與 discrimination evidence contract

驗證完成：
- `source venv/bin/activate && python -m pytest tests/test_q15_support_audit.py tests/test_hb_predict_probe.py tests/test_live_decision_quality_drilldown.py tests/test_frontend_decision_contract.py tests/test_api_feature_history_and_predictor.py -q` → **65 passed**
- `source venv/bin/activate && python scripts/hb_predict_probe.py && python scripts/live_decision_quality_drilldown.py && python scripts/hb_q15_support_audit.py`
- `data/q15_support_audit.json` / `docs/analysis/q15_support_audit.md` 已顯示 exact-supported + discrimination-verified current state

---

## 主目標

### 目標 A：把 q15 exact-supported lane 做成真正 runtime floor-cross patch
重點：
- support 與 discrimination 兩個前提已收斂
- 直接處理 `feat_4h_bias50`，把 `entry_quality_below_trade_floor` 變成可驗證 runtime closure
- patch 必須讓 `allowed_layers > 0`，不能只停留在 counterfactual

### 目標 B：讓 probe / drilldown / q15 audit 完全共用同一份 q15 current-live truth
重點：
- probe 不可再內嵌舊 q15 audit 摘要
- q15 support / floor-cross / discrimination 三組 machine-readable 欄位必須在所有 surface 同步
- Dashboard / Strategy Lab 若讀到這條 lane，不能再看到互相矛盾的 blocker

### 目標 C：把 q15 的 exact-supported closure 變成 deployment 級證據
重點：
- `allowed_layers` 必須真的從 0 變成 >0
- `execution_guardrail_reason` / `deployment_blocker` 不得回歸
- pytest、live probe、q15 audit 必須共同證明 patch 後仍保留 positive discrimination

---

## 下一步
1. 實作 `feat_4h_bias50` 的 q15 exact-supported runtime patch
2. 讓 `hb_predict_probe.py` refresh / consume 最新 q15 audit summary，消除內嵌 stale truth
3. 重跑 probe + drilldown + q15 audit + regression tests，確認 q15 lane 真正從 `0 layers` 前進到可部署狀態

---

## 成功標準
- q15 current live row 不再卡在 `entry_quality_below_trade_floor`
- `allowed_layers > 0` 且 `execution_guardrail_reason` / `deployment_blocker` 不回歸
- `preserves_positive_discrimination=true` 仍成立，且證據繼續 machine-readable
- probe / drilldown / q15 audit / UI 對同一條 q15 lane 不出現語義漂移
