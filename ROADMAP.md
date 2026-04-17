# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **generic exact-bucket blocker fallback 已補齊**：`model/predictor.py` 現在會從 exact-scope `no_rows` 診斷直接推導 `unsupported_exact_live_structure_bucket`，不再被較寬 calibration scope 掩蓋
- **q35 runtime closure surface 已產品化**：`scripts/hb_predict_probe.py` / `data/live_predict_probe.json` / `data/live_decision_quality_drilldown.json` 現在會明示 `patch_active_but_execution_blocked` 與對應 `runtime_closure_summary`
- **current-bucket issue governance 已回到 live truth**：`scripts/auto_propose_fixes.py` 不再把 stale governance route 誤寫成「139/50 仍 under minimum」
- 已用以下測試與 runtime 驗證鎖住本輪 patch：
  - `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_live_decision_quality_drilldown.py tests/test_auto_propose_fixes.py tests/test_hb_parallel_runner.py -q`
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast`

---

## 主目標

### 目標 A：收斂 current live q35 exact-support blocker
**目前真相**
- current live bucket = `CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=0`
- `deployment_blocker=unsupported_exact_live_structure_bucket`
- q35 discriminative redesign 可把 `entry_quality` 拉到 `0.6883`，但 runtime 仍被 blocker 壓回 `allowed_layers=0`

**成功標準**
- `current_live_structure_bucket_rows >= 50`
- live probe / drilldown / fast heartbeat 不再回報 `unsupported_exact_live_structure_bucket`
- `allowed_layers_reason` 與 `deployment_blocker` 對 current live row 仍維持同一個 truth

### 目標 B：把 recent distribution pathology 從症狀升級成 root cause
**目前真相**
- primary window = recent 500
- `alerts = label_imbalance + regime_concentration + regime_shift`
- `dominant_regime=bull(99.20%)`
- top shifts = `feat_4h_bb_pct_b / feat_4h_bias20 / feat_4h_ma_order`
- new compressed = `feat_dxy / feat_vix`

**成功標準**
- heartbeat 產出可重跑的 root-cause artifact / patch
- guardrail reason 能直接引用 feature / label / target-path 病灶，而不是只剩 drift 摘要

### 目標 C：讓 fast lane heavy governance artifacts 不再 stale-first
**目前真相**
- `feature_group_ablation.py`、`bull_4h_pocket_ablation.py`、`hb_leaderboard_candidate_probe.py` 在 fast lane 仍 timeout 20s
- current live blocker 已回到 q35 exact-support truth，但 heavy governance 仍有 stale fallback 風險

**成功標準**
- fast lane 能在 cron 預算內刷新這三條 artifact，或至少明確標示 cache/stale age
- current-state summary 不再依賴過期 shrinkage / bull-pocket / leaderboard snapshot 才能解讀 product truth

---

## 下一步
1. **追 current live q35 exact support**
   - 驗證：`python scripts/hb_predict_probe.py` / `python scripts/live_decision_quality_drilldown.py` / fast heartbeat 三者都維持 `deployment_blocker=unsupported_exact_live_structure_bucket` 直到 rows 補滿；補滿後三者必須同步移除 blocker
2. **做 recent pathology root-cause drill-down**
   - 驗證：產出可重跑 artifact，能直接指出 feature variance / distinct-count / target-path 根因，並把結果接進 issue / heartbeat summary
3. **處理 fast lane heavy artifact timeout**
   - 驗證：`hb_parallel_runner.py --fast` 不再讓 feature-group / bull-pocket / leaderboard probe 以 timeout fallback 收尾，或 summary 會清楚顯示 stale age / cache source

---

## 成功標準
- `ISSUES.md` / `ROADMAP.md` / live artifacts 都只描述最新 current q35 blocker，不殘留 q65 舊主線
- live probe、drilldown、fast heartbeat 對 current bucket / blocker / layers 給出同一個答案
- recent pathology 有 root-cause artifact，而不是只剩 drift 指標
- fast lane heavy governance artifacts 的 stale/fallback 風險下降到可操作水位
