# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **exact-lane toxic blocker propagation 已產品化**：`model/predictor.py` 現在會把 toxic current bucket 升級成 `deployment_blocker=exact_live_lane_<status>`，不再只藏在 `allowed_layers_reason`
- **live runtime closure 文案已補齊**：`scripts/hb_predict_probe.py` 現在會把 toxic exact-lane blocker 轉成明確 `runtime_closure_state / runtime_closure_summary`
- **auto-propose 已能追 toxic current bucket**：`scripts/auto_propose_fixes.py` 新增 `#H_AUTO_CURRENT_BUCKET_TOXICITY` 路徑，避免 exact-supported toxic lane 再被靜默吃掉
- **本輪回歸驗證已通過**：
  - `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_auto_propose_fixes.py -q`
  - `source venv/bin/activate && python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q`
- **fast heartbeat 已重跑驗證最新 truth**：
  - `Raw=30826 / Features=22244 / Labels=61921`
  - `Global IC=14/30 / TW-IC=29/30`
  - current live bucket 重新回到 `CAUTION|structure_quality_caution|q35`
  - latest blocker = `unsupported_exact_live_structure_bucket (0/50)`

---

## 主目標

### 目標 A：收斂 current live q35 exact-support blocker
**目前真相**
- current live bucket = `CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=0 / minimum_support_rows=50`
- `q35_discriminative_redesign_applied=true`
- `entry_quality=0.5556`、`entry_quality_label=C`
- `allowed_layers_raw=1 -> allowed_layers=0`
- `deployment_blocker=unsupported_exact_live_structure_bucket`

**成功標準**
- `current_live_structure_bucket_rows >= 50`
- `live_predict_probe.json` / `live_decision_quality_drilldown.json` / `heartbeat_fast_summary.json` 三處同時移除 `unsupported_exact_live_structure_bucket`
- q35 redesign 若仍 active，必須在 exact-supported current row 上維持同一個 runtime truth，而不是只留 broader governance 分數

### 目標 B：把 recent distribution pathology 從症狀升級成 root cause artifact
**目前真相**
- primary window = recent 500
- `alerts = label_imbalance + regime_concentration + regime_shift`
- `win_rate=0.8440` vs full `0.6375`
- dominant regime = `bull (99.20%)`
- top shifts = `feat_4h_bb_pct_b / feat_4h_bias20 / feat_4h_ma_order`
- new compressed = `feat_dxy / feat_vix`

**成功標準**
- heartbeat 產出可重跑的 root-cause artifact
- artifact 能直接回答 feature variance / distinct-count / target-path 問題，而不是只剩 drift 摘要
- guardrail reason 能直接引用該 artifact，而不是人工轉述

### 目標 C：讓 fast lane heavy governance artifacts 不再 stale-first
**目前真相**
- `feature_group_ablation.py`、`bull_4h_pocket_ablation.py`、`hb_leaderboard_candidate_probe.py` 在 fast lane 仍 timeout 20s
- current summary 仍出現 `snapshot_stale=True`
- governance split 仍需人工判讀

**成功標準**
- fast lane 能在 cron 預算內刷新這三條 artifact，或明確持久化 cache age / stale source / reuse reason
- current-state docs 不再依賴 stale artifact 才能解讀 blocker

---

## 下一步
1. **追 current live q35 exact support**
   - 驗證：`python scripts/hb_predict_probe.py` / `python scripts/live_decision_quality_drilldown.py` / `python scripts/hb_parallel_runner.py --fast` 對 current bucket rows / blocker / layers 三者給出同一個答案
2. **做 recent 500-row pathology root-cause drill-down**
   - 驗證：輸出 artifact 能直接列出 feature variance / distinct-count / target-path 病灶，並被 ISSUES / heartbeat summary 引用
3. **處理 fast-lane heavy artifact timeout**
   - 驗證：fast heartbeat 不再讓 feature-group / bull-pocket / leaderboard probe 只靠 timeout fallback 收尾，或 summary 會清楚顯示 stale age / cache source

---

## 成功標準
- `ISSUES.md` / `ROADMAP.md` / live artifacts 都只描述本輪最新 current-live q35 truth
- live probe、drilldown、fast heartbeat 對 current bucket / blocker / layers 給出同一個答案
- toxic exact-lane blocker 不會再只藏在 `allowed_layers_reason`
- recent pathology 有 root-cause artifact，而不是只剩 drift 指標
- fast lane heavy governance artifacts 的 stale/fallback 風險下降到可操作水位
