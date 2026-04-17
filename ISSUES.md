# ISSUES.md — Current State Only

_最後更新：2026-04-17 12:47 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 的最新產品真相是：**runtime 仍被 canonical 1440m circuit breaker 正式擋下，但 q35 bias50 校正已被鎖回 q35 專屬 lane，不再污染 q15 exact-supported component patch。** 這輪完成的是一個 execution-correctness / runtime-contract 修補，而不是數字重跑。

本輪已完成的產品化前進：
- 修補 `model/q35_bias50_calibration.py`：`compute_piecewise_bias50_score()` 現在**只有在 `CAUTION|structure_quality_caution|q35`** 才會套用 q35 bias50 校正
- 避免 q35 calibration 洩漏到 q15 lane，導致 q15 exact-supported patch 把 entry quality 誤抬高、runtime sizing 過度樂觀
- 新增 regression test：`test_piecewise_q35_bias50_calibration_ignores_non_q35_structure_bucket`
- 既有 q15 patch regression 再次通過：q15 exact-supported patch 的 profile 回到預期 `entry_quality=0.5501`、`allowed_layers=1`
- live runtime 重新驗證後，系統仍明確維持 `CIRCUIT_BREAKER`，沒有把這次 q15/q35 修補誤報成可部署進展

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
- operator 若只看局部 lane 修補，仍可能對 live readiness 產生錯誤期待

**下一步**
- 以 canonical 1440m tail pathology 為唯一 breaker truth
- 直接追 `recent 50` 為何只剩 `1/50`，不要再用 mixed-scope 或局部 lane 訊號稀釋 blocker
- 所有 UI / API / docs 都必須持續顯示 `還差 14 勝` 的 release math

### P0. Binance / OKX execution lifecycle 仍缺真實 partial-fill / cancel / restart-replay artifact
**現況**
- lifecycle contract / reconciliation surface 已存在
- 但本輪沒有新增真實 venue lifecycle artifact；仍缺 partial fill / cancel / restart replay 的可回放證據

**風險**
- 沒有 replay artifact，就無法證明重啟後 account/order/position truth 可恢復一致
- Dashboard / Strategy Lab / `/api/status` 仍可能只有 visibility，沒有 recovery closure

**下一步**
- 以 Binance 為第一 venue 補真實 partial fill / cancel / restart replay artifact
- 同步讓 Dashboard / Strategy Lab / `/api/status` 對同一筆 order 顯示一致 replay verdict

### P1. q15 / q35 lane contract 仍需持續防止跨-lane 語義污染
**現況**
- 本輪已修掉一個真實 bug：q35 bias50 calibration 會錯套到 q15 lane
- 代表 live decision contract 仍存在「局部治理 artifact 誤套到其他 lane」的風險

**風險**
- 只要 lane 邊界不夠硬，runtime sizing / entry quality / support verdict 就可能再次跨 lane 污染
- 這類 bug 會讓 operator 看到錯誤的 deployability 或 floor-cross 結論

**下一步**
- 繼續把 q15 / q35 / broader-scope override 都鎖成明確 structure-bucket guard
- 每次新增 runtime override 都必須附 lane-boundary regression test

---

## Not Issues
- 不是 q15 exact-supported patch 本身失效：回歸測試顯示 q15 patch 仍能在正確 lane 產生預期 `entry_quality=0.5501`
- 不是 breaker release math 缺失：probe / drilldown / audit 都仍能輸出 `additional_recent_window_wins_needed=14`
- 不是 mixed-scope 假 blocker：`mixed_scope.release_ready = true`，真正 blocker 仍是 canonical 1440m aligned scope

---

## Current Priority
1. 先處理 **canonical 1440m circuit breaker tail pathology**，不要把 lane patch 誤當 live readiness
2. 補 **Binance execution lifecycle replay artifact closure**，把 execution 從 visibility 推到 recovery truth
3. 持續做 **lane-boundary hardening**，避免 q15/q35/runtime overrides 再次跨 lane 污染
