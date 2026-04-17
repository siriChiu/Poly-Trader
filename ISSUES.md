# ISSUES.md — Current State Only

_最後更新：2026-04-18 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線
本輪已把 **current live q35 exact-bucket blocker** 拉回 machine-read runtime truth：
- current live bucket = `CAUTION|structure_quality_caution|q35`
- `entry_quality=0.6883`、`entry_quality_label=B`
- `allowed_layers_raw=2 -> allowed_layers=0`
- `deployment_blocker=unsupported_exact_live_structure_bucket`
- `allowed_layers_reason=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket`
- `runtime_closure_state=patch_active_but_execution_blocked`
- `runtime_closure_summary` 已明示：**q35 discriminative redesign 有把 entry quality 拉高，但 execution 仍被 exact-bucket blocker 擋住，不可誤讀成可部署**

本輪已修正的 product/runtime drift：
- `model/predictor.py` 現在會從 exact-scope `no_rows` 診斷直接推導 generic `unsupported_exact_live_structure_bucket`，不再只依賴較寬 calibration scope 或舊 guardrail flag
- `scripts/hb_predict_probe.py` / `data/live_predict_probe.json` / `data/live_decision_quality_drilldown.json` 現在會把 **q35 discriminative redesign active but blocked** 明確寫成 runtime closure，而不是退回 `patch_inactive_or_blocked`
- `scripts/auto_propose_fixes.py` 現在優先信任 live probe 的 current bucket truth，不再把 stale governance route 誤寫成「139/50 仍 under minimum」

已驗證：
- `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_live_decision_quality_drilldown.py tests/test_auto_propose_fixes.py tests/test_hb_parallel_runner.py -q`
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast`

---

## Open Issues

### P0. recent canonical window 仍是 bull-concentrated distribution pathology
**現況**
- primary window = recent 500
- `win_rate=0.8400`、`avg_quality=0.3716`、`avg_drawdown_penalty=0.1460`
- alerts = `label_imbalance + regime_concentration + regime_shift`
- dominant regime = `bull (99.20%)`
- sibling-window top shifts 仍集中在 `feat_4h_bb_pct_b / feat_4h_bias20 / feat_4h_ma_order`
- new compressed = `feat_dxy / feat_vix`

**風險**
- 若只看 recent 高 win rate，會把病態 bull pocket 誤當成健康 closure
- calibration / governance 容易被病態 slice 稀釋，造成假樂觀 runtime expectation

**下一步**
- 直接做 recent canonical rows 的 feature variance / distinct-count / target-path root cause artifact
- 在根因被 patch 前，維持 decision-quality guardrails

### P1. current live q35 exact support 仍為 0/50
**現況**
- current live bucket = `CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=0`
- `minimum_support_rows=50`
- runtime 已明示 `deployment_blocker=unsupported_exact_live_structure_bucket`
- q35 discriminative redesign 雖能把 `entry_quality` 拉到 `0.6883`，但 **raw capacity 不能當 deployment closure**

**風險**
- 若只看 `entry_quality` 或 raw layers，operator 會誤判為已可放行
- broader / proxy rows 仍可能被誤讀成 exact live lane 支持

**下一步**
- 以 current live q35 bucket 為主累積 exact support
- 持續驗證 probe / drilldown / heartbeat summary 都保留同一個 blocker truth

### P1. fast lane heavy artifacts 仍 timeout 20s
**現況**
- `feature_group_ablation.py`
- `bull_4h_pocket_ablation.py`
- `hb_leaderboard_candidate_probe.py`
- 以上三條在 fast lane 仍走 timeout fallback

**風險**
- shrinkage / bull pocket / leaderboard governance 仍可能引用 stale snapshot
- current-state docs 雖已回到 q35 truth，但 heavy artifact 仍可能落後 current runtime

**下一步**
- 縮短或拆分 heavy artifact 的 fast-lane path
- 至少把 cache age / stale state 更明確寫入 summary

### P1. model stability / profile split 仍未收斂
**現況**
- `cv_accuracy=0.6978`
- `cv_std=0.1161`
- `cv_worst=0.5445`
- leaderboard global winner 與 support-aware production path 仍是雙角色治理

**風險**
- 容易把 dual-role governance 誤寫成簡單 parity drift
- heavy artifact 若 stale，會讓 profile split 更難解釋

**下一步**
- 維持「global ranking vs support-aware production」雙角色語義
- 在 q35 exact support 未補滿前，不把 profile split 當主 blocker

### P2. sparse-source blockers 仍在背景
**現況**
- blocked features = 8
- 最硬 blocker 仍是 `fin_netflow` 的 `auth_missing`

**風險**
- 會持續限制 research overlay / archive-window completeness
- 但目前不是 current-live deployment 的第一順位 blocker

**下一步**
- defer，等 q35 current-live blocker 與 recent pathology 先收斂

---

## Not Issues
- `q65` current-live blocker 敘事：**不是本輪真相**；本輪 current live row 已回到 `CAUTION|structure_quality_caution|q35`
- `139/50 仍 under minimum`：**不是最新真相**；這是本輪修掉的 stale issue-generation bug，不可再寫進 current-state docs
- `patch_inactive_or_blocked` on active q35 redesign：**已修正**；probe / drilldown 現在會明示 patch active but execution blocked

---

## Current Priority
1. **做 recent distribution pathology 的 root-cause artifact / patch，不再只停在 drift 摘要**
2. **累積 current live q35 exact support，直到 `unsupported_exact_live_structure_bucket` 從 runtime surface 消失**
3. **處理 fast lane heavy artifact timeout，避免 governance 再回退成 stale-first**
