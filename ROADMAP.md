# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 22:18:37 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **本輪產品化 patch：leaderboard current-live signature priority 已落地**
  - `scripts/hb_parallel_runner.py::_current_leaderboard_candidate_semantic_signature()` 現在優先讀 `data/live_predict_probe.json` 的 current-live bucket / rows / support governance truth。
  - 這修掉了 stale `bull_4h_pocket_ablation.json` live_context 把實際 bull/q35 truth 誤判成 cache mismatch 的 cron-safe bug。
- **本輪產品化 patch：stale bull pocket timeout fallback 已改成 reference-only**
  - `collect_bull_4h_pocket_diagnostics()` 現在會在 live signature mismatch 時回傳 `reference_only_stale_live_context`，保留 `bull_all / bull_collapse_q35`，但不再把 stale q15/chop live-specific proxy cohorts 當成 current q35 truth。
- **本輪 fast heartbeat 已完成且留下新鮮 artifacts**
  - `python scripts/hb_parallel_runner.py --fast` 完成：`Raw=31144 / Features=22562 / Labels=62676`。
  - `Global IC=13/30`、`TW-IC=27/30`。
  - current live truth：`deployment_blocker=circuit_breaker_active`、`current_live_structure_bucket=CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_rows=1/50`、`support_route_verdict=exact_bucket_present_but_below_minimum`。
- **本輪驗證已補齊**
  - `pytest tests/test_hb_parallel_runner.py::test_current_leaderboard_candidate_semantic_signature_prefers_live_probe_bucket_over_stale_bull_artifact tests/test_hb_parallel_runner.py::test_collect_bull_4h_pocket_diagnostics_marks_semantic_mismatch_reference_only tests/test_hb_parallel_runner.py::test_collect_bull_4h_pocket_diagnostics_reads_live_bucket_support tests/test_hb_parallel_runner.py::test_leaderboard_candidate_cache_hit_uses_semantic_alignment_signature -q` → `4 passed`
  - browser `/lab`：breaker-first truth、q35 `1/50` support、reference-only patch、venue blockers 全部可見
  - browser `/execution/status`：`circuit_breaker_active`、`support 1/50`、`bull/q35`、venue blockers 全部可見
- **本輪 current-state 文件覆寫已完成**
  - `ISSUES.md` / `ROADMAP.md` / `ORID_DECISIONS.md` 已覆寫成 heartbeat #fast 的 current-state-only truth。
  - `ARCHITECTURE.md` 已補上 `current-live signature priority` 與 `stale-bull-artifact fallback` contract。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live blocker
**目前真相**
- `deployment_blocker=circuit_breaker_active`
- `recent 50 wins=1/50`
- `additional_recent_window_wins_needed=14`
- `streak=3`
- `allowed_layers=0`
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`

**成功標準**
- `/`、`/execution/status`、`/lab`、`hb_predict_probe.py`、`live_decision_quality_drilldown.py`、`issues.json`、`ISSUES.md` 全部一致把 breaker 視為唯一 current-live deployment blocker。

### 目標 B：維持 q35 `1/50` 與 reference-only patch 真相
**目前真相**
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=1 / minimum_support_rows=50`
- `gap_to_minimum=49`
- `support_route_verdict=exact_bucket_present_but_below_minimum`
- `recommended_patch=core_plus_macro`
- `recommended_patch_status=reference_only_until_exact_support_ready`

**成功標準**
- probe / drilldown / `/lab` / `/execution/status` / docs / `issues.json` / heartbeat summary 都一致承認：`1/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready`。

### 目標 C：把 recent canonical 250-row pathology 當成 breaker 根因持續鑽深
**目前真相**
- `recent_window=250`
- `win_rate=0.0040`
- `dominant_regime=bull(100%)`
- `avg_pnl=-0.0099`
- `avg_quality=-0.2813`
- `adverse_streak=246x0`
- top shifts=`feat_4h_bb_pct_b`、`feat_4h_bias20`、`feat_eye`
- new compressed=`feat_vwap_dev`

**成功標準**
- drift / live probe / docs 能直接指出 pathological slice 與 top feature shifts；
- 不再把 current blocker 稀釋成 generic leaderboard / venue 討論。

### 目標 D：讓 bull pocket fast path 變成 cron-safe current-truth lane
**目前真相**
- `bull_4h_pocket_ablation.py` 仍會在 fast mode 20s budget timeout
- 但 stale live-specific cohorts 已不再污染 current q35 truth
- 當前 fallback 語義：`reference_only_stale_live_context`

**成功標準**
- fast heartbeat 中 bull pocket 要嘛在 budget 內完成 current-bucket rebuild，要嘛提供更便宜的 current-bucket refresh lane；
- 在任何 timeout 情況下，都不得再把 stale q15/chop live-specific cohorts 說成 current bull/q35 runtime truth。

### 目標 E：守住 leaderboard / venue / source blocker 的產品語義同步
**目前真相**
- leaderboard：`count=6 / comparable_count=6 / top=rule_baseline / core_only / scan_backed_best`
- venue blockers：`live exchange credential / order ack lifecycle / fill lifecycle` 仍未驗證
- `fin_netflow=source_auth_blocked`

**成功標準**
- `/lab`、`/execution/status`、probe、`issues.json`、docs 對 leaderboard top row、current blocker、venue blockers、source auth blockers 說同一個真相。

---

## 下一輪 gate
1. **維持 breaker-first truth + q35 `1/50` support truth across UI / probe / docs**
   - 驗證：browser `/lab`、browser `/execution/status`、`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`
   - 升級 blocker：若任一 surface 再把 q35 `1/50` 說成 support 已 closure，或把 patch / venue 排到 breaker 前面
2. **讓 bull pocket fast path 不再只靠 reference-only timeout fallback**
   - 驗證：`python scripts/hb_parallel_runner.py --fast`，觀察 `bull_4h_pocket_ablation` 是否 `rc=0` 或有明確 current-bucket refresh lane；`data/heartbeat_fast_summary.json`
   - 升級 blocker：若 bull pocket 再次 timeout 且 current live truth 被 stale artifact 污染
3. **持續鑽 recent canonical 250-row pathology，而不是 generic 化 blocker**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`
   - 升級 blocker：若 drift artifact 再失去 top shifts / adverse streak / target-path evidence，或 docs 又退回只寫 generic leaderboard / venue 問題

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- `/lab` 與 `/execution/status` 都先顯示 `deployment_blocker=circuit_breaker_active`，再顯示 venue blockers
- `current live q35 = 1/50 + exact_bucket_present_but_below_minimum + reference_only_until_exact_support_ready` 在 probe / drilldown / API / UI / docs / summary 全部 machine-read 一致
- bull pocket timeout fallback 即使存在，也只會降級成 **reference-only**，不再把 stale q15/chop live-specific cohorts 說成 current bull/q35 truth
- canonical leaderboard 維持：**6 筆 comparable rows、top row = `rule_baseline / core_only / scan_backed_best`**
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
