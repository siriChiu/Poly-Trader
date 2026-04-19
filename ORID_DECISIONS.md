# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-20 00:32:56 CST_

---

## 心跳 #20260420a ORID

### O｜客觀事實
- `python scripts/hb_parallel_runner.py --fast --hb 20260420a` 已完成 collect + verify 閉環：`Raw 31152→31153 / Features 22570→22571 / Labels 62712→62743`。
- 本輪 current-live truth：
  - `deployment_blocker=circuit_breaker_active`
  - `reason=Consecutive loss streak: 60 >= 50; Recent 50-sample win rate: 0.00% < 30%`
  - `recent 50 wins=0/50`
  - `streak=60`
  - `regime_label=chop / regime_gate=CAUTION`
  - `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q15`
  - `current_live_structure_bucket_rows=0 / minimum_support_rows=50 / gap_to_minimum=50`
  - `support_route_verdict=exact_bucket_missing_proxy_reference_only`
  - `support_governance_route=exact_live_bucket_proxy_available`
- recent canonical 250-row pathology 仍存在：`win_rate=0.0040`、`dominant_regime=bull(100%)`、`avg_quality=-0.2623`、`avg_pnl=-0.0086`。
- root cause investigation 確認：`hb_predict_probe.py` / `live_predict_probe.json` 已經有 q15 current-live truth，但 `/api/status.execution.live_runtime_truth` 頂層缺少 `current_live_structure_bucket / rows / minimum / gap / support_governance_route`，導致 API / UI / docs machine-read split-brain。
- 本輪產品化 patch：`server/routes/api.py::_build_live_runtime_closure_surface()` 現在會在 breaker 下也回傳 top-level q15 same-bucket support 欄位，不再只藏在 `deployment_blocker_details`。
- 驗證：
  - `pytest tests/test_server_startup.py -q` → `29 passed`
  - `pytest tests/test_frontend_decision_contract.py -q` → `19 passed`
  - `cd web && npm run build` → pass
  - `curl http://127.0.0.1:8000/api/status`：已回傳 `current_live_structure_bucket=q15`、`rows=0/50`、`support_governance_route=exact_live_bucket_proxy_available`
  - browser `/execution/status`、`/lab`：都已看到 q15 `0/50` current-live truth

### R｜感受直覺
- 這一輪真正的產品風險不是缺少數字，而是 **API 把 same-bucket truth 藏在太深的 nested blocker details**。
- breaker-first 沒有錯，但如果 current-live q15 bucket / 0/50 rows 不在 top-level，前端與文件就容易各自 fallback，最後又形成「probe 是對的、API/UI 是空的」的假 split-brain。
- 這類 bug 比單純數值錯誤更危險，因為 operator 看到的是「不知道 current bucket 是什麼」，而不是明確的 `q15 0/50`。

### I｜意義洞察
1. **breaker-first 不代表可以隱藏 same-bucket support truth**：current-live blocker 是 breaker，但 operator 仍需要 machine-read 看到當前 q15 bucket、rows、gap 與 governance route。
2. **top-level API contract 本身就是產品化工作**：probe JSON 正確不夠；若 `/api/status` 頂層欄位缺失，Dashboard / Strategy Lab / docs 就會各自補洞，最後再度 drift。
3. **本輪 patch 的價值是消除 API/UI/docs 的語義裂縫**：現在同一個 q15 `0/50` 真相可以被 curl、browser、tests 同時驗證，不再依賴人工翻 nested JSON。

### D｜決策行動
- **Owner**：AI Agent / runtime contract / execution surfaces
- **Action**：維持 `/api/status.execution.live_runtime_truth` 在 breaker 下也直接輸出 `current_live_structure_bucket / current_live_structure_bucket_rows / minimum_support_rows / current_live_structure_bucket_gap_to_minimum / support_governance_route / support_route_deployable`。
- **Artifacts**：
  - `server/routes/api.py`
  - `tests/test_server_startup.py`
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ORID_DECISIONS.md`
  - `ARCHITECTURE.md`
- **Verify**：
  - `python -m pytest tests/test_server_startup.py -q`
  - `python -m pytest tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`
  - `curl http://127.0.0.1:8000/api/status`
  - browser `/execution/status`
  - browser `/lab`
- **If fail**：若 top-level runtime surfaces 再把 q15 current-live bucket / rows / gap 回成 null，直接升級為 execution-runtime P0 blocker，因為這會讓 breaker-first truth 與 same-bucket governance 在 API / UI / docs 重新 split-brain。
