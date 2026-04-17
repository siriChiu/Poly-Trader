# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 11:13 UTC_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- **Fast governance cache contract 擴張**
  - `hb_parallel_runner.py` 新增通用 dependency-based artifact cache helper
  - fast mode 新增 cache reuse lane：
    - `feature_group_ablation`
    - `bull_4h_pocket_ablation`
    - `hb_q15_support_audit`
    - `hb_q15_bucket_root_cause`
    - `hb_q15_boundary_replay`
  - leaderboard candidate cache 已收斂到同一套 reusable contract
- **Regression lock**
  - `python -m pytest tests/test_hb_parallel_runner.py -q` → **45 passed**
- **Runtime evidence refresh**
  - fast heartbeat 目前實測：`Raw=30607 / Features=22025 / Labels=61780`
  - canonical runtime：`Global IC 14/30`、`TW-IC 28/30`、`CIRCUIT_BREAKER`、recent 50=`8/50`

---

## 主目標

### 目標 A：把 fast governance de-timeout 從「有程式碼」推進到「真的命中 cache」
重點：
- 本輪已把 cache lane 擴到 feature ablation / bull pocket / q15 lanes
- 下一步不是再加更多 timeout fallback，而是要讓這些 lane 真正重用 fresh artifact
- 必須把「fresh reuse」和「timeout fallback 舊 artifact」明確區分

成功標準：
- 下一輪 fast run 至少有一條新 governance lane 顯示 `cached=True`
- summary 可直接區分 `cached / fresh recompute / timeout fallback`
- operator 不會再把 stale artifact 當成當輪 fresh fact

### 目標 B：保持 breaker-first canonical runtime truth
重點：
- `circuit_breaker_active` 仍是真正 deployment blocker
- `/api/status`、probe、drilldown、Dashboard、Strategy Lab 必須維持同一 blocker truth
- heartbeat 必須直接回答距 release 還差多少勝

成功標準：
- recent 50 win rate 回到 `>= 30%`
- 所有主要 surface 一致顯示 release condition 與 remaining gap
- heartbeat summary 能直接回答 `8/50 → 15/50` 的剩餘差距

### 目標 C：把 recent canonical distribution pathology 收斂成可執行根因
重點：
- current primary pathology 仍是 recent 500 bull concentration
- 必須把高 win rate 與真實 deployment readiness 分離
- canonical recent-window root cause 要回到 machine-readable 證據

成功標準：
- recent pathology 不再只是 `distribution_pathology` 黑盒標籤
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
1. **Fresh baseline + cache hit**：先重建一輪 fresh governance artifact，再驗證 fast mode 的新 cache lane 至少命中一次
2. **Semantic freshness gating**：把 `live_predict_probe` / `live_decision_quality_drilldown` 從單純檔案更新，升級成基於 feature timestamp 的 semantic cache
3. **Breaker tail root cause**：直接追 canonical recent 50/500 的 target-path / feature variance 根因

---

## 成功標準
- fast heartbeat 具備 **cron-safe + machine-readable + actual cache hit evidence**
- `/api/status`、Dashboard、Strategy Lab、probe 對 breaker release math 維持 **同一套 runtime truth**
- recent canonical pathology 被縮小或明確解釋，不再是 deployment blocker 黑盒
- execution lane 具備 **真實 venue-backed artifact**，而不只是產品外觀完整
