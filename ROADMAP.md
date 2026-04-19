# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 16:24 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast collect + direct probe refresh 成功**：`Raw=31111 (+2) / Features=22529 (+2) / Labels=62632 (+8)`；`240m / 1440m` freshness 仍屬 expected horizon lag，資料管線不是 frozen。
- **本輪產品化 patch：canonical model leaderboard 改用 recent-window 評估，不再卡在 placeholder-only**
  - `backtesting/model_leaderboard.py` 新增 `EVALUATION_MAX_FOLDS=4` 與 `latest_bounded_walk_forward` 選窗，leaderboard 評估不再只看最早期 fold，而是固定使用最新 4 個 bounded walk-forward windows。
  - `server/routes/api.py` 將 `evaluation_fold_window` / `evaluation_max_folds` 序列化到 `/api/models/leaderboard`，讓 API / UI / probe 可以 machine-read 目前排行榜用的是哪個評估視窗。
  - `tests/test_model_leaderboard.py` 新增 regression，鎖住「leaderboard 必須偏向最新 bounded walk-forward folds」的 contract。
- **本輪產品化 patch：Strategy Lab 明示排行榜回測用最近兩年，並把預設區間對齊這個產品語義**
  - `server/routes/api.py` 新增 `_resolve_default_strategy_backtest_range()`，當使用者沒明確指定區間時，策略回測預設落在最近 730 天而不是任意全歷史。
  - `web/src/pages/StrategyLab.tsx` 現在固定顯示「排行榜回測固定使用最近兩年」，並在資料可用時自動帶入最新兩年區間。
  - `tests/test_strategy_lab.py` 新增 regression，鎖住 default backtest range 與 explicit range preserving contract。
- **本輪產品化 patch：Web UI shell / surface classes 統一**
  - `web/src/App.tsx`、`web/src/index.css`、`Dashboard / StrategyLab / ExecutionConsole / ExecutionStatus / Senses` 與多個 summary components 已切到同一組 `app-shell / app-page-shell / app-page-header / app-surface-card` 設計語義。
  - `tests/test_frontend_decision_contract.py` 新增 regression，鎖住統一 shell 與 Strategy Lab 兩年回測政策文案。
- **canonical model leaderboard 已恢復可比較 rows**
  - browser `fetch('/api/models/leaderboard')` 驗證：`count=6`、`comparable_count=6`、`placeholder_count=0`、`evaluation_fold_window=latest_bounded_walk_forward`、`evaluation_max_folds=4`。
  - browser `/lab` 已顯示 6 筆真實模型排行，不再是 placeholder-only 空榜；同頁也可看到 current live blocker、venue blockers、live lane vs spillover patch 卡與兩年回測政策。
- **runtime truth 維持 breaker-first**
  - `python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/hb_q15_support_audit.py` 已刷新 current-live artifacts。
  - browser `/execution/status` 驗證：`deployment_blocker=circuit_breaker_active`、`streak=264`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`support=0/50`、venue blockers 仍可見。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=264`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`

**成功標準**
- `/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 q15 `0/50` 與 reference-only patch 的分離真相
**目前真相**
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
- `live_current_structure_bucket_rows=0 / minimum_support_rows=50`
- `gap_to_minimum=50`
- `support_route_verdict=exact_bucket_missing_exact_lane_proxy_only`
- `remaining_gap_to_floor=0.1376`
- `best_single_component=feat_4h_bias50`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`
- `spillover_regime_gate=bull|CAUTION`

**成功標準**
- probe / drilldown / Strategy Lab / docs / `issues.json` 都一致承認：`0/50 + exact_bucket_missing_exact_lane_proxy_only + stalled_under_minimum + reference_only_until_exact_support_ready`。
- `bull|CAUTION` spillover 與 q15 current-live truth 不能再混成 deployable advice。

### 目標 C：把 recent canonical 250-row pathology 當成 breaker 根因持續鑽深
**目前真相**
- `recent_window=250`
- `win_rate=0.0000`
- `dominant_regime=bull(100%)`
- `avg_pnl=-0.0103`
- `avg_quality=-0.2862`
- `tail_streak=250x0`
- top shifts：`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`

**成功標準**
- recent drift / live probe / docs 能直接指出 pathological slice 與 feature shifts；
- 不再把 current blocker 稀釋成 generic leaderboard / venue 討論。

### 目標 D：守住已恢復的 canonical leaderboard comparable rows 與 Strategy Lab 兩年回測 contract
**目前真相**
- `/api/models/leaderboard`：`count=6`、`comparable_count=6`、`placeholder_count=0`
- `evaluation_fold_window=latest_bounded_walk_forward`
- `evaluation_max_folds=4`
- Strategy Lab 已明示：`排行榜回測固定使用最近兩年`
- browser `/lab` 可直接看到真實 model leaderboard rows，不再依賴 placeholder fallback

**成功標準**
- `/api/models/leaderboard` 維持 comparable rows；
- Strategy Lab 工作區與模型排行維持最近兩年 policy，不再回退成 placeholder-only 或短窗假樂觀；
- regression tests 與 build 長期守住這個 contract。

### 目標 E：把 venue / source blockers 維持在可見但不搶 breaker 主線的位置
**目前真相**
- `binance=config enabled + public-only + metadata OK`
- `okx=config disabled + public-only + metadata OK`
- `fin_netflow=source_auth_blocked`
- `COINGLASS_API_KEY` 缺失

**成功標準**
- `/execution`、`/execution/status`、`/lab`、`ISSUES.md`、`issues.json` 都保留 venue blockers 與 source auth blockers，但它們永遠排在 breaker-first current blocker 之後。

---

## 下一輪 gate
1. **維持 breaker-first truth across `/execution` / `/execution/status` / `/lab` / probe / drilldown**
   - 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若任何 surface 再把 q15 / venue / spillover 排到 breaker 前面，或遺失 `additional_recent_window_wins_needed=15`
2. **鎖住 q15 `0/50` + reference-only `core_plus_macro` patch visibility**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`
   - 升級 blocker：若 `recommended_patch` 消失、被升級成 deployable、或 `support_route_verdict` / `support_progress` / `gap_to_minimum` 再次失真
3. **守住 canonical leaderboard comparable rows 與 Strategy Lab 兩年回測 contract，並把重算保持在 cron 可承受範圍內**
   - 驗證：browser `fetch('/api/models/leaderboard')`、browser `/lab`、`pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`
   - 升級 blocker：若 leaderboard 再回到 placeholder-only、丟失 `evaluation_fold_window=latest_bounded_walk_forward`、或 Strategy Lab 回退成模糊區間 / 短窗預設

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + exact_bucket_missing_exact_lane_proxy_only + stalled_under_minimum + reference_only_until_exact_support_ready` 在 probe / API / UI / docs / issues 全部 machine-read 一致
- recent canonical 250 rows pathology 仍被明確當成 breaker 根因，而不是被 leaderboard / venue 討論稀釋
- canonical leaderboard 維持：**6 筆 comparable rows、latest_bounded_walk_forward、Strategy Lab 兩年回測 policy 可見**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
