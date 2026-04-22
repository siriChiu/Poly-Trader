# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-22 12:30:18 CST_

---

## 心跳 #20260422t ORID

### O｜客觀事實
- 本輪直接重跑 current-live diagnostics：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/recent_drift_report.py` 均成功。
- current-live blocker 仍是 `deployment_blocker=unsupported_exact_live_structure_bucket`。
- current live bucket 仍為 `BLOCK|bull_high_bias200_overheat_block|q35`，`support=0/50`，`gap=50`，`support_route_verdict=exact_bucket_unsupported_block`，`support_governance_route=no_support_proxy`。
- drilldown 仍維持 `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_until_exact_support_ready` / `reference_scope=bull|CAUTION`。
- recent drift 仍以 `window=1000` 為主病灶：`win_rate=38.8%` / `dominant_regime=bull(81.3%)` / `alerts=regime_shift`。
- 本輪產品化 patch：Bot 營運 sleeve cards 已移除 duplicate sleeve-name pills，改為顯示 `策略：<title>` 或 `待儲存策略快照`；`pullback` 缺件狀態現在可直接在卡片頂部 machine-read / human-read。
- 驗證：`pytest tests/test_execution_surface_contract.py tests/test_frontend_decision_contract.py -q` → `52 passed`；`cd web && npm run build` 成功；browser `/execution` 已確認 duplicate texts 消失，且 `待儲存策略快照` 可見。

### R｜感受直覺
- current-live blocker truth 已穩，但 Bot 營運頁卡片頂部原本把 sleeve 名稱重複渲染成假資訊，會讓 operator 一眼看不出哪張卡是真的缺 strategy snapshot。
- 這種 UX 雜訊雖不改變 blocker math，卻直接傷害 execution surface 的可掃描性，尤其在 `covered sleeves 3/4 · missing pullback` 這種治理場景下會誤導判讀。

### I｜意義洞察
1. **execution surface clarity 本身就是 guardrail**：當 blocker 已經很多時，卡片標頭若還重複 sleeve 名稱，等於把真正重要的 `strategy binding status` 藏起來。
2. **missing strategy snapshot 必須在 operator 第一視線曝光**：`pullback` 缺件不是 runtime blocker，但它是 execution productization 的真實缺口，應與 blocker 文案分開呈現。
3. **current-live truth 無變更，但 operator UX 有實質前進**：本輪沒有改寫 blocker 事實，而是把 Bot 營運表面對齊到更可操作的 current-state truth。

### D｜決策行動
- **Owner**：execution operator surface / Bot 營運頁
- **Action**：保留 current-live blocker truth 不動，持續把 operator-facing execution cards 做到「先看得懂，再做決策」；下一步優先處理 `pullback` 缺少 saved strategy snapshot 的治理缺口。
- **Artifacts**：`web/src/pages/ExecutionConsole.tsx`、`tests/test_execution_surface_contract.py`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`data/recent_drift_report.json`。
- **Verify**：`pytest tests/test_execution_surface_contract.py tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/execution`。
- **If fail**：若 Bot 營運頁再次回到 duplicate sleeve labels，或 missing saved strategy 狀態重新被埋回卡片內文，視為 execution surface clarity regression，優先升級回 P1 operator UX blocker。
