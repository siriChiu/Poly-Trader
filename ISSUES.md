# ISSUES.md — Current State Only

_最後更新：2026-04-18 18:40 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **q15 live lane 的 support closure 已成立，但 live predictor 仍是 trade-floor blocker**：`current_live_structure_bucket=CAUTION|structure_quality_caution|q15`、`support_route_verdict=exact_bucket_supported`、`support_rows=96/50`，但 `hb_predict_probe.py` 最新 top-level live truth 仍是 `entry_quality=0.4181 / D / allowed_layers=0 / allowed_layers_reason=decision_quality_below_trade_floor`。
- **q15 stale-audit 假 patch-ready probe bug 已修掉**：`hb_predict_probe.py` 現在會先 refresh `q15_support_audit`、必要時 replay prediction、audit/probe 不一致時再 force-refresh，避免舊 audit 讓 probe 假裝已 patch active。
- **model leaderboard zero-trade surface 已修成 placeholder-only governance**：`/api/models/leaderboard` / `hb_model_leaderboard_api_probe.py` 最新結果為 `count=0 / comparable_count=0 / placeholder_count=6 / evaluated_row_count=6`，並帶 `leaderboard_warning=目前 6 個模型都沒有產生任何交易；排行榜已降級為 placeholder 檢視，請勿把 #1 當成可部署排名。`
- **驗證現況**：
  - `python -m pytest tests/test_hb_predict_probe.py tests/test_model_leaderboard.py tests/test_model_leaderboard_api_cache.py tests/test_hb_model_leaderboard_api_probe.py tests/test_strategy_leaderboard_contract.py tests/test_q15_support_audit.py -q` → `57 passed`
  - `python -m pytest tests/test_frontend_decision_contract.py tests/test_server_startup.py -q` → `36 passed`
  - `cd web && npm run build` → PASS

---

## Open Issues

### P0. q15 current-live lane is exact-supported, but live predictor still remains below trade floor
**現況**
- `support_route_verdict=exact_bucket_supported`
- `support_rows=96 / 50`
- `hb_predict_probe.py` top-level live truth：`entry_quality=0.4181 / D / allowed_layers=0`
- `allowed_layers_reason=decision_quality_below_trade_floor`
- `q15_exact_supported_component_patch_applied=false`
- `q15_support_audit.component_experiment.verdict=exact_supported_component_experiment_ready`

**風險**
- support closure 已完成，但 live predictor 還沒跨過 trade floor；如果 operator 只看到 audit/component experiment ready，仍可能把研究型 patch readiness 誤讀成 deployment closure。

**下一步**
- 把 `q15_support_audit` 的 component experiment 與 `hb_predict_probe` 的 live baseline 明確分層，不再讓兩者語義混淆。
- 若要真正放行 q15，必須讓 live predictor 本身達到 `entry_quality >= 0.55` 且 `allowed_layers > 0`；否則就維持 machine-readable no-deploy governance。
- 驗證方式：`python scripts/hb_predict_probe.py` 與相關 pytest 必須同時證明 top-level live truth 與 audit semantics 一致。

### P1. model leaderboard is now honest, but still has zero comparable models
**現況**
- `/api/models/leaderboard` 最新 probe：`count=0 / comparable_count=0 / placeholder_count=6`
- warning 已明確指出「placeholder-only」
- zero-trade rows 不再偽裝成正常 top-ranked winners，但目前仍沒有任何可比較、可部署的 model row

**風險**
- Strategy Lab 雖然不再被假排行榜誤導，但現在仍缺少真正可比較的 deployment 候選；產品層面仍無法回答「目前哪個模型可部署」。

**下一步**
- 追出為何 6 個 refresh models 全都 `avg_trades=0`，確認是 deployment profile、資料窗口、target semantics，還是 run/evaluation path 本身沒有產生 trade。
- 在找出真正可交易 row 之前，所有 operator / Strategy Lab surface 都必須保留 placeholder-only warning，不得回退成正常排名語氣。
- 驗證方式：`python scripts/hb_model_leaderboard_api_probe.py` 必須先維持 placeholder warning；之後若修好，至少要看到 `comparable_count>0`。

---

## Not Issues
- **q15 stale support audit 讓 probe 假裝 patch-ready / support-ready**：已修復；probe 現在會 refresh audit、必要時 replay prediction，避免直接相信舊 audit。
- **model leaderboard cache 把 zero-trade rows 當正常 top-ranked rows**：已修復；placeholder rows 現在會被分離，`leaderboard_warning` 也會 machine-read 保留。

---

## Current Priority
1. **把 q15 current-live 問題收斂成真正的 live deployment truth，而不是 audit-ready 假 closure**
2. **把 model leaderboard 從「誠實但全 placeholder」推進到至少一條可比較的 deployment row**
