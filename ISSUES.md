# ISSUES.md — Current State Only

_最後更新：2026-04-17 12:40 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 的最新產品真相是：**資料管線仍在前進、canonical IC / recent drift / circuit-breaker 診斷都可重跑，而且 circuit breaker 已從「只有 on/off」升級成 operator 可執行的 release math contract。Dashboard / probe / drilldown 現在能直接看到 recent 50 視窗還差幾勝才能解除 blocker。**

本輪已完成的產品化前進：
- heartbeat 實際推進資料：`Raw=30591 (+1) / Features=22009 (+1) / Labels=61736 (+1)`
- `scripts/hb_collect.py` 成功完成 collect / feature / label 閉環
- canonical 診斷：`Global IC=14/30`、`TW-IC=29/30`
- recent drift 仍指出最近 500 筆是 `bull 100%` 的 distribution pathology，而不是 collector 停擺
- `model/predictor.py` 現在輸出 breaker release math：
  - `current_streak`
  - `current_recent_window_wins`
  - `required_recent_window_wins`
  - `additional_recent_window_wins_needed`
  - `blocked_by / release_ready`
- `scripts/hb_predict_probe.py` / `scripts/live_decision_quality_drilldown.py` 現在會把 breaker release math 寫進 runtime summary
- Dashboard `ConfidenceIndicator` 現在在 `circuit_breaker_active` 狀態下顯示：
  - `recent 50 release window`
  - `release gap`
  - `streak release condition`
  - `operator next step`
  不再把 support/floor-cross 卡片誤拿來解釋 breaker

---

## Open Issues

### P0. Canonical 1440m circuit breaker 仍然有效，live runtime 仍不可部署
**現況**
- `scripts/hb_predict_probe.py`：`signal=CIRCUIT_BREAKER`
- 原因：`Recent 50-sample win rate: 2.00% < 30%`
- `scripts/hb_circuit_breaker_audit.py`：
  - `aligned_scope.triggered = true`
  - `aligned_scope.release_condition.current_recent_window_wins = 1`
  - `aligned_scope.release_condition.required_recent_window_wins = 15`
  - `aligned_scope.release_condition.additional_recent_window_wins_needed = 14`
- mixed all-horizon scope 已證明不是 blocker；真正 blocker 是 **canonical 1440m aligned scope**

**風險**
- 若沒有把 breaker 視為當前最高優先 blocker，會把 q15/q35、support 或 calibration 修補誤讀成可部署進展
- 若 UI 只顯示 generic blocker 文案而不顯示 release math，operator 無法知道距離解除還差多少

**下一步**
- 持續以 canonical 1440m tail 為唯一 breaker truth
- 下一輪直接驗證 `/api/predict/confidence` 與 Dashboard runtime surface 都已消費 `additional_recent_window_wins_needed`
- 若 release gap 長時間不收斂，升級成 tail-path root-cause / label-pathology blocker

### P0. Binance / OKX execution lifecycle 仍未完成真實 partial-fill / cancel / restart-replay artifact
**現況**
- `/api/status.execution_reconciliation.lifecycle_contract` 已能顯示 baseline contract / replay readiness / missing lifecycle events
- 但目前仍偏向 **visibility contract**，不是 venue lifecycle closure

**風險**
- 若沒有真實 partial fill / cancel / restart replay artifact，runtime / recovery / UI 仍無法證明重啟後可完整回放 order lifecycle

**下一步**
- 以 Binance 為第一 venue，補齊 partial fill / cancel / restart replay artifact
- 讓 Dashboard / Strategy Lab / `/api/status` 對同一筆 order 顯示一致 replay verdict

### P1. Recent bull-only distribution pathology 仍在污染 calibration 判讀
**現況**
- `recent_drift_report.py`：最近 500 筆 `win_rate=0.8000`、`dominant_regime=bull (100.00%)`
- alerts：`label_imbalance`、`regime_concentration`、`regime_shift`
- sibling-window 對比：`prev_win_rate=0.988 → current=0.800`、`quality Δ=-0.3349`、`pnl Δ=-0.0167`

**風險**
- 若把這個 bull-only pocket 直接當成 calibration / deployment 證據，會產生假 readiness

**下一步**
- 繼續讓 live probe / drilldown / leaderboard 明確拒絕 polluted lane
- breaker 解除後，第一優先驗證是否仍被 bull-only pathology 汙染

### P1. Sparse-source blockers 仍需分流治理
**現況**
- blocked sparse features：`8`
- 分布：`archive_required=3`、`snapshot_only=4`、`short_window_public_api=1`
- `fin_netflow` 仍是 auth-blocked 代表案例，最新 status 仍為 `auth_missing`

**風險**
- 若把 forward archive ready 誤讀成 feature 已成熟，會把研究型 sparse source 混進主產品敘事

**下一步**
- `fin_netflow` 先補 auth
- 其餘 source 繼續區分 auth-blocked / archive-gap / snapshot-only，不混成 generic coverage 問題

---

## Not Issues
- 不是資料管線停滯：本輪仍有 `+1 raw / +1 features / +1 labels`
- 不是 IC 腳本失效：`full_ic.py`、`regime_aware_ic.py`、`recent_drift_report.py` 都成功刷新
- 不是 breaker 混 horizon 假陽性：`hb_circuit_breaker_audit.py` 已證明 blocker 來自 canonical 1440m aligned scope

---

## Current Priority
1. 先處理 **canonical 1440m circuit breaker release path**，把 runtime/UI/operator surface 都對齊 release math
2. 補 **Binance execution lifecycle artifact closure**，不要停留在 visibility-only contract
3. 持續治理 **bull-only recent pathology** 與 **sparse-source blockers**，避免假 readiness
