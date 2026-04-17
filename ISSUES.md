# ISSUES.md — Current State Only

_最後更新：2026-04-18 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線
本輪把 `/execution` 的 **strategy snapshot / version contract** 補到 operator surface：
- 新增 `GET /api/execution/strategies/source`
- `/api/execution/overview` / `/api/execution/runs` 繼續帶 `strategy_source_summary`、profile/run `strategy_binding`
- Execution Console 現在直接顯示：
  - strategy source summary
  - sleeve 對應 strategy snapshot
  - run 綁定的 strategy hash / source /最近版本資訊
- 未覆蓋 sleeve 會明示 `missing_saved_strategy`，不再隱藏成模糊預設

已驗證：
- `source venv/bin/activate && python -m pytest tests/test_execution_run_control.py tests/test_execution_console_overview.py tests/test_frontend_decision_contract.py tests/test_server_startup.py -q`
- `cd web && npm run build`

**目前定位仍必須講清楚：這是 stateful operator-beta + strategy version clarity，不是 per-run ledger closure。**

---

## Open Issues

### P0. Run 仍不是 `ExecutionService` 的真正 runtime owner
**現況**
- run 已有 start / pause / stop / event log
- run 已可顯示綁定的 strategy snapshot / version
- 但 run 還沒有真正擁有 order lifecycle、venue ack / fill / cancel、restart replay

**風險**
- 若把「有 run + 有策略版本」誤讀成完整 bot owner，仍會造成假產品化

**下一步**
- 把 `ExecutionRun` 綁到 `ExecutionService`
- 讓 lifecycle / recovery / replay / venue artifact 落到 run scope

### P0. Capital / position / open-order / PnL 仍不是 per-run attribution
**現況**
- `/execution` 現在能顯示 budget、shared balance、shared symbol positions / open orders
- 但這仍是 shared preview，不是 run-owned ledger
- 沒有真正 per-run realized / unrealized / total PnL、capital usage、open-order ownership

**風險**
- operator 雖然能看懂 strategy 版本，仍無法對單一 run 做資金與績效閉環

**下一步**
- 建立 per-run capital / position / open-order attribution
- 補 run-owned realized / unrealized / total PnL

### P1. `/execution` 還缺 capital actions 與完整 strategy coverage
**現況**
- 手動交易 / automation toggle 已進 `/execution`
- strategy source route 與 snapshot/version 已可見
- 但 capital actions（充值 / 提現 / 調整部署資金）尚未進來
- 未覆蓋 sleeve 目前只會被明示，還沒有 operator 內建補齊流程

**風險**
- `/execution` 仍像 operator beta，而不是完整 bot operations workspace

**下一步**
- 把 capital actions 收進 `/execution`
- 讓 operator 能直接補齊缺少的 strategy snapshot coverage，而不是跳出去手動追

### P1. Binance / OKX readiness 仍缺 venue-backed closure
**現況**
- reconciliation、metadata smoke、venue lanes 已可見
- 但 run 尚未擁有真實 venue-backed ack / fill / cancel / replay artifact ownership

**風險**
- 不能把現在的 surface 寫成 live-ready

**下一步**
- 將 venue-backed artifact 與 run scope 對齊
- 讓 `/execution` 與 Dashboard 都能直接顯示 run-owned venue closure

---

## Not Issues
- 不是看得到 strategy hash / source，就等於 run 已完成 runtime ownership
- 不是有 stateful run control，就等於 per-run ledger 完成
- 不是看得到 shared balance / shared positions / shared open orders，就等於 per-run PnL 已閉環

---

## Current Priority
1. **把 shared preview 升級成 per-run capital / position / open-order / PnL attribution**
2. **把 `ExecutionRun` 綁到 `ExecutionService`，形成 run-owned lifecycle / replay / recovery**
3. **把 capital actions 與 strategy coverage closure 收進 `/execution`**
4. **補齊 Binance / OKX venue-backed closure evidence**
