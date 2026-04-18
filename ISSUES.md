# ISSUES.md — Current State Only

_最後更新：2026-04-18 22:16 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線事實
- **本輪 heartbeat #20260418g 已完成閉環**：`Raw=30888 / Features=22306 / Labels=62195`，`simulated_pyramid_win=0.5788`，`Global IC=14/30`，`TW-IC=30/30`。
- **current-live blocker 仍是 canonical circuit breaker**：`hb_predict_probe.py` 顯示 `signal=CIRCUIT_BREAKER`、`deployment_blocker=circuit_breaker_active`、`allowed_layers=0`、`allowed_layers_reason=circuit_breaker_blocks_trade`；對齊 canonical 1440m 時 `recent 50` 只贏 `2/50`，距離 release floor `15/50` 還差 `13` 勝，且當前 `streak=47`。
- **recent tail pathology 仍未解除**：`recent_drift_report.py` 主視窗仍是最近 `1000` 筆，`interpretation=distribution_pathology`、`dominant_regime=bull 89.0%`、`win_rate=0.8430`；canonical 1440m 尾端已擴大為 **47 連續 `simulated_pyramid_win=0`**（自 `2026-04-17 13:41:12` 起）。
- **q15 / q35 目前都只是 background reference**：`hb_q15_support_audit.py`、`hb_q15_bucket_root_cause.py`、`hb_q35_scaling_audit.py` 都被 runtime breaker preempt；不得再把舊 q15/q35 patch 敘事誤寫成 current-live blocker。
- **Strategy Lab 的 placeholder-only UX 已產品化前進**：`/api/models/leaderboard` 仍是 `count=0 / comparable_count=0 / placeholder_count=4`，但 `strategy_param_scan` 已提供 `6` 個候選策略；`web/src/pages/StrategyLab.tsx` 現在會在模型排行榜區塊直接顯示 fallback candidate cards 與 `載入候選` 按鈕。瀏覽器已驗證可從 fallback panel 載入 `Auto Leaderboard · 重掃 rule_baseline #01` 回到工作區。
- **策略排行榜本身可用**：`/lab` 的策略排行榜已有 `6` 條重掃策略列，可直接作為 placeholder-only model leaderboard 的 operator fallback，而不是停在 no-trade 空榜。
- **venue readiness blocker 仍在**：工作區 / `/execution` / `/execution/status` 仍顯示 `live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證`；breaker 解除前後都不能把 UI 誤報成 live-ready。
- **稀疏來源 blocker 尚未清空**：仍有 `8` 個 blocked sparse features；其中 `fin_netflow` 最新狀態仍是 `auth_missing`（缺 `COINGLASS_API_KEY`）。

---

## Open Issues

### P0. canonical circuit breaker active — current live path remains non-deployable
**現況**
- `signal=CIRCUIT_BREAKER`
- `deployment_blocker=circuit_breaker_active`
- `allowed_layers=0`
- canonical `horizon=1440m`
- `recent_window=50`
- `current_recent_window_wins=2`
- `required_recent_window_wins=15`
- `additional_recent_window_wins_needed=13`
- `streak=47`

**風險**
- 若繼續沿用 q15/q35 的舊 blocker 敘事，operator 會誤判當前主 blocker。
- breaker 未解除前，任何 floor-gap / support patch 都不能當成 deployment closure。

**下一步**
- 以 `hb_predict_probe.py`、`hb_circuit_breaker_audit.py`、`recent_drift_report.py` 鎖定 recent 50 / 1000 的 release-math 根因。
- 驗證方式：`python scripts/hb_parallel_runner.py --fast --hb <N>`、`python scripts/hb_predict_probe.py`、`python scripts/hb_circuit_breaker_audit.py <N>`、瀏覽器 `/execution/status`。

### P0. recent canonical tail is still pathological (47-loss streak, bull-dominated 1000-row pathology)
**現況**
- `47` 連續 `simulated_pyramid_win=0`
- primary drift window = `1000`
- `interpretation=distribution_pathology`
- `dominant_regime=bull (89.0%)`
- sibling-window 對比顯示 `win_rate 0.551 → 0.843`、`quality 0.2039 → 0.4577`，代表目前不是「全面變差」，而是 canonical tail 與 broader bull pocket 嚴重脫鉤

