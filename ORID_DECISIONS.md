# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-20 00:06:40 CST_

---

## 心跳 #fast ORID

### O｜客觀事實
- `python scripts/hb_parallel_runner.py --fast` 已完成 collect + verify 閉環：`Raw 31148→31149 / Features 22565→22567 / Labels 62691→62712`。
- 本輪 current live truth：
  - `deployment_blocker=circuit_breaker_active`
  - `recent 50 wins=1/50`
  - `additional_recent_window_wins_needed=14`
  - `streak=30`
  - `allowed_layers=0`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
  - `current_live_structure_bucket_rows=1 / minimum_support_rows=50 / gap_to_minimum=49`
  - `recommended_patch=core_plus_macro_plus_all_4h`
  - `recommended_patch_status=reference_only_until_exact_support_ready`
- recent canonical 250-row pathology 仍存在：`win_rate=0.0040`、`dominant_regime=bull(100%)`、`avg_quality=-0.2724`、`avg_pnl=-0.0091`。
- 本輪產品化 patch：`Dashboard.tsx`、`ExecutionConsole.tsx`、`ExecutionStatus.tsx`、`StrategyLab.tsx` 的 execution 區塊，在第一次 `/api/status` 尚未返回前改顯示 `同步中 / 正在同步 /api/status`，不再假裝 `unavailable / none / unknown`。
- 驗證：
  - `pytest tests/test_frontend_decision_contract.py -q` → `19 passed`
  - `cd web && npm run build` → pass
  - browser 首屏 `/`、`/execution/status`、`/lab` 都已看到 loading copy `同步中`
  - `curl http://127.0.0.1:8000/api/status` 仍回傳 breaker-first truth 與 q35 `1/50` support

### R｜感受直覺
- 這一輪最真實的產品風險不是缺少新數字，而是 **頁面剛打開時短暫說錯真相**。
- 如果 operator 在首屏看到 `unavailable / none / unknown`，就算幾秒後資料回來，也已經種下錯誤心智模型；這比單純的 loading spinner 更危險。
- breaker 仍是唯一 current-live blocker；所以 execution surfaces 必須連 loading 階段都維持 breaker-first product semantics。

### I｜意義洞察
1. **loading state 也是 runtime contract 的一部分**：不能只在資料回來後才要求 breaker-first，一進頁的第一屏也必須避免假陰性。
2. **這個 patch 雖小，但直接提升 operator trust**：它消除了「頁面剛開時看起來沒 blocker / metadata unavailable」的錯覺，讓 UI 更像 production console，而不是研究儀表板。
3. **主 blocker 仍然不是 UI 本身，而是 canonical pathology**：q35 support 依舊只有 `1/50`，recent 250 rows 依舊是 distribution pathology；UI patch 只是讓真相更穩定可見。

### D｜決策行動
- **Owner**：AI Agent / frontend execution surfaces
- **Action**：維持 initial-sync loading contract；在 `/api/status` 首次返回前，execution summaries 只能說 `同步中`，不可回退成 `unavailable / none / unknown`。
- **Artifacts**：
  - `web/src/pages/Dashboard.tsx`
  - `web/src/pages/ExecutionConsole.tsx`
  - `web/src/pages/ExecutionStatus.tsx`
  - `web/src/pages/StrategyLab.tsx`
  - `tests/test_frontend_decision_contract.py`
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ORID_DECISIONS.md`
  - `ARCHITECTURE.md`
- **Verify**：
  - `python -m pytest tests/test_frontend_decision_contract.py -q`
  - `cd web && npm run build`
  - browser `/`
  - browser `/execution/status`
  - browser `/lab`
  - `curl http://127.0.0.1:8000/api/status`
- **If fail**：若首屏又回退成 `unavailable / none / unknown`，直接升級為 execution-surface P1 blocker，因為它會在 breaker 未解除前持續污染 operator 對 current-live truth 的第一印象。
