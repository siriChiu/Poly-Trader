# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 10:47 UTC_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- **Fast recent-drift cache reuse**
  - `scripts/recent_drift_report.py` 新增 `source_meta={label_rows, latest_label_timestamp}`
  - `scripts/hb_parallel_runner.py` fast mode 會在 canonical 1440m label 簽名未變時直接重用 fresh drift artifact
  - `serial_results` 現在會明確持久化：`cached / cache_reason / cache_details`
  - 這讓 fast heartbeat 不再把「safe fresh reuse」和「timeout fallback 舊 artifact」混在一起
- **Regression lock**
  - `python -m pytest tests/test_hb_parallel_runner.py -q` → **42 passed**
- **Runtime seed evidence**
  - `python scripts/recent_drift_report.py` → **77.7s**，成功重建含 `source_meta` 的 artifact
  - fast serial path 對 `recent_drift_report` 已能回傳 `cached=True`

---

## 主目標

### 目標 A：保持 breaker-first canonical runtime truth
重點：
- `circuit_breaker_active` 仍是真正 deployment blocker
- `/api/status`、probe、drilldown、Dashboard、Strategy Lab 必須維持同一 blocker truth
- 所有主要 surface 都必須直接回答「距 release 還差多少」

成功標準：
- recent 50 win rate 回到 `>= 30%`
- 所有主要 surface 一致顯示 release condition 與 remaining gap
- heartbeat summary 能直接回答距 release 還差多少勝

### 目標 B：把 fast governance de-timeout 從 single-lane 擴成完整策略
重點：
- 本輪只拿下 `recent_drift_report`
- 下一步要把同類 freshness reuse / input-signature gating 擴到：
  - `hb_q35_scaling_audit`
  - `feature_group_ablation`
  - `bull_4h_pocket_ablation`
  - `hb_leaderboard_candidate_probe`

成功標準：
- fast mode serial governance timeout 數量明顯下降
- summary 可區分 `cached`、`fresh recompute`、`timeout fallback`
- operator 不會再把 stale artifact 當成當輪 fresh fact

### 目標 C：把 recent canonical distribution pathology 收斂成可執行根因
重點：
- current primary pathology 仍是 recent 500 bull concentration
- 必須把高 win rate 與真實 deployment readiness 分離
- canonical recent-window root cause 要回到 machine-readable 證據

成功標準：
- recent pathology 不再是 `distribution_pathology`
- heartbeat / probe / docs 對同一 pathology root cause 給出一致結論
- 不再靠 guardrail 長期遮住同一個 unexplained pocket

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
1. **De-timeout 擴張**：把 `recent_drift_report` 的 cache/signature 模式複製到 q35 / ablation / leaderboard probe
2. **Breaker release root cause**：直接追 canonical recent 50/500 tail evidence，驗證從 `7/50` 提升到 release floor 的必要條件
3. **Binance venue artifacts**：補 partial-fill / cancel / restart-replay 真實證據鏈

---

## 成功標準
- `/api/status`、Dashboard、Strategy Lab、probe 對 breaker release math 維持 **同一套 runtime truth**
- fast heartbeat 維持 **cron-safe + machine-readable + fail-soft**，且 serial lanes 能明確分成 `cached / fresh / fallback`
- recent canonical pathology 被縮小或明確解釋，不再是 deployment blocker 的黑盒子
- execution lane 具備 **真實 venue-backed artifact**，而不只是產品外觀完整
