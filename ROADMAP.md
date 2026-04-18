# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 20:23 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **hybrid / model leaderboard 路徑已補齊 local turning-point context**：`server/routes/api.py` 與 `backtesting/model_leaderboard.py` 現在都會把 `feat_local_bottom_score` / `feat_local_top_score` 傳入 `run_hybrid_backtest()`；canonical 掃描不再遺漏 turning-point gating。
- **leaderboard frame 已補齊 regime / turning-point 欄位**：`load_model_leaderboard_frame()` 現在會載入 `regime_label`、`feat_local_bottom_score`、`feat_local_top_score`、`feat_turning_point_score`。
- **全模型重掃腳本已建立並驗證**：`scripts/rescan_models_and_refresh_strategy_leaderboard.py --top-per-model 1` 會重掃 refresh models、做參數搜尋、清掉舊 auto candidates、重建最新 strategy leaderboard。
- **策略排行榜已刷新成 6 筆最新 auto candidates**：包含 `rule_baseline`、`logistic_regression`、`xgboost`、`lightgbm`、`catboost`、`random_forest` 各 1 筆最佳候選。
- **model leaderboard placeholder-only 狀態已產品化一層**：`/api/models/leaderboard` 現在雖然仍是 `count=0`，但 payload 會額外帶 `strategy_param_scan`，明確告訴 operator 目前可參考的 scan-backed strategy candidates。
- **驗證完成**：
  - `python -m pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_rescan_models_and_refresh_strategy_leaderboard.py -q` → `68 passed`
  - `python -m py_compile server/routes/api.py backtesting/model_leaderboard.py scripts/rescan_models_and_refresh_strategy_leaderboard.py` → PASS
  - `python scripts/rescan_models_and_refresh_strategy_leaderboard.py --top-per-model 1` → PASS
  - `python scripts/hb_model_leaderboard_api_probe.py` → PASS（cache stable, placeholder warning retained）

---

## 主目標

### 目標 A：用 live predictor truth 收斂 q15 current-live closure
**目前真相**
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q15`
- `support_route_verdict=exact_bucket_supported`
- `current_live_structure_bucket_rows=96 / 50`
- 但 top-level live baseline 仍是 `entry_quality=0.3385 / D / allowed_layers=0 / should_trade=false`

**成功標準**
- 要嘛 live predictor 本身跨過 trade floor，變成真正可部署；
- 要嘛所有 surface 一律明確呈現 `support closed but live baseline still below floor`，不再混淆成 patch-ready / venue-ready / deploy-ready。

### 目標 B：把 canonical model leaderboard 從 placeholder-only 推進到 usable comparable ranking
**目前真相**
- canonical leaderboard 仍是 `count=0 / placeholder_count=6`
- 但 `strategy_param_scan` 與 strategy leaderboard 已經提供 6 條 scan-backed deployable candidates
- 目前 scan 顯示有效參數普遍落在：
  - `bias50_max ≈ 3.0`
  - `stop_loss ≈ -0.05`
  - `turning_point.bottom_score_min ≈ 0.56~0.62`

**成功標準**
- 把上述有效參數回灌到 canonical leaderboard 的 deployment profiles / evaluation path，至少產生 `comparable_count > 0`；
- 若短期內仍無 comparable rows，則 Strategy Lab / operator UX 必須直接顯示 `strategy_param_scan` advisory，而不是只留下空榜。

### 目標 C：維持產品化排行榜同步
**目前真相**
- `Auto Leaderboard · ...` 已改為由最新 scan artifact 驅動
- rule_baseline 落盤 bug 已修掉
- stale auto candidates 已清除

**成功標準**
- 每次 scan 都能 deterministically 清掉舊 auto candidates、重建新候選、同步到 `/api/strategies/leaderboard`。

---

## 下一步
1. **把 scan winner 參數回灌到 canonical model leaderboard deployment profiles**
   - 驗證：`python scripts/hb_model_leaderboard_api_probe.py` 或 `/api/models/leaderboard` 出現 `comparable_count > 0`
2. **把 `strategy_param_scan` advisory 接到 Strategy Lab / operator UI**
   - 驗證：前端 surface 能在 placeholder-only 時直接顯示 scan-backed candidates，而不是只顯示空榜 warning
3. **持續以 live probe truth 收斂 q15 current-live semantics**
   - 驗證：`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`/execution/status`

---

## 成功標準
- q15 current-live truth 與 operator surface 完全一致：support closure 不再被誤讀為 deployment closure
- canonical model leaderboard 要嘛出現至少 1 條 comparable row，要嘛 placeholder-only UX 已完整產品化
- strategy leaderboard 持續反映最新 scan artifact，而不是舊的 stale auto candidates
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
