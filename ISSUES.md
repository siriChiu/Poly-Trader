# ISSUES.md — Current State Only

_最後更新：2026-04-18 20:23 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **P0 目前真相來自 `data/live_predict_probe.json`**：`current_live_structure_bucket=CAUTION|structure_quality_caution|q15`、`support_route_verdict=exact_bucket_supported`、`current_live_structure_bucket_rows=96 / 50`，但 top-level live baseline 仍是 `entry_quality=0.3385 / D / allowed_layers=0 / should_trade=false`，`deployment_blocker=decision_quality_below_trade_floor`。也就是說：**support 已 closure，但 live deployment truth 仍是明確 no-deploy**。
- **P1 canonical model leaderboard 仍是 placeholder-only，但已補上產品化 advisory**：`/api/models/leaderboard` 最新 cache/probe 仍是 `count=0 / comparable_count=0 / placeholder_count=6`；不過 payload 現在額外帶 `strategy_param_scan`，直接指出重掃後的 deployable strategy candidates，避免 operator 只看到空榜卻不知道下一個可用候選在哪裡。
- **策略排行榜已完成全模型重掃 refresh**：`scripts/rescan_models_and_refresh_strategy_leaderboard.py --top-per-model 1` 已重建 6 筆 `Auto Leaderboard · 重掃 ...` 候選，當前 `/api/strategies/leaderboard` 可見 6 筆最新自動候選；目前前段候選包含：
  - `Auto Leaderboard · 重掃 logistic_regression Hybrid #01` → ROI `0.2775`, trades `106`
  - `Auto Leaderboard · 重掃 lightgbm Hybrid #01` → ROI `0.2567`, trades `81`
  - `Auto Leaderboard · 重掃 xgboost Hybrid #01` → ROI `0.2580`, trades `106`
  - `Auto Leaderboard · 重掃 random_forest Hybrid #01` → win rate `0.6988`, trades `83`
- **rule_baseline 落盤異常已修復**：重掃腳本現在會把 `rule_baseline` 以 `rule_based` 而非錯誤的 `hybrid` 路徑保存，所以 `Auto Leaderboard · 重掃 rule_baseline #01` 已正常存在於 strategy store。
- **驗證現況**：
  - `python -m pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_rescan_models_and_refresh_strategy_leaderboard.py -q` → `68 passed`
  - `python -m py_compile server/routes/api.py backtesting/model_leaderboard.py scripts/rescan_models_and_refresh_strategy_leaderboard.py` → PASS
  - `python scripts/rescan_models_and_refresh_strategy_leaderboard.py --top-per-model 1` → PASS
  - `python scripts/hb_model_leaderboard_api_probe.py` → cache stable (`refreshing=false / stale=false`) 且 placeholder warning 仍存在

---

## Open Issues

### P0. q15 support is closed, but current live baseline still stays below trade floor
**現況**
- `support_route_verdict=exact_bucket_supported`
- `current_live_structure_bucket_rows=96 / 50`
- `q15_exact_supported_component_patch_applied=false`
- `entry_quality=0.3385 / entry_quality_label=D`
- `allowed_layers=0`
- `allowed_layers_reason=decision_quality_below_trade_floor`
- `deployment_blocker=decision_quality_below_trade_floor`
- `should_trade=false`

**風險**
- 如果 operator 只看 support closure，會誤判 q15 已可部署；但目前 live predictor 本身仍沒有跨過 trade floor，屬於明確 no-deploy runtime truth。

**下一步**
- 直接以 `data/live_predict_probe.json` 為單一 truth source，持續分清 support closure、component experiment、final execution gate 三者語義。
- 若要真正放行 q15，必須讓 top-level live baseline 本身達到 `entry_quality >= 0.55` 且 `allowed_layers > 0`；否則就維持 machine-readable no-deploy governance。
- 驗證方式：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/hb_parallel_runner.py --fast --hb <N>`、瀏覽器 `/execution/status`。

### P1. canonical model leaderboard is still empty, but scan-backed strategy candidates now exist
**現況**
- `/api/models/leaderboard` 仍是 `count=0 / comparable_count=0 / placeholder_count=6`
- placeholder-only warning 仍保留，沒有假裝正常排名
- payload 新增 `strategy_param_scan`，可直接讀到 6 筆重掃後候選；最佳 strategy candidate 目前是 `lightgbm` 路徑，scan artifact 顯示約 `ROI=0.3744 / trades=71`
- `scripts/rescan_models_and_refresh_strategy_leaderboard.py` 已把 scan 結果同步成 6 筆最新 auto strategies

**風險**
- canonical model leaderboard 仍無法直接回答「哪個模型 lane 在 canonical固定評估下可部署」；目前只是透過 scan advisory 與 strategy leaderboard 緩解產品可用性問題。

**下一步**
- 把 scan 發現的有效參數（例如 `bias50_max≈3.0`、`stop_loss≈-0.05`、`turning_point.bottom_score_min≈0.56~0.62`）回灌到 canonical model leaderboard deployment profiles，確認能否產生 `comparable_count > 0`。
- 在 canonical row 仍為 0 之前，Strategy Lab / operator UX 必須持續顯示 `strategy_param_scan` advisory，不得回退成只有空榜沒有下一步。
- 驗證方式：`python scripts/hb_model_leaderboard_api_probe.py` 與直接讀 `/api/models/leaderboard` payload；只有在 `comparable_count > 0` 時才可移除 placeholder-only 主警告。

---

## Not Issues
- **舊 Auto Leaderboard 候選仍殘留 / stale**：已修復；重掃腳本會先清掉舊 auto candidates，再重建當前版本。
- **rule_baseline 無法寫回 strategy store**：已修復；現在會走 `rule_based` 保存路徑。
- **model leaderboard cache 一直 stale/refreshing**：本輪已重新 refresh，最新 probe 為 `refreshing=false / stale=false`。

---

## Current Priority
1. **以 live predictor truth 收斂 q15：support 已 closure ≠ deployment 已 closure**
2. **把 canonical model leaderboard 從 placeholder-only 推進到至少一條 comparable row；在那之前持續暴露 strategy-param-scan advisory**
3. **維持策略排行榜與 scan artifact 同步，避免再次回退成 stale auto candidates**
