# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 10:16 UTC_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- **Fast heartbeat timeout fallback observability**：
  - `scripts/hb_parallel_runner.py` 已新增 `serial_results` summary contract
  - fast summary 現在逐項保存 `success / timed_out / fallback_artifact_used / artifact_path / artifact_generated_at / artifact_age_seconds`
  - operator 可直接分辨「本輪刷新 artifact」vs「沿用舊 snapshot fail-soft 關閉」
  - regression：`python -m pytest tests/test_hb_parallel_runner.py -q` → **39 passed**
- **本輪 fast heartbeat 完成**：
  - `python scripts/hb_parallel_runner.py --fast` ✅ 完成
  - `Raw=30604 / Features=22022 / Labels=61776`（本輪 `+1 / +1 / +0`）
  - `Global IC 14/30`
  - `TW-IC 28/30`
  - live `CIRCUIT_BREAKER`：recent 50 = `7/50`，距 release 還差 `8` 勝
  - recent drift：primary window=`500`，`distribution_pathology`，`bull=100%`
  - fast summary 現在明確標出 drift/q35/ablation/bull-pocket/leaderboard probe 的 timeout fallback 狀態

---

## 主目標

### 目標 A：保持 breaker-first canonical runtime truth
重點：
- `circuit_breaker_active` 仍是真正 deployment blocker
- `/api/status`、probe、drilldown、Dashboard、Strategy Lab 必須維持同一個 blocker truth
- 所有主要 surface 都必須直接回答「距 release 還差多少」

成功標準：
- recent 50 win rate 回到 `>= 30%`
- 所有主要 surface 一致顯示 release condition 與 remaining gap
- heartbeat summary 能直接回答距 release 還差多少勝

### 目標 B：把 recent canonical distribution pathology 收斂成可執行根因
重點：
- current primary pathology 仍是 recent 500 bull concentration
- 必須把 high win-rate 與 true deployment readiness 分離
- canonical recent-window root-cause 要回到機器可讀證據

成功標準：
- recent pathology 不再是 `distribution_pathology`
- heartbeat / probe / docs 對同一個 pathology root-cause 給出一致結論
- 不再靠 guardrail 長期遮住同一個 unexplained pocket

### 目標 C：把 timeout fallback 從「可觀測」推進到「真正縮時」
重點：
- 本輪已補 summary-level visibility，但 drift / q35 / ablation / leaderboard probe 仍 timeout
- 下一步不是再補報表，而是縮短 runtime 或更嚴格標 stale

成功標準：
- fast mode serial governance 腳本 timeout 數量明顯下降
- 若仍 timeout，summary 會明確標示 freshness/staleness，且 operator 可立即判讀風險
- heartbeat 不再把舊 artifact 誤當成本輪即時事實

### 目標 D：把 Binance execution lane 推進到真實 venue-backed closure
重點：
- 不再只停在 runtime/product surface 完整
- 補 partial-fill / cancel / restart-replay 真實 artifact 鏈

成功標準：
- Binance lane 進入 `venue_backed_path_ready`
- `/api/status`、Dashboard、Strategy Lab 對同一 lane 顯示同一 execution truth
- provenance 不再停在 dry-run / internal-only

---

## 下一步
1. **Breaker release root-cause**：直接追 canonical recent 50/500 tail evidence，驗證從 `7/50` 提升到 release floor 的必要條件
2. **Fast governance de-timeout**：優先處理 `recent_drift_report`、`hb_q35_scaling_audit`、`feature_group_ablation`、`bull_4h_pocket_ablation`、`hb_leaderboard_candidate_probe` 的 runtime
3. **Binance venue artifacts**：補 partial-fill / cancel / restart-replay 真實證據鏈

---

## 成功標準
- `/api/status`、Dashboard、Strategy Lab、probe 對 breaker release math 維持 **同一套 runtime truth**
- fast heartbeat 維持 **cron-safe + machine-readable + fail-soft**，且 serial timeout/fallback freshness 可直接判讀
- recent canonical pathology 被縮小或明確解釋，不再是 deployment blocker 的黑盒子
- execution lane 具備 **真實 venue-backed artifact**，而不只是產品外觀完整
