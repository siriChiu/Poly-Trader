# ROADMAP.md — Current Plan Only

_最後更新：2026-04-20 00:06:40 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat 本輪完成 collect + verify 閉環**
  - `python scripts/hb_parallel_runner.py --fast`
  - `Raw=31149 / Features=22567 / Labels=62712`
  - collect 實際新增 `+1 raw / +2 features / +21 labels`
  - `Global IC=13/30`、`TW-IC=26/30`
- **current-live breaker / q35 truth 已重新量測**
  - `deployment_blocker=circuit_breaker_active`
  - `recent 50 wins=1/50`
  - `additional_recent_window_wins_needed=14`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
  - `current_live_structure_bucket_rows=1 / minimum_support_rows=50 / gap_to_minimum=49`
  - `recommended_patch=core_plus_macro_plus_all_4h`
  - `recommended_patch_status=reference_only_until_exact_support_ready`
- **本輪產品化 patch：execution surfaces 的初次載入改成 loading truth，而不是假 unavailable**
  - `Dashboard.tsx`、`ExecutionConsole.tsx`、`ExecutionStatus.tsx`、`StrategyLab.tsx` 現在在第一次 `/api/status` 尚未返回時，會顯示 `同步中 / 正在同步 /api/status`。
  - 初次進頁時不再把 `current live blocker / metadata freshness / reconciliation` 誤渲染成 `unavailable / none / unknown`。
  - 這個 patch 直接提升 operator 對 breaker-first truth 的信任度：短暫 loading 不再被誤讀成 current state。
- **recent pathological slice 與 leaderboard current truth 已確認**
  - recent canonical `250` rows：`win_rate=0.0040`、`dominant_regime=bull(100%)`、`avg_quality=-0.2724`
  - leaderboard：`count=6 / comparable_count=6 / top=rule_baseline / core_only / scan_backed_best`
- **本輪驗證已補齊**
  - `pytest tests/test_frontend_decision_contract.py -q` → `19 passed`
  - `cd web && npm run build` → pass
  - browser 首屏 `/`、`/execution/status`、`/lab`：已看到 `同步中` loading copy，而不是 `unavailable / none / unknown`
  - `curl http://127.0.0.1:8000/api/status`：breaker-first truth、q35 `1/50` support、reference-only patch、venue blockers 都存在
- **current-state 文件覆寫已完成**
  - `ISSUES.md` / `ROADMAP.md` / `ORID_DECISIONS.md` 已覆寫為本輪 current state
  - `ARCHITECTURE.md` 已加入 initial-sync loading contract

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=1/50`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=14`
- `streak=30`
- `allowed_layers=0`

**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、docs 全部一致把 breaker 視為唯一 current-live deployment blocker。
- 在第一次 `/api/status` 尚未返回前，也只能顯示 `同步中`，不能回退成 `unavailable / none / unknown`。

### 目標 B：維持 q35 `1/50` 與 reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=1 / minimum_support_rows=50`
- `gap_to_minimum=49`
- `support_route_verdict=exact_bucket_present_but_below_minimum`
- `recommended_patch=core_plus_macro_plus_all_4h`
- `recommended_patch_status=reference_only_until_exact_support_ready`

**成功標準**
- probe / drilldown / `/` / `/execution/status` / `/lab` / docs / `issues.json` 都一致承認：`1/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready`。

### 目標 C：把 recent canonical 250-row pathology 當成 breaker 根因持續鑽深
**目前真相**
- `recent_window=250`
- `win_rate=0.0040`
- `dominant_regime=bull(100%)`
- `avg_pnl=-0.0091`
- `avg_quality=-0.2724`
- top shifts=`feat_eye`、`feat_local_top_score`、`feat_rsi14`
- new compressed=`feat_vwap_dev`

**成功標準**
- drift / live probe / docs 能直接指出 pathological slice、adverse streak、top feature shifts；
- blocker 不再被 generic leaderboard / venue 討論稀釋。

### 目標 D：守住 venue / source blockers 的產品語義同步
**目前真相**
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 未驗證
- `fin_netflow=source_auth_blocked`
- `COINGLASS_API_KEY` 仍缺失

**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、docs 對 venue blockers 與 source auth blocker 說同一個真相，且永遠排在 breaker-first current blocker 之後。

---

## 下一輪 gate
1. **維持 breaker-first truth + initial-sync loading contract across UI / probe / docs**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若任一 surface 再把 loading state 誤顯示成 `unavailable / none / unknown`，或把 patch / venue 排到 breaker 前面
2. **持續鑽 recent canonical 250-row pathology，而不是 generic 化 blocker**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 target-path / adverse-streak / top-shift 證據，或 docs 又退回 generic leaderboard / venue 敘事
3. **守住 q35 reference-only patch 與 venue/source blockers 的可見性**
   - 驗證：browser `/`、browser `/execution/status`、browser `/lab`、`data/bull_4h_pocket_ablation.json`、`data/execution_metadata_smoke.json`
   - 升級 blocker：若 q35 patch 被誤升級成 deployable truth，或 venue / CoinGlass blocker 在 current-state surfaces 消失

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- 初次進入 `/`、`/execution`、`/execution/status`、`/lab` 時，execution/loading 區塊先顯示 **同步中**，而不是 `unavailable / none / unknown`
- `current live q35 = 1/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready` 在 probe / drilldown / API / UI / docs 全部 machine-read 一致
- recent canonical pathology 仍以同一個 250-row slice 為主敘事，不被 generic 問題稀釋
- venue blockers 與 CoinGlass auth blocker 在 operator-facing surfaces 持續可見
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
