# ROADMAP.md — Current Plan Only

_最後更新：2026-04-23 12:55:30 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **heartbeat #20260423j：operator-facing blocker truth humanization completed**
  - `/`、`/execution`、`/execution/status`、`/lab` 的主 blocker / routing / runtime closure 摘要已接上共用 humanizer
  - toxic q15 bucket 主 blocker 不再在主卡片漏出 raw machine token（`exact_live_lane_toxic_sub_bucket_current_bucket` / `toxic sub-bucket` / `regime gate` / `blocks trade`）
  - 驗證：`pytest tests/test_frontend_decision_contract.py tests/test_execution_surface_contract.py tests/test_strategy_lab.py -q` → `123 passed`
  - 驗證：`cd web && npm run build` → pass
  - 驗證：browser `/`、`/execution/status`、`/lab` 主 blocker 區塊無 JS error，operator copy 與 live runtime truth 對齊
- **資料 / 覆蓋基線沿用 fast heartbeat #20260423i**
  - `Raw=32031 / Features=23449 / Labels=64018`
  - `2y_backfill_ok=True` / `simulated_pyramid_win=57.03%`
- **latest current-live truth 已確認**
  - `deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket`
  - `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=199/50` / `gap=0`
  - `runtime_closure_state=deployment_guardrail_blocks_trade` / `entry_quality=0.4266` / `allowed_layers=0`

---

## 主目標

### 目標 A：維持 toxic q15 bucket 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket`
- `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=199/50` / `gap=0` / `support_route_verdict=exact_bucket_supported`
**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都把 toxic q15 bucket 視為唯一 current-live blocker
- support closure 仍可 machine-read，但不會被誤包裝成 deployment closure

### 目標 B：繼續鑽 recent canonical 1000-row blocker pocket
**目前真相**
- `latest_window=100` / `win_rate=97.0%` / `dominant_regime=bull(91.0%)` / `avg_quality=+0.6707` / `avg_pnl=+0.0224`
- `blocking_window=1000` / `win_rate=41.7%` / `dominant_regime=bull(80.4%)` / `avg_quality=+0.1189` / `avg_pnl=+0.0030`
**成功標準**
- drift / probe / docs 能同時指出 1000-row bull concentration pocket 與當前 toxic q15 bucket 根因，而不是退回 generic 摘要

### 目標 C：守住 reference-only patch 與 leaderboard dual-role governance
**目前真相**
- `recommended_patch=core_plus_macro_plus_all_4h` / `status=reference_only_non_current_live_scope` / `reference_patch_scope=bull|CAUTION`
- `leaderboard_count=6` / `top_model=rule_baseline` / `selected_feature_profile=core_only` / `support_aware_profile=core_plus_macro_plus_all_4h`
**成功標準**
- patch 在所有 surface 都維持 reference-only 語義
- leaderboard / Strategy Lab / docs 不回退 placeholder-only，也不把 dual-role governance 誤判成 parity blocker

### 目標 D：維持 venue/source blockers 與 docs automation current-state sync
**目前真相**
- `fin_netflow=source_auth_blocked` / `archive_window_coverage_pct=0.0`
- `binance=public-only metadata OK` / `okx=disabled public-only metadata OK`
- current-state docs 必須保持 overwrite sync，不保留失效歷史流水帳
**成功標準**
- venue/source blockers 持續可見
- docs 與 `issues.json` / live artifacts 對齊，不再讓 markdown drift

---

## 下一輪 gate
1. **沿 toxic q15 bucket 的 component counterfactual 繼續追根因**
   - 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`data/q15_bucket_root_cause.json`
   - 升級 blocker：若 toxic q15 bucket 再被 generic blocker copy 覆蓋，或 exact support truth 從 top-level surface 消失
2. **沿 recent canonical 1000-row bull concentration pocket 繼續 drill-down**
   - 驗證：`python scripts/recent_drift_report.py`、browser `/`
   - 升級 blocker：若 1000-row blocker pocket 的 top-shift / adverse-streak 證據再次失真或消失
3. **守住 reference-only patch、venue/source blockers、leaderboard governance 與 docs overwrite sync**
   - 驗證：browser `/lab`、browser `/execution/status`、`curl http://127.0.0.1:8000/api/status`、`data/execution_metadata_smoke.json`
   - 升級 blocker：若 patch 被誤升級成 deployable truth、venue/source blocker 消失、或 docs 再次落後 live artifacts

---

## 成功標準
- current-live blocker 清楚且唯一：**exact_live_lane_toxic_sub_bucket_current_bucket**
- current live q15 truth 維持：**199/50 + exact_bucket_supported + deployment_guardrail_blocks_trade**
- recent canonical 1000-row blocker pocket 維持可 machine-read：**41.7% / bull 80.4% / avg_quality 0.1189**
- operator-facing blocker truth 在 Dashboard / Execution / Strategy Lab 維持中文產品語義，不回退 raw machine tokens
- heartbeat 每輪都完成：**issue 對齊 → patch → verify → docs overwrite sync → commit → push / blocker 記錄**
