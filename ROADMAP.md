# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 23:27 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **canonical model leaderboard 已恢復可比較 rows**：`backtesting/model_leaderboard.py` 現在會把 `strategy_param_scan` 的最佳參數作為 `scan_backed_best` deployment profile candidate 納入 canonical 評估；最新 `/api/models/leaderboard` 為 `count=5 / comparable_count=5 / placeholder_count=1`。
- **P1 placeholder-only 主 blocker 已解除**：`hb_model_leaderboard_api_probe.py` 最新為 `refreshing=false / stale=false / comparable_count=5`，不再是只有 placeholder snapshot。
- **q15/q35 stale blocker 敘事已被 circuit breaker 真相取代**：最新 `hb_predict_probe.py` 與 `hb_q15_support_audit.py` 都表明本輪 current-live blocker 是 canonical breaker，而不是 q15 support/component patch。
- **Heartbeat charter 已明確加入『主動追根因並積極修復 P0/P1』規則**：HEARTBEAT 不再允許只做被動巡檢或只報告不修。
- **本輪驗證已完成**：
  - `python -m pytest tests/test_model_leaderboard.py::test_deployment_profile_candidates_include_scan_backed_best_when_artifact_exists tests/test_model_leaderboard.py::test_build_strategy_params_uses_scan_backed_best_params_when_available -q` → PASS
  - `python scripts/hb_model_leaderboard_api_probe.py` → `comparable_count=5`
  - `python -m pytest tests/test_auto_propose_fixes.py tests/test_hb_predict_probe.py tests/test_q15_support_audit.py tests/test_api_feature_history_and_predictor.py -q` → `102 passed`

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live 真相，直到真正解除
**目前真相**
- canonical `1440m` recent `50` 只贏 `0/50`
- `streak=74`
- 距離 release floor `15/50` 還差 `15` 勝

**成功標準**
- 要嘛 recent `50` 提升到 `>=15` 勝且 breaker 解除；
- 要嘛所有 operator / heartbeat / docs / issues 都只把 breaker release math 當成唯一 current-live blocker。

### 目標 B：把 recent canonical tail pathology 轉成可修的 root cause
**目前真相**
- primary drift window = `1000`
- `interpretation=distribution_pathology`
- `dominant_regime=bull 91.7%`
- canonical tail 已 `74x0`

**成功標準**
- 能清楚指出 recent `50 / 100 / 1000` 為何持續形成 loss tail；
- 對應 patch 必須能用 `recent_drift_report.py` / `hb_predict_probe.py` / `hb_circuit_breaker_audit.py` 重跑驗證。

### 目標 C：把 `scan_backed_best` 升級成穩定的 code-backed canonical deployment profile
**目前真相**
- leaderboard 已有 `5` 條 comparable rows
- 但目前主要依賴 artifact-backed `scan_backed_best`

**成功標準**
- comparable rows 仍保留，
- 同時把有效參數沉澱為清楚命名、穩定可維護的 code-backed profiles，而不是長期依賴 scan artifact。

### 目標 D：保持 execution/runtime/operator surface 同步，且不掩蓋 venue blocker
**目前真相**
- `/api/status` 已可正確顯示 breaker release math
- 同頁仍明示 `live exchange credential / order ack / fill lifecycle` 未驗證

**成功標準**
- 即使 breaker 將來解除，operator surface 仍必須保留 venue readiness blocker，直到 runtime 證據真的 closure。

---

## 下一步
1. **把 canonical tail pathology 轉成具體 patch，而不是只維持觀測**
   - 驗證：`recent_drift_report.py`、`hb_predict_probe.py`、必要時新增 regression test
2. **把 `scan_backed_best` 正式沉澱為 stable deployment profiles**
   - 驗證：`/api/models/leaderboard` 仍維持 `comparable_count > 0`，且 profile source / naming 更穩定
3. **保持 breaker-first current-live truth 與 venue blockers 同步可見**
   - 驗證：`/execution/status`、`/execution`、`/api/status`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- recent tail pathology 有可重跑、可驗證的 root cause / patch / regression evidence
- canonical model leaderboard 不再退回 placeholder-only，且 scan-backed params 已逐步升級成穩定 canonical profiles
- heartbeat 維持：**issue 對齊 → 主動修復 P0/P1 → verify → docs overwrite → commit → push**
