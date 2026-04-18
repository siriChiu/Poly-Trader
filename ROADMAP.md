# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 12:55 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat ablation fail-soft 已產品化**：
  - `scripts/hb_parallel_runner.py` 新增 **bounded label-drift cache reuse**
  - `feature_group_ablation` 可在 1440m canonical labels 只小幅 drift（<=12 rows / <=6h）時安全 reuse
  - `bull_4h_pocket_ablation` 除了 bounded label drift，還會檢查 **current live structure bucket / blocker semantic signature**；在 `exact bucket rows=0` 時，不再因 `entry_quality_label` 的小幅跳動被迫重跑
- **bull pocket artifact 現在持久化 `source_meta`**，讓 fast lane 能機器可讀地判斷 artifact 是否仍可安全沿用
- **回歸驗證已通過**：
  - `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py tests/test_bull_4h_pocket_ablation.py -q`
  - 結果：`55 passed`
- **本輪 runtime 證據**：
  - `data/heartbeat_fast_summary.json` 顯示：
    - `feature_group_ablation.cached=true`
    - `cache_reason=bounded_label_drift_feature_group_ablation_artifact_reused`
    - `bull_4h_pocket_ablation.cached=true`
    - `cache_reason=bounded_label_drift_bull_4h_pocket_artifact_reused`
  - fast lane 已不再被 45s / 20s ablation timeout 卡住

---

## 主目標

### 目標 A：解除 current live q35 exact-support deployment blocker
**目前真相**
- current live bucket = `CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=0 / minimum_support_rows=50`
- `deployment_blocker=unsupported_exact_live_structure_bucket`
- q35 discriminative redesign 已把 raw layers 拉高，但最終 execution 仍被 blocker 壓回 `allowed_layers=0`

**成功標準**
- `current_live_structure_bucket_rows >= 50`
- `live_predict_probe.json` / `live_decision_quality_drilldown.json` / `heartbeat_fast_summary.json` 三處同時移除 exact-support blocker
- current-live truth 仍保持 blocker-first，而不是只剩 broader governance 分數

### 目標 B：把 recent 500-row pathology 變成可執行 root-cause patch
**目前真相**
- recent 500 = `distribution_pathology`
- dominant regime = `bull (99.20%)`
- `win_rate=0.8560` vs full `0.6381`
- top shifts = `feat_4h_bb_pct_b / feat_4h_vol_ratio / feat_eye`
- new compressed = `feat_atr_pct / feat_vix`

**成功標準**
- heartbeat 產出可重跑的 root-cause artifact / patch，不只剩 drift 摘要
- artifact 能直接回答 variance / distinct-count / target-path 病灶
- guardrail reason 能直接引用該 artifact，而不是人工轉述

### 目標 C：修掉 leaderboard stale snapshot 依賴
**目前真相**
- candidate probe 可讀，但 `leaderboard_payload_source` 仍是 `latest_persisted_snapshot`
- `leaderboard_payload_cache_error = CallbackContainer/xgboost circular import`
- ablation fast-lane freshness 已不是主 blocker；剩下的是 leaderboard refresh path 本身

**成功標準**
- `model_leaderboard_cache.json` 能 fresh refresh
- `leaderboard_payload_source` 回到 fresh cache / current snapshot
- summary / docs 能 machine-read fresh/stale state，而不是靠人工猜測

---

## 下一步
1. **追 current q35 exact support 0→50**
   - 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、`python scripts/hb_parallel_runner.py --fast` 三處對 blocker / minimum / gap / route 完全一致
2. **把 recent 500 pathology 升級成 root-cause artifact / patch**
   - 驗證：artifact 直接列出 variance / distinct-count / target-path 病灶，並被 ISSUES / heartbeat summary 直接引用
3. **修掉 leaderboard cache refresh stale-first**
   - 驗證：`hb_leaderboard_candidate_probe.py` 的 `leaderboard_payload_source` 不再是 `latest_persisted_snapshot`

---

## 成功標準
- fast lane 內的 feature-group / bull-pocket governance 已能穩定 bounded-reuse，不再是 cron blocker
- q35 exact support 不再是 current-live deployment blocker
- recent pathology 有 root cause，而不是只有 drift 指標
- leaderboard 治理回到 fresh cache / current snapshot，而不是 stale snapshot fallback
