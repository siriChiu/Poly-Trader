# ISSUES.md — Current State Only

_最後更新：2026-04-18 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線
本輪 heartbeat 先把 **exact-lane toxic sub-bucket blocker propagation** 補齊成 machine-read runtime contract：
- `model/predictor.py` 現在會把 `decision_quality_exact_live_lane_toxicity_applied=true` 的 current-bucket 毒性狀態升級成 `deployment_blocker=exact_live_lane_<status>`
- `scripts/hb_predict_probe.py` 現在會把這類 blocker 轉成明確 `runtime_closure_state / runtime_closure_summary`，不再只藏在 `allowed_layers_reason`
- `scripts/auto_propose_fixes.py` 現在會在 live bucket 已 exact-supported 但成為 toxic current bucket 時，自動開出 `#H_AUTO_CURRENT_BUCKET_TOXICITY`
- 已用 regression tests 鎖住：
  - `source venv/bin/activate && python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_auto_propose_fixes.py -q`
  - `source venv/bin/activate && python -m pytest tests/test_live_decision_quality_drilldown.py tests/test_hb_parallel_runner.py -q`

**但本輪最新 runtime 真相仍是 support blocker，而不是 toxic exact lane blocker：**
- current live bucket = `CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=0 / minimum_support_rows=50`
- live probe = `entry_quality=0.5556`、`entry_quality_label=C`
- `q35_discriminative_redesign_applied=true`
- `allowed_layers_raw=1 -> allowed_layers=0`
- `deployment_blocker=unsupported_exact_live_structure_bucket`
- 代表：**q35 redesign 已能把當前 row 拉過 trade floor，但 exact support 仍是 deployment closure 的第一順位 blocker**

---

## Open Issues

### P0. current live q35 exact support 仍是 deployment blocker
**現況**
- fast heartbeat（本輪最新）顯示 `current_live_structure_bucket_rows=0/50`
- live probe chosen scope 回到 `regime_label`，exact live lane diagnostics 對 current q35 row 為 `no_rows`
- broader scope 仍可看到 `expected_win_rate=0.6633 / expected_quality=0.2800`，但這只是 governance 參考，不是 current-live exact support
- `q35_discriminative_redesign_applied=true`，`entry_quality=0.5556`、`raw layers=1`，最終仍被 `unsupported_exact_live_structure_bucket` 壓回 `allowed_layers=0`

**風險**
- 容易把「已跨過 trade floor」誤讀成「已可部署」
- 若 probe / drilldown / docs 對 blocker 語義不一致，Dashboard / Strategy Lab 會再次誤導 operator

**下一步**
- 以 current q35 exact bucket 為唯一 deployment gate，累積到 `>=50 rows`
- 驗證 `live_predict_probe.json`、`live_decision_quality_drilldown.json`、`heartbeat_fast_summary.json` 三處同時移除 `unsupported_exact_live_structure_bucket`
- 在 rows 未補滿前，明確把 q35 redesign 視為 **governance progress**，不是 deployment closure

### P0. recent canonical 500-row distribution pathology 仍未收斂
**現況**
- primary window = recent 500
- `alerts = label_imbalance + regime_concentration + regime_shift`
- `win_rate=0.8440` vs full `0.6375`（`Δ=+0.2065`）
- dominant regime = `bull (99.20%)`
- top shifts = `feat_4h_bb_pct_b / feat_4h_bias20 / feat_4h_ma_order`
- new compressed = `feat_dxy / feat_vix`
- adverse streak evidence 仍存在：`259x1`

**風險**
- calibration / governance 容易被 bull-only pathology 汙染
- 會讓 broader scope 的高分數看起來像可部署 closure

**下一步**
- 直接產出 recent canonical rows 的 feature variance / distinct-count / target-path root-cause artifact
- 在根因落地前，維持 decision-quality guardrails，不把 broader lane 當 current-live truth

### P1. fast lane heavy governance artifacts 仍 timeout 20s
**現況**
- `feature_group_ablation.py` timeout fallback
- `bull_4h_pocket_ablation.py` timeout fallback
- `hb_leaderboard_candidate_probe.py` timeout fallback
- 本輪 fast summary 仍顯示 `snapshot_stale=True`

**風險**
- shrinkage / bull-pocket / leaderboard governance 可能落回 stale-first
- current-state docs 仍需人工判讀，而不是 runner 自己保持乾淨一致

**下一步**
- 縮短 heavy artifact 的 fast-lane path，或先做更輕量的 alignment refresh
- 至少把 cache age / stale source 更明確地灌進 summary 與 docs

### P1. model stability / profile split 仍未收斂
**現況**
- `train_accuracy=0.6457`
- `cv_accuracy=0.6978`
- `cv_std=0.1161`
- `cv_worst=0.5445`
- leaderboard global winner 與 support-aware production path 仍是雙角色治理

**風險**
- 容易把 healthy dual-role governance 誤寫成 parity drift
- heavy artifact timeout 會讓 profile split 更難 machine-read 解釋

**下一步**
- 保持 `global ranking vs support-aware production` 雙角色語義
- 在 q35 current-live support 補滿前，不把 profile split 升級成第一順位 blocker

### P2. sparse-source blockers 仍在背景
**現況**
- blocked features = 8
- 最硬 blocker 仍是 `fin_netflow` 的 `auth_missing`

**風險**
- 限制 research overlay / archive-window completeness
- 但目前不是 current-live deployment 的第一順位 blocker

**下一步**
- defer，等 q35 current-live blocker 與 recent pathology 先收斂

---

## Not Issues
- `q15` exact support：**不是本輪 current-live closure**；q15 lane 雖 exact-supported，但當前 live row 仍是 `q35`
- `q35 discriminative redesign`：**不是 deployment closure**；本輪只是把 `entry_quality` 拉到 0.5556，exact support 仍為 0/50
- `exact-lane toxic sub-bucket blocker propagation`：**本輪已修補 contract**；未來 exact-supported toxic lane 不會再只藏在 `allowed_layers_reason`

---

## Current Priority
1. **補 current live q35 exact support 到 50 rows，並讓 blocker 同步從 probe / drilldown / fast heartbeat 消失**
2. **把 recent 500-row pathology 從 drift 摘要升級成 root-cause artifact**
3. **處理 fast-lane heavy artifact timeout，避免 stale-first governance 再回來**
