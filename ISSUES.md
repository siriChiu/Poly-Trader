# ISSUES.md — Current State Only

_最後更新：2026-04-17 09:12 UTC_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪 heartbeat 把 **circuit breaker 與 recent pathology 的 runtime truth 綁在一起**：
- `model/predictor.py` 的 `CIRCUIT_BREAKER` 回傳現在會同步帶出 `decision_quality_recent_pathology_*`
- `scripts/hb_predict_probe.py` 與 `/api/status` 的 runtime closure summary 不再只說 breaker，會直接附帶 canonical recent-window pathology 原因
- operator 現在能在 **breaker-first** 前提下，同時看到「為什麼被擋」與「最近 canonical distribution 有什麼病灶」

本輪實測事實：
- targeted regression：`python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_server_startup.py -q` → **78 passed**
- 本輪 collect/runtime：`Raw=30599 / Features=22017 / Labels=61773`，本輪 **+1 / +1 / +1**
- canonical diagnostics：`Global IC 14/30`、`TW-IC 28/30`
- recent drift：主要視窗為最近 `500` 筆，`win_rate=0.804`、`bull=100%`、`interpretation=distribution_pathology`
- live predictor：`CIRCUIT_BREAKER`，canonical 1440m recent 50 只贏 `5/50`，距 release 還差 `10` 勝
- sparse-source blockers：仍有 `8` 個；`fin_netflow` 仍被 `COINGLASS_API_KEY` 缺失卡住

---

## Open Issues

### P0. Circuit breaker 仍是 live deployment blocker
**現況**
- canonical 1440m recent 50 = `5/50`，recent win rate = `10%`
- release floor = `30%`，目前至少還差 `10` 勝
- 本輪已修正：breaker path 不再遮蔽 recent pathology，runtime 可同時看見 blocker 與 drift

**風險**
- 若任何 surface 又退回只顯示 breaker、不顯示 pathology，operator 會重新失去 root-cause 視角

**下一步**
- 維持 breaker-first + pathology-visible contract
- 下一輪優先追 canonical tail root-cause / release evidence，不放寬 breaker

### P0. Recent distribution pathology 已可見，但根因尚未收斂
**現況**
- 最近 `500` 筆 `simulated_pyramid_win=0.804`，但 `bull` regime 佔比 `100%`，被判定為 `distribution_pathology`
- 最近 `100` 筆 `win_rate=0.42`，同樣是 `bull=100%`，顯示 recent canonical window 高度偏態
- sibling-window contrast 指向 `feat_4h_bias20 / feat_4h_ma_order / feat_4h_bb_pct_b` 位移，並新增 `feat_dxy / feat_vix` compression 訊號

**風險**
- 若只看高 win-rate 視窗，容易把 bull-only concentration 誤讀成 deployment readiness

**下一步**
- 以 canonical recent-window drift root-cause 為主線
- 釐清 bull-only concentration、4H 結構位移與 macro compression 對 runtime sizing 的真實影響

### P0. Binance / OKX 仍缺真實 venue-backed partial-fill / cancel / restart-replay artifact
**現況**
- lane drilldown、timeline、operator instruction 已有產品 surface
- 但真正的交易所 venue-backed artifact 鏈仍不足，closure 仍偏 dry-run / internal-ready

**風險**
- UI 雖已有產品感，但沒有 venue-backed artifact 仍不能宣稱 live-ready execution

**下一步**
- 先補 Binance 真實 partial-fill / cancel / restart replay 證據鏈
- 驗證 `/api/status`、Dashboard、Strategy Lab 對同一 lane 的 truth 完全一致

### P1. Sparse-source readiness 仍被 auth / 歷史缺口阻塞
**現況**
- blocked sparse features = `8`
- `fin_netflow` 仍為 `source_auth_blocked`，根因是 `COINGLASS_API_KEY` 缺失
- 其餘 sparse lanes 多數已有 forward archive，但歷史 coverage 仍卡在 archive gap

**風險**
- 若 production / research feature 邊界不清楚，會污染產品敘事與 operator 預期

**下一步**
- 解除 CoinGlass auth blocker
- 繼續把 sparse-source 嚴格留在 research / blocked 層，不可滲入 core runtime 決策

---

## Not Issues
- 不是 runtime 在 breaker 下完全失明：本輪已把 recent pathology 正式傳到 predictor / probe / `/api/status`
- 不是資料管線完全停住：本輪 collect 後 `raw/features/labels` 均有新增
- 不是 targeted regression 失敗：本輪 78 個關鍵測試通過
- 不是 breaker 已解除：canonical 1440m live breaker 仍 active

---

## Current Priority
1. 維持 **breaker-first + pathology-visible runtime truth**，禁止把 patch / 局部高分敘事包裝成 deployment readiness
2. 補出 **Binance 真實 venue-backed artifact 鏈**，關閉 execution lane P0
3. 解除 **CoinGlass auth blocker**，並把 sparse-source 穩定留在 research / blocked 邊界內
