# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 14:52 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat + collect 成功**：`Raw=31104 (+1) / Features=22522 (+1) / Labels=62619 (+2)`；`240m / 1440m` freshness 仍屬 expected horizon lag，資料管線不是 frozen。
- **本輪產品化 patch：鎖住 Strategy Lab Gate 摘要 contract**
  - `server/routes/api.py` 的 `_compute_decision_profile()` 現在固定輸出 `regime_gate_summary={ALLOW,CAUTION,BLOCK}`，不再只回傳 dominant gate。
  - `_decorate_strategy_entry()` 現在會在 legacy strategy `last_results` 已有完整 trade log 時，自動回填 `regime_gate_summary`，避免工作區卡片掉回 `0/0/0` 假空白。
  - `ARCHITECTURE.md` 已同步更新 backtest / Strategy Lab contract；`README.md` 的 q15 support 事實也已校正回 `0/50`。
- **auto strategy workspace UX 已維持可用**
  - `python scripts/rescan_models_and_refresh_strategy_leaderboard.py --top-per-model 1` 產生的 6 筆 auto strategies 仍可在 Strategy Lab workspace 正常載入。
  - browser `/lab` 已驗證 `catboost` 顯示 `ALLOW 0 / CAUTION 39 / BLOCK 0`，不再是全零 Gate 摘要。
- **驗證完成**
  - `source venv/bin/activate && PYTHONPATH=. python scripts/hb_parallel_runner.py --fast --hb 20260419w`
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_strategy_lab.py tests/test_api_feature_history_and_predictor.py -q` → `105 passed`
  - `cd web && npm run build` → success
  - browser `http://127.0.0.1:5174/lab`：auto strategy workspace 已載入、Gate 摘要非零、console 無 JS exception
  - browser `http://127.0.0.1:5174/execution/status`：breaker-first blocker truth、q15 `0/50`、venue blockers 均可見
- **current-state docs / tracker 已同步**：`issues.json`、`ISSUES.md`、`ROADMAP.md`、`ARCHITECTURE.md`、`README.md` 已覆蓋成最新 truth。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=261`
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
- wider spillover：`bull|BLOCK` 199 rows
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`
- `reference_patch_scope=bull|CAUTION`

**成功標準**
- probe / drilldown / Strategy Lab / docs / `issues.json` 都一致承認：`0/50 + exact_bucket_missing_exact_lane_proxy_only + stalled_under_minimum + reference_only_until_exact_support_ready`；
- `bull|BLOCK` spillover 與 `bull|CAUTION` reference patch scope 不能再混成 current-live deployable advice。

### 目標 C：把 recent canonical 250-row pathology 當成 breaker 根因持續鑽深
**目前真相**
- `recent_window=250`
- `win_rate=0.0000`
- `dominant_regime=bull(100%)`
- `avg_pnl=-0.0103`
- `avg_quality=-0.2854`
- `tail_streak=250x0`
- top shifts：`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`

**成功標準**
- recent drift / live probe / docs 能直接指出 pathological slice 與 feature shifts；
- 不再把 current blocker 退化成 generic model parity 或單純 leaderboard 討論。

### 目標 D：把 canonical model leaderboard 從 placeholder-only 推向 comparable rows，但不回退 Strategy Lab UX
**目前真相**
- canonical model leaderboard：`leaderboard_count=0`、`comparable_count=0`、`placeholder_count=4`
- Strategy Lab workspace：**已修復**，browser `/lab` 可載入真實 auto strategy 並顯示非零 Gate 摘要
- governance split：`global_profile=core_only`、`train_selected_profile=core_plus_macro`、`governance_contract=dual_role_governance_active`

**成功標準**
- canonical model leaderboard 產生可比較列，placeholder warning 只在真的 no-trade 時出現；
- `/lab` workspace 保持目前已修復的非零 Gate 摘要與可載入 auto candidates，不可回退成 `ALLOW/CAUTION/BLOCK = 0/0/0`。

---

## 下一輪 gate
1. **維持 breaker-first truth across `/execution` / `/execution/status` / `/lab` / probe / drilldown**
   - 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若任何 surface 再把 q15 / venue / spillover 排到 breaker 前面，或遺失 `additional_recent_window_wins_needed=15`
2. **鎖住 q15 `0/50` + reference-only `core_plus_macro` patch visibility**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`
   - 升級 blocker：若 `recommended_patch` 再次消失、被升級成 deployable、或 `bull|BLOCK` spillover / `bull|CAUTION` reference scope 分離失真
3. **把 canonical model leaderboard 從 placeholder-only 往 comparable rows 推進，同時守住已修好的 Strategy Lab Gate 摘要 UX**
   - 驗證：`python scripts/hb_leaderboard_candidate_probe.py`、browser `/lab`、`pytest tests/test_strategy_lab.py tests/test_api_feature_history_and_predictor.py -q`
   - 升級 blocker：若 canonical leaderboard 仍無 comparable rows且 Strategy Lab surface 再回退成 Gate 摘要全零或無法載入 auto candidate

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + exact_bucket_missing_exact_lane_proxy_only + stalled_under_minimum + reference_only_until_exact_support_ready` 在 probe / API / UI / docs / issues 全部 machine-read 一致
- recent canonical 250 rows pathology 仍被明確當成 breaker 根因，而不是被 broader model / venue 討論稀釋
- Strategy Lab workspace 保持：**auto strategy 可載入、Gate 摘要非零、Live blocker / venue blockers / patch visibility 正常、console 無 JS exception**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
