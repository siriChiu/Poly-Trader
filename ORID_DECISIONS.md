# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-19 22:18:37 CST_

---

## 心跳 #fast ORID

### O｜客觀事實
- `python scripts/hb_parallel_runner.py --fast` 已完成 collect + verify 閉環：`Raw 31143→31144 / Features 22561→22562 / Labels 62674→62676`。
- `scripts/hb_parallel_runner.py::_current_leaderboard_candidate_semantic_signature()` 已修正為 **live-probe-priority**；`leaderboard_feature_profile_probe.json` 現在不再因 stale `bull_4h_pocket_ablation.json` q15/chop live_context 被誤判成 cache mismatch。
- `collect_bull_4h_pocket_diagnostics()` 已修正為 **reference_only_stale_live_context** fallback：當 `bull_4h_pocket_ablation.py` timeout 且 artifact live signature 與最新 probe 不一致時，只保留 `bull_all / bull_collapse_q35` 的 reference-only patch 可見性，不再把 stale live-specific proxy cohorts 當成 current q35 truth。
- 本輪 fast heartbeat 產出的 current live truth：
  - `deployment_blocker=circuit_breaker_active`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
  - `current_live_structure_bucket_rows=1`
  - `minimum_support_rows=50`
  - `support_route_verdict=exact_bucket_present_but_below_minimum`
  - `recommended_patch=core_plus_macro`
  - `recommended_patch_status=reference_only_until_exact_support_ready`
- 近期漂移仍是 canonical 250-row pathology：`win_rate=0.0040`、`dominant_regime=bull(100%)`、`avg_quality=-0.2813`、`adverse_streak=246x0`。
- leaderboard 仍穩定：`count=6 / comparable_count=6 / top=rule_baseline / core_only / scan_backed_best / latest_persisted_snapshot`。
- 驗證：
  - `pytest ... test_current_leaderboard_candidate_semantic_signature_prefers_live_probe_bucket_over_stale_bull_artifact ... test_collect_bull_4h_pocket_diagnostics_marks_semantic_mismatch_reference_only ... -q` → `4 passed`
  - browser `/lab` 與 `/execution/status` 均已看到 breaker-first truth、q35 `1/50` support、reference-only patch 與 venue blockers

### R｜感受直覺
- 這一輪最大的產品風險不是 IC 數字，而是 **stale artifact 把 current live truth 帶偏**：一旦 fast heartbeat把舊 q15/chop bull artifact 當成現在的 bull/q35，leaderboard cache 與 patch visibility 都會被假 mismatch/假 live context 汙染。
- breaker 仍是唯一 current-live blocker，但 current q35 `1/50` support truth 也必須保持可見；兩者不能互相遮蔽，更不能讓 stale artifact 取代 live probe。

### I｜意義洞察
1. **current-state signature 的 single source of truth 必須先看 live probe**：current live bucket / rows / support governance route 是 runtime truth，不能先從舊 bull artifact 反推。
2. **bull pocket artifact 在 fast mode timeout 時只能降級成 reference-only**：它仍可提供 `bull_collapse_q35 -> core_plus_macro` 的治理參考，但不能冒充 current q35 live-specific proxy cohorts。
3. **這個修正直接提升 cron-safe 產品可信度**：fast heartbeat 現在能完成 end-to-end，且 `/lab`、`/execution/status`、probe、docs 對同一個 bull/q35 current live truth 說同一句話。

### D｜決策行動
- **Owner**：AI Agent / heartbeat runtime-governance path
- **Action**：維持 `live-probe-priority signature + reference_only_stale_live_context fallback`，確保 stale bull artifact 不再污染 leaderboard candidate probe 與 current-state docs。
- **Artifact**：`scripts/hb_parallel_runner.py`、`tests/test_hb_parallel_runner.py`、`data/heartbeat_fast_summary.json`、`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`、`ARCHITECTURE.md`
- **Verify**：
  - `python -m pytest tests/test_hb_parallel_runner.py::test_current_leaderboard_candidate_semantic_signature_prefers_live_probe_bucket_over_stale_bull_artifact tests/test_hb_parallel_runner.py::test_collect_bull_4h_pocket_diagnostics_marks_semantic_mismatch_reference_only tests/test_hb_parallel_runner.py::test_collect_bull_4h_pocket_diagnostics_reads_live_bucket_support tests/test_hb_parallel_runner.py::test_leaderboard_candidate_cache_hit_uses_semantic_alignment_signature -q`
  - `python scripts/hb_parallel_runner.py --fast`
  - browser `/lab`
  - browser `/execution/status`
- **If fail**：若 fast heartbeat 再把 stale bull/q15 artifact 說成 current q35 truth，或 candidate probe 再因 fake cache mismatch 被迫重跑，直接把它升級成 P1 cron-safe governance blocker，禁止 heartbeat 繼續沿用該 artifact truth。
