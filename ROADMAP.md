# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 13:57 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat + collect 成功**：`Raw=31102 (+1) / Features=22520 (+1) / Labels=62610 (+9)`；`240m / 1440m` freshness 仍屬 expected horizon lag，資料管線不是 frozen。
- **本輪產品化 patch：恢復 non-bull live row 的 artifact-backed patch visibility**
  - `server/live_pathology_summary.py` 現在在 current live 不是 bull、但 wider scope spillover 已落到 `bull|BLOCK` 時，仍會保留 `bull_4h_pocket_ablation.bull_collapse_q35` 的 `recommended_patch`，並明確標成 `reference_only_until_exact_support_ready`。
  - `data/live_predict_probe.json` 與 `data/live_decision_quality_drilldown.json` 已重新輸出 `recommended_patch={recommended_profile=core_plus_macro, spillover_regime_gate=bull|BLOCK, reference_patch_scope=bull|CAUTION, reference_source=bull_4h_pocket_ablation.bull_collapse_q35}`。
- **回歸測試已補齊**
  - `tests/test_live_pathology_summary.py` 新增 non-bull live row regression，鎖住 `recommended_patch` 不得再掉成 `null`。
  - `tests/test_hb_predict_probe.py` 新增 end-to-end probe regression，鎖住 `hb_predict_probe.py` 仍須輸出 reference-only patch summary。
- **驗證完成**
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_live_pathology_summary.py tests/test_hb_predict_probe.py -q` → `20 passed`
  - `source venv/bin/activate && PYTHONPATH=. pytest tests/test_frontend_decision_contract.py -q` → `16 passed`
  - `cd web && npm run build` → 通過
  - browser `http://127.0.0.1:5173/lab`：顯示 `current live blocker=circuit_breaker_active`、venue blockers、`bull|BLOCK` spillover，以及 `core_plus_macro` reference-only patch 卡；console 無 JS exception。
- **current-state docs / tracker 已同步**：`issues.json`、`ISSUES.md`、`ROADMAP.md` 已覆蓋成最新 truth。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=0/50`
- `additional_recent_window_wins_needed=15`
- `streak=256`
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
- `avg_pnl=-0.0104`
- `avg_quality=-0.2843`
- top shifts：`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_4h_rsi14`
- venue blockers 與 `fin_netflow auth_missing` 仍是 secondary readiness truth，不可覆蓋主病灶

**成功標準**
- recent drift / live probe / docs 能直接指出 pathological slice 與 feature shifts；
- 不再把 current blocker 退化成 generic model parity 或單純 leaderboard 討論。

---

## 下一輪 gate
1. **維持 breaker-first truth across `/execution` / `/execution/status` / `/lab` / probe / drilldown**
   - 驗證：browser `/execution`、browser `/execution/status`、browser `/lab`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若任何 surface 再把 q15 / venue / spillover 排到 breaker 前面，或遺失 `additional_recent_window_wins_needed=15`
2. **鎖住 q15 `0/50` + reference-only `core_plus_macro` patch visibility**
   - 驗證：`python scripts/hb_q15_support_audit.py`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/lab`、`pytest tests/test_live_pathology_summary.py tests/test_hb_predict_probe.py -q`
   - 升級 blocker：若 `recommended_patch` 再次消失、被升級成 deployable、或 `bull|BLOCK` spillover / `bull|CAUTION` reference scope 分離失真
3. **持續追 recent canonical 250-row distribution pathology root cause**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`、current-state docs 必須明記 top feature shifts 與 target streak
   - 升級 blocker：若 heartbeat 又回到 generic parity 報告，或 venue/auth 問題掩蓋了 current pathological slice

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `q15 support 0/50 + exact_bucket_missing_exact_lane_proxy_only + stalled_under_minimum + reference_only_until_exact_support_ready` 在 probe / API / UI / docs / issues 全部 machine-read 一致
- non-bull live row 時，`bull|BLOCK` spillover 仍可看到 `bull|CAUTION` artifact-backed reference patch，但不會被誤包裝成 current-live deployable advice
- `/lab` 同時保留：**breaker-first truth 清楚、venue blockers 可見、exact-vs-spillover 對照可見、reference-only patch card 可見、runtime console 無 JS exception**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
