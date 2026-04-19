# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-19 21:03:53 CST_

---

## 心跳 #20260419ah ORID

### O｜客觀事實
- `python scripts/hb_parallel_runner.py --fast --hb 20260419ah` 完成 collect + verify 閉環：`Raw 31139→31140 / Features 22557→22558 / Labels 62661→62665`。
- `python scripts/hb_predict_probe.py` / fast heartbeat live probe 顯示 current-live 仍是 **canonical circuit breaker**：`deployment_blocker=circuit_breaker_active`、`streak=273`、`recent 50 wins=0/50`、`additional_recent_window_wins_needed=15`、`structure_bucket=CAUTION|base_caution_regime_or_bias|q15`、`allowed_layers=0`。
- `recent_drift_report.py` 主視窗仍是最近 `250` 筆 `distribution_pathology`：`win_rate=0.0000`、`dominant_regime=bull(100%)`、`avg_quality=-0.2845`、`tail_streak=250x0`；top shifts=`feat_4h_bb_pct_b / feat_4h_bias20 / feat_4h_bias50`。
- 本輪 patch：`server/routes/api.py` 與 `scripts/hb_leaderboard_candidate_probe.py` 現在都會比較 disk cache 與 persisted snapshot，優先採用較新的 leaderboard payload，避免舊但非空的 cache 遮蔽更新 snapshot。
- 回歸驗證：`pytest tests/test_auto_propose_fixes.py tests/test_model_leaderboard.py tests/test_hb_leaderboard_candidate_probe.py -q` → `85 passed`。
- Runtime / browser 驗證：
  - `curl http://127.0.0.1:8000/api/models/leaderboard` 回 `count=6 / comparable_count=6 / top=rule_baseline / core_only / scan_backed_best`
  - browser `/lab` 顯示 `current live blocker circuit_breaker_active`、獨立 `venue blockers`、以及 `reference-only core_plus_macro patch`
  - browser `/execution/status` 顯示 `circuit_breaker_active`、`support 0/50`、`layers 0→0`、與 venue metadata

### R｜感受直覺
- 這一輪最大的產品風險不是「排行榜暫時哪個模型第一」，而是 **runtime / probe / docs 可能各自讀到不同 freshness 的 leaderboard payload**；只要 rowful 舊 cache 還能遮蔽新 snapshot，operator 就會在同一輪 heartbeat 裡看到自相矛盾的 top model 真相。
- breaker 仍是唯一 current-live blocker；如果被 leaderboard plumbing 或 q15 patch 敘事搶走主線，會再次修錯地方。

### I｜意義洞察
1. **leaderboard freshness 不是內部實作細節，而是 operator-facing contract**：只要 API / probe / docs 對 top model 不一致，Strategy Lab 就不可信。
2. **現在的主 blocker 仍然不是 leaderboard 本身**：freshness arbitration 修好後，真正卡住 live deployment 的仍是 breaker release math + recent 250-row pathology。
3. **q15 patch 只能維持 reference-only**：exact support 仍是 `0/50`，因此任何 `core_plus_macro` patch 都只能作治理參考，不能包裝成 deployable runtime fix。

### D｜決策行動
- **Owner**：AI Agent / heartbeat current-state governance path
- **Action**：維持 leaderboard freshness arbitration；後續所有 runtime / probe / docs 一律以最新 snapshot truth 對齊，同時把 breaker-first current blocker 繼續放在所有 surface 的最前面。
- **Artifact**：`server/routes/api.py`、`scripts/hb_leaderboard_candidate_probe.py`、`tests/test_model_leaderboard.py`、`tests/test_hb_leaderboard_candidate_probe.py`、`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`
- **Verify**：
  - `pytest tests/test_auto_propose_fixes.py tests/test_model_leaderboard.py tests/test_hb_leaderboard_candidate_probe.py -q`
  - `python scripts/hb_parallel_runner.py --fast --hb 20260419ah`
  - `curl http://127.0.0.1:8000/api/models/leaderboard`
  - browser：`/lab`、`/execution/status`
- **If fail**：若 rowful older cache 再遮蔽更新 snapshot，或 API / probe / docs 對 top model 再 split-brain，直接把 leaderboard freshness arbitration 升級成 P1 blocker，禁止 heartbeat 繼續沿用舊 cache truth。
