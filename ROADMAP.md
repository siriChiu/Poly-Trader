# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 13:16 UTC_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- **Leaderboard candidate fast-cache 語義化**
  - `scripts/hb_parallel_runner.py` 不再只用 data file mtime 決定 `hb_leaderboard_candidate_probe` 是否可 reuse
  - 新增 semantic signature 比對：`feature_group_ablation / bull_4h_pocket_ablation / q15_support_audit / live_predict_probe / last_metrics`
  - 同時保留 code dependency freshness：`hb_leaderboard_candidate_probe.py / server/routes/api.py / backtesting/model_leaderboard.py`
- **Regression guard 補齊**
  - `tests/test_hb_parallel_runner.py` 新增兩個案例：
    - 語義相同但 dependency mtime 較新時仍可 reuse
    - 語義漂移時必須拒絕 reuse
  - 驗證：`PYTHONPATH=. pytest tests/test_hb_parallel_runner.py tests/test_hb_leaderboard_candidate_probe.py -q` → **60 passed**
- **Fast heartbeat evidence refresh**
  - `Raw=30614 / Features=22032 / Labels=61791`
  - canonical runtime：`Global IC 14/30`、`TW-IC 28/30`、`CIRCUIT_BREAKER`、recent 50=`11/50`

---

## 主目標

### 目標 A：拿到 fast governance 的真實 cache-hit 證據
重點：
- semantic cache logic 已落地，下一步不是再寫 fallback，而是讓至少一條重型 lane 出現 `cached=True`
- leaderboard candidate lane 是目前最直接的驗證對象
- summary 必須清楚區分 `cached / fresh recompute / timeout fallback`

成功標準：
- 下一輪 fast run 至少一條重型 lane 顯示 `cached=True`
- `serial_results` machine-readable 顯示正確 `cache_reason / artifact_path / artifact_age_seconds`
- operator 能直接判斷該 lane 為真 reuse 而非 timeout fallback

### 目標 B：維持 breaker-first canonical runtime truth
重點：
- `circuit_breaker_active` 仍是真正 deployment blocker
- q15 / q35 / profile governance 只能當背景治理，不可覆蓋 live blocker
- heartbeat 必須直接回答距 release 還差多少勝

成功標準：
- recent 50 win rate 回到 `>= 30%`
- recent 50 至少達 `15/50`
- predictor / drilldown / breaker audit / docs 維持同一 breaker-first truth

### 目標 C：把 recent canonical pathology 轉成可行動根因
重點：
- current primary pathology 仍是 `window=500` bull concentration
- 必須把「局部高 win rate」與 deployment readiness 分離
- 直接追 target-path / feature variance / distinct-count 根因

成功標準：
- recent pathology 不再只是 `distribution_pathology` 黑盒標籤
- heartbeat / probe / docs 對同一 root cause 給出一致結論
- guardrail 不再只是遮住 unexplained pocket

### 目標 D：exact support 只作治理，不覆蓋 live blocker
重點：
- `support_governance_route=no_support_proxy`
- `current_live_structure_bucket_rows=0 / minimum_support_rows=50`
- q15/q35 的研究輸出必須留在 governance lane

成功標準：
- exact support 有累積趨勢或明確停滯證據
- 未達 minimum 前，不再把 q15/q35 patch 寫成 deployment closure

---

## 下一步
1. **刷新 leaderboard candidate artifact**：讓 probe 對齊最新 `server/routes/api.py` / `backtesting/model_leaderboard.py` 後，再重跑 fast heartbeat 驗證 `cached=True`
2. **Tail root cause**：直接拆 canonical recent 50/500 的 target path，回答為何仍停在 `11/50`
3. **Support governance discipline**：維持 q15/q35 只作治理候選，直到 exact support 有實際累積

---

## 成功標準
- fast heartbeat 具備 **至少一條真 cache-hit 的重型治理 lane**
- breaker-first runtime truth 在所有主要 surface 保持一致
- recent canonical pathology 被縮小或明確解釋，不再只是 blocker 黑盒
- q15/q35 exact support 未達標前，不再被誤包裝成 live closure
