# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-19 21:40:43 CST_

---

## 心跳 #20260419aj ORID

### O｜客觀事實
- `python scripts/hb_parallel_runner.py --fast --hb 20260419aj` 完成 collect + verify 閉環：`Raw 31141→31142 / Features 22559→22560 / Labels 62668→62671`。
- `python scripts/hb_predict_probe.py` 與 `python scripts/live_decision_quality_drilldown.py` 現在一致顯示：
  - `deployment_blocker=circuit_breaker_active`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
  - `current_live_structure_bucket_rows=1`
  - `minimum_support_rows=50`
  - `support_route_verdict=exact_bucket_present_but_below_minimum`
  - `recommended_patch=core_plus_macro`
  - `recommended_patch_status=reference_only_until_exact_support_ready`
- 本輪 patch：`model/predictor.py::_summarize_structure_bucket_support_route()` 改成 **rows-aware**；under-minimum exact bucket 不再因 `exact_bucket_supported_*` mode hint 被誤報成 support closure。
- 回歸驗證：`pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py -q` → `80 passed`。
- 近期漂移仍是 canonical 250-row pathology：`win_rate=0.0040`、`dominant_regime=bull(100%)`、`avg_quality=-0.2816`、`adverse_streak=248x0`。
- leaderboard 仍穩定：`count=6 / comparable_count=6 / top=rule_baseline / core_only / scan_backed_best / latest_persisted_snapshot`。

### R｜感受直覺
- 這一輪最大的產品風險不是新的 IC 數字，而是 **support-route 語義假性放行**：只要 `1/50` 也能被說成 `exact_bucket_supported`，operator 就會把 reference-only patch 誤讀成 runtime 已可部署。
- breaker 仍是唯一 current-live blocker；但 breaker 下的 support truth 必須保持可見，不能因為被 breaker 擋住就退回舊的 stale support 敘事。

### I｜意義洞察
1. **exact-support closure 是 rows contract，不是 mode-hint contract**：`exact_bucket_supported_*` 只是語義來源，真正 closure 要看 `current_live_structure_bucket_rows >= minimum_support_rows`。
2. **probe / drilldown / docs 必須以數值 truth 為主**：當 current live bucket 只有 `1/50` 時，就算 q35 redesign / fallback lane 還在，也只能是 `present_but_below_minimum` + `reference-only`。
3. **這個修正直接提升產品可信度**：它防止 Strategy Lab、Execution 狀態與 current-state 文件把 under-minimum live bucket 說成已 closure，讓 operator 決策不再被 false-open support wording 誤導。

### D｜決策行動
- **Owner**：AI Agent / heartbeat current-state governance path
- **Action**：維持 rows-aware support-route truth，並把 q35 `1/50` 與 reference-only `core_plus_macro` patch 固定成 probe / drilldown / docs / summary 的一致 machine-read。
- **Artifact**：`model/predictor.py`、`tests/test_api_feature_history_and_predictor.py`、`data/live_predict_probe.json`、`data/live_decision_quality_drilldown.json`、`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`
- **Verify**：
  - `pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py -q`
  - `python scripts/hb_parallel_runner.py --fast --hb 20260419aj`
  - `python scripts/hb_predict_probe.py`
  - `python scripts/live_decision_quality_drilldown.py`
- **If fail**：若任一 surface 再把 `1/50` current live bucket 說成 `exact_bucket_supported`，或把 `core_plus_macro` 升級成 deployable，直接把 support-route false-open regression 升級成 P1 blocker，禁止 heartbeat 繼續沿用該 artifact truth。