**風險**
- 若只看全域 / TW-IC 改善，會錯把 bull pocket 的高勝率當成可部署優勢。
- 若不先拆出 tail root cause，breaker release math 只會持續卡死。

**下一步**
- 直接檢查 recent 50 / 100 / 1000 canonical rows 的 target path、regime mix、4H shift 與 release-window examples，找出為何 recent 50 持續失敗。
- 驗證方式：`recent_drift_report.py`、`hb_predict_probe.py`、`hb_circuit_breaker_audit.py`、必要時針對 tail pathology 補 regression test。

### P1. canonical model leaderboard is still placeholder-only, but fallback UX is now live
**現況**
- `/api/models/leaderboard`：`count=0 / comparable_count=0 / placeholder_count=4`
- `strategy_param_scan.saved_strategy_count=6`
- Strategy Lab 現在已在模型排行榜區塊顯示 fallback candidate cards + `載入候選`
- 瀏覽器已驗證從 fallback panel 載入 `Auto Leaderboard · 重掃 rule_baseline #01` 成功切回工作區

**風險**
- 若 canonical model leaderboard 一直沒有 comparable row，模型排名仍無法直接回答「哪個 model deployment profile 可部署」。
- 若只靠 placeholder table 而沒有 fallback candidate，operator 會卡在 no-trade 空榜；這一點本輪已修掉，但根本問題（`comparable_count=0`）仍在。

**下一步**
- 讓 canonical leaderboard 產生至少一條 `comparable_count > 0` 的 model row；在做到前，維持 placeholder-only honesty + strategy_param_scan fallback。
- 驗證方式：`/api/models/leaderboard` payload、瀏覽器 `/lab`、`python scripts/hb_model_leaderboard_api_probe.py`。

### P1. venue readiness still blocks true live operations after breaker clears
**現況**
- `/execution`、`/execution/status`、Strategy Lab 工作區仍顯示：`live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證`

**風險**
- 即使 breaker 解除，若 venue lifecycle 未驗證，operator 仍不能把 UI blocker 消失誤讀成可實盤。

**下一步**
- 維持 venue blocker 在 operator surfaces 的可見性，直到 credentials / order ack / fill recovery 全部有 runtime 證據。
- 驗證方式：瀏覽器 `/execution`、`/execution/status`、對應 `/api/status` payload。

### P1. sparse-source auth/history blockers still cap feature maturity
**現況**
- blocked sparse features = `8`
- `fin_netflow` 仍為 `auth_missing`
- 其餘 sparse-source 多為 `archive_required` / `snapshot_only`

**風險**
- 研究訊號成熟度不足時，會持續限制 FeatureChart / coverage / research overlay 的可信度。

**下一步**
- 補齊 `COINGLASS_API_KEY` 後重跑 heartbeat collect，並持續累積 forward archive；未補 auth 前不得把 `fin_netflow` 誤包裝成可用訊號。
- 驗證方式：`python scripts/hb_parallel_runner.py --fast --hb <N>`、`/api/features/coverage`、feature coverage report。

---

## Not Issues
- **q15 patch-active / q35 scaling lane**：本輪都不是 current-live 主 blocker；runtime 已被 canonical breaker preempt。
- **Strategy Lab 缺少 placeholder-only fallback guidance**：本輪已修復；模型排行榜現在會直接顯示 `strategy_param_scan` 候選與 `載入候選` 動作。
- **Execution route reachability**：`/execution`、`/execution/status`、`/lab` 本輪皆可打開且能看到最新 blocker truth。

---

## Current Priority
1. **先解 canonical circuit breaker release math，停止沿用舊 q15/q35 blocker 敘事**
2. **把 recent canonical tail pathology 轉成可修的 root cause / regression patch**
3. **讓 canonical model leaderboard 產生至少一條 comparable row；在此之前，維持 strategy_param_scan fallback 可操作**
4. **持續保留 venue readiness blocker，禁止任何 live-ready 假象**
