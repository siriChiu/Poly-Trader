# ISSUES.md — Current State Only

_最後更新：2026-04-17 13:10 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 的產品真相是：**live runtime 仍被 canonical 1440m circuit breaker 正式擋下（recent 50 = 1/50，至少還差 14 勝），而 Strategy Lab / SignalBanner 已補上同一套 breaker release math 與 runtime closure 文案，避免 operator 把 q15 patch 或 support artifact 誤讀成可部署訊號。**

本輪已完成的產品化前進：
- 補強 `web/src/pages/StrategyLab.tsx`：live runtime 卡片現在直接顯示 `runtime_closure_state / runtime_closure_summary` 與 circuit breaker release math（recent window、win-rate floor、release gap、streak guardrail）
- 補強 `web/src/components/SignalBanner.tsx`：快捷下單面板現在同步 canonical breaker 狀態與 release math，不再只講 q15 patch
- 兩個前端 surface 都明示：**不要把 support / component patch 當成 breaker release 替代品**
- `tests/test_frontend_decision_contract.py` 已加入對上述 contract 的 regression coverage
- 前端 build 已通過，確認新欄位與 UI 文案不只是靜態字串，而是 TypeScript 可編譯的 runtime contract

---

## Open Issues

### P0. Canonical 1440m circuit breaker 仍然有效，live runtime 仍不可部署
**現況**
- `scripts/hb_predict_probe.py`：`signal=CIRCUIT_BREAKER`
- 原因：`Recent 50-sample win rate: 2.00% < 30%`
- release math：
  - `current_recent_window_wins = 1`
  - `required_recent_window_wins = 15`
  - `additional_recent_window_wins_needed = 14`
  - `current_streak = 2`（streak 已不是 blocker）
- `scripts/hb_circuit_breaker_audit.py`：
  - `mixed_scope.triggered = false`
  - `aligned_scope.triggered = true`
  - root cause = `canonical_breaker_active`

**風險**
- 若忽略這個 blocker，任何 q15/q35、support bucket、component patch 的改善都可能被誤讀成可部署信號
- 就算 UI 已補齊 release math，底層 canonical tail pathology 仍未解除

**下一步**
- 直接追 1440m recent-50 為何只剩 `1/50` 的 canonical path artifact
- 所有 UI / API / docs 必須持續顯示 `至少還差 14 勝` 的 release math，直到 breaker 解除

### P0. Binance / OKX execution lifecycle 仍缺真實 partial-fill / cancel / restart-replay artifact
**現況**
- Dashboard / Strategy Lab / `/api/status` 已能顯示 lifecycle / reconciliation contract
- 但本輪沒有新增真實 venue partial fill / cancel / restart replay artifact；recovery closure 仍缺實證

**風險**
- 沒有 replay artifact，就無法證明重啟後 account/order/position truth 可恢復一致
- execution surface 仍偏向治理可見性，而非 venue recovery closure

**下一步**
- 以 Binance 為第一 venue 補真實 partial fill / cancel / restart replay artifact
- 同步讓 Dashboard / Strategy Lab / `/api/status` 對同一筆 order 顯示一致 replay verdict

### P1. q15 / q35 lane contract 仍需持續防止跨-lane 語義污染
**現況**
- 本輪已把 Strategy Lab / SignalBanner 明確拉回 canonical breaker truth，不再讓 q15 patch 文案搶走主語義
- 但 runtime override / support artifact / lane patch 仍有再次跨 lane 污染的風險

**風險**
- 若 lane 邊界不夠硬，runtime sizing / entry quality / support verdict 仍可能再次跨 lane 漂移
- operator 可能再次把 local patch 誤讀成 canonical live readiness

**下一步**
- 繼續把 q15 / q35 / broader-scope override 都鎖成明確 structure-bucket guard
- 每次新增 runtime override 都必須附 lane-boundary regression test

---

## Not Issues
- 不是 q15 exact-supported patch 本身失效：本輪修的是「主 blocker 呈現順序與語義」，不是回滾 q15 patch
- 不是 breaker release math 缺失：probe / audit / Dashboard / Strategy Lab / SignalBanner 都已可見同一組 math
- 不是 mixed-scope 假 blocker：`mixed_scope.release_ready = true`，真正 blocker 仍是 canonical 1440m aligned scope

---

## Current Priority
1. 先處理 **canonical 1440m circuit breaker tail pathology**，不要把 lane patch 誤當 live readiness
2. 補 **Binance execution lifecycle replay artifact closure**，把 execution 從 visibility 推到 recovery truth
3. 持續做 **lane-boundary hardening**，避免 q15/q35/runtime overrides 再次跨 lane 污染
