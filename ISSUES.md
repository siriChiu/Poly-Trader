# ISSUES.md — Current State Only

_最後更新：2026-04-16 09:33 UTC_

只保留目前仍有效的問題；不保留歷史敘事。

---

## Step 0.5 承接（把上輪結論當本輪輸入）
- 上輪 carry-forward 主軸：`feat_4h_bias20 recent-window unexpected compression root cause`、`q15 exact support accumulation / replay`、`keep q35 reference-only until current live returns to q35`。
- 本輪逐條對照結果：
  1. **`feat_4h_bias20` 仍是 primary recent blocker**：`recent_drift_report.py` 重新確認 sibling-window `new_compressed = feat_4h_bias20`，本輪尚未完成 root-cause patch，仍停留在待拆解狀態。
  2. **q15 support accumulation 已從口頭要求變成 machine-readable artifact**：本輪補上 `scripts/hb_q15_support_audit.py` 的 `support_progress` contract，能直接輸出 `status / gap_to_minimum / previous_rows / delta_vs_previous / stagnant_run_count / escalate_to_blocker / history`。但目前 current q15 exact rows 仍只有 **4 / 50**，`support_progress.status = no_recent_comparable_history`，代表還沒有足夠同路徑 heartbeat 歷史可判定「累積」或「停滯」。
  3. **q35 仍是 reference-only，不可搶回主線**：`hb_q35_scaling_audit.py` 相關舊敘事仍不能覆蓋 current q15 blocker；本輪沒有把 q35 重新升級成 current-live closure。
  4. **q15 replay 路徑更清楚，但仍未進入 deployable**：`hb_q15_bucket_root_cause.py` 指向 `same_lane_neighbor_bucket_dominates`，候選 patch feature 為 `feat_4h_bb_pct_b`；`hb_q15_boundary_replay.py` 仍回報 `boundary_replay_not_applicable`，表示現階段不能把 boundary replay 當 deployment 解法。

---

## 系統現況
- 本輪最新 DB：**Raw / Features / Labels = 30524 / 16750 / 43750**
- 最新時間：
  - Raw：`2026-04-16 08:35:24.573669`
  - Features：`2026-04-16 08:35:24.573669`
  - Labels：`2026-04-16 01:43:50.141947`
  - Canonical 1440m labels：`2026-04-15 05:53:35.506756`
- canonical 1440m：**12709 rows / simulated_pyramid_win = 0.6470**
- 全域 IC：**17 / 30 pass**
- TW-IC：**26 / 30 pass**
- regime-aware IC：**Bear 5/8、Bull 6/8、Chop 4/8**
- recent drift primary window：**100**
  - alerts = `constant_target`, `regime_concentration`, `regime_shift`
  - interpretation = `distribution_pathology`
  - `wins = 100 / losses = 0`
  - `dominant_regime = bull (100%)`
  - sibling-window `new_compressed = feat_4h_bias20`
- current live probe：
  - regime / gate / bucket：**bull / CAUTION / q15**
  - `entry_quality = 0.4326`
  - `entry_quality_label = D`
  - `allowed_layers_raw = 0`
  - `allowed_layers = 0`
  - `deployment_blocker = under_minimum_exact_live_structure_bucket`
  - exact current-bucket rows = **4**
- q15 support audit：
  - `support_route.verdict = exact_bucket_present_but_below_minimum`
  - `support_progress.status = no_recent_comparable_history`
  - `support_progress.current_rows / minimum = 4 / 50`
  - `support_progress.gap_to_minimum = 46`
  - `floor_cross_legality.verdict = math_cross_possible_but_illegal_without_exact_support`
  - `best_single_component = feat_4h_bias50`
  - `best_single_component_required_score_delta = 0.3913`
  - `component_experiment.verdict = reference_only_until_exact_support_ready`
- q15 root-cause artifact：
  - `verdict = same_lane_neighbor_bucket_dominates`
  - `candidate_patch_type = structure_component_scoring`
  - `candidate_patch_feature = feat_4h_bb_pct_b`
  - `gap_to_q35_boundary = 0.0476`
  - `near_boundary_rows = 21`
- q15 boundary replay：`boundary_replay_not_applicable`
- comprehensive test：**6/6 PASS**

---

## Step 1 事實分類

### 已改善
1. **q15 support blocker 終於有進度語義**：本輪不是只重述「rows=4」。`hb_q15_support_audit.py` 現在會持久化 `support_progress`，能直接分辨 `accumulating / stalled_under_minimum / regressed_under_minimum / exact_supported / no_recent_comparable_history`。
2. **q15 support contract 已落到測試**：`tests/test_q15_support_audit.py` 新增 support-progress 回歸，驗證停滯狀態會正確升級 `stalled_under_minimum + escalate_to_blocker`。
3. **文件 contract 已同步**：`ARCHITECTURE.md` 已把 q15 support audit 的 `support_progress` 納入 machine-read contract，避免下一輪又回到只看 rows 的報告式心跳。
4. **閉環驗證完整**：
   - `python -m pytest tests/test_q15_support_audit.py -q` → **7 passed**
   - `python scripts/recent_drift_report.py`
   - `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
   - `python scripts/live_decision_quality_drilldown.py`
   - `python scripts/hb_q15_support_audit.py`
   - `python scripts/hb_q15_bucket_root_cause.py`
   - `python scripts/hb_q15_boundary_replay.py`
   - `python scripts/full_ic.py`
   - `python scripts/regime_aware_ic.py`
   - `python tests/comprehensive_test.py` → **6/6 PASS**

### 惡化
1. **recent canonical pathology 沒有解除**：recent 100 仍是 `100x1 bull pocket`，`new_compressed` 仍停在 `feat_4h_bias20`，代表主病灶還沒被 patch 掉。
2. **current live blocker 仍未進入累積態**：q15 exact rows 雖存在，但 `support_progress` 還是 `no_recent_comparable_history`，代表 heartbeat summary 尚未形成可比較的同 bucket / 同 route 歷史鏈。

### 卡住不動
1. **q15 exact support 仍卡在 deployment-grade minimum 之外**：當前只有 **4 / 50**，`feat_4h_bias50` 雖然在數學上可補 floor gap，但依 contract 仍屬非法放行。
2. **boundary replay 仍不能用**：`boundary_replay_not_applicable` 表示本輪不能用 bucket boundary 重標路徑掩蓋 exact support 缺口。
3. **dual-role governance 仍不是本輪主線**：current blocker 仍是 `feat_4h_bias20` + q15 exact support，不應回退到 q35/leaderboard 敘事。

---

## Open Issues

### P0. `feat_4h_bias20` 仍是 recent bull pocket 的主病灶
**現象**
- `recent_drift_report.py` 仍顯示 recent 100 = `100x1 bull pocket`
- sibling-window `new_compressed = feat_4h_bias20`
- `feat_4h_bias50` 已不是 primary blocker，但 `feat_4h_bias20` 還沒有 root-cause patch

**影響**
- recent calibration 與 drift triage 仍被 bull pocket pathology 污染
- 若下一輪仍只重跑 artifact 而不拆 `feat_4h_bias20`，就是報告式空轉

**本輪證據**
- `python scripts/recent_drift_report.py`
- `data/recent_drift_report.json`

**下一步**
- 直接拆 `feat_4h_bias20`：先判斷是 4H projection 過平滑、短週期對齊問題，還是 underlying market-state 真壓縮

### P1. q15 exact support 仍只有 4/50；但本輪已補齊 support-progress contract
**現象**
- current live = `bull / CAUTION / q15`
- `deployment_blocker = under_minimum_exact_live_structure_bucket`
- `support_route.verdict = exact_bucket_present_but_below_minimum`
- `support_progress.status = no_recent_comparable_history`
- `gap_to_minimum = 46`

**影響**
- runtime 仍必須維持 `allowed_layers = 0`
- 雖然 blocker 沒解除，但現在至少能 machine-read support 是否在累積、停滯或回退；下輪不能再只寫「rows 不足」

**本輪 patch / 證據**
- `scripts/hb_q15_support_audit.py`：新增 `support_progress` 歷史/狀態輸出
- `tests/test_q15_support_audit.py`：新增 q15 support-progress 回歸測試
- `ARCHITECTURE.md`：同步新增 q15 support-progress contract
- 驗證：`python -m pytest tests/test_q15_support_audit.py -q` → **7 passed**

**下一步**
- 先把 `q15_support_audit` 訊號帶進 heartbeat summary，讓後續 run 能形成同 bucket / 同 route 歷史鏈
- 若下輪 rows 仍停在 4 且 status 轉成 `stalled_under_minimum`，直接升級成 blocker，不得再寫成 generic support 不足

### P1. q15 root cause 已指向同 lane neighbor dominance，但仍只屬 reference-only
**現象**
- `hb_q15_bucket_root_cause.py`：`same_lane_neighbor_bucket_dominates`
- candidate patch = `feat_4h_bb_pct_b`
- `gap_to_q35_boundary = 0.0476`
- `near_boundary_rows = 21`
- `hb_q15_boundary_replay.py`：`boundary_replay_not_applicable`

**影響**
- 當前最小 patch 候選已縮到 `feat_4h_bb_pct_b`，但仍不能拿來繞過 exact support minimum
- 代表下一輪該做的是 q15 同 lane neighbor 對照 / component 差異驗證，而不是回到 q35 formula review

**下一步**
- 比較 current row 與 dominant q35 neighbor bucket 的 `feat_4h_bb_pct_b / feat_4h_bias50 / feat_4h_dist_bb_lower / feat_4h_dist_swing_low` 差值
- 先做最小 counterfactual，驗證是否只是 structure component scoring 就能把 q15 row 推向可比較 lane

### P2. q35 保持 reference-only，不得重回 current-live 主敘事
**現象**
- current live bucket 仍是 q15
- q35 相關 audit 只可保留 calibration / reference value

**影響**
- 若下輪重新把 q35 當 current blocker，文件又會失真

**下一步**
- 只有在 current live row 回到 q35 時，才重啟 q35 deployment closure

---

## Not Issues
- **`feat_4h_bias50` 仍是 primary recent blocker**：不是。它已退居 q15 floor-cross 的單點 component 候選，recent pathology 主病灶仍是 `feat_4h_bias20`。
- **`feat_4h_bias50` 單點可跨 floor = 現在就能放行**：不是。`floor_cross_legality` 明確是 `math_cross_possible_but_illegal_without_exact_support`。
- **boundary replay 已可當 current-live closure**：不是。`boundary_replay_not_applicable`。
- **q35 應回來接管本輪主線**：不是。current live 仍在 q15。

---

## Current Priority
1. **直接處理 `feat_4h_bias20` recent-window root cause**
2. **讓 q15 support-progress 正式進入 heartbeat summary 歷史鏈，並持續監看 4/50 → 是否累積 / 停滯 / 回退**
3. **沿 q15 neighbor-dominance 線追最小 component patch（優先 `feat_4h_bb_pct_b`），但不得越權解除 exact-support blocker**

---

## Next Gate Input
- **Next focus**：`feat_4h_bias20 recent-window unexpected compression root cause`、`q15 support_progress history + accumulation`、`q15 same-lane neighbor dominance minimal component counterfactual`
- **Success gate**：
  - `recent_drift_report.json` 的 sibling-window `new_compressed` 不再是 `feat_4h_bias20`，或至少留下 1 個針對 `feat_4h_bias20` 的 root-cause patch + verify
  - `q15_support_audit.json` 的 `support_progress.status` 不再只是 `no_recent_comparable_history`，至少能進入 `accumulating / stalled_under_minimum / regressed_under_minimum` 之一
  - current q15 exact rows 明確增加，或至少 heartbeat summary 已保留可比較的 support-progress 歷史鏈
  - 若做 q15 component counterfactual，必須明確證明它仍是 **reference-only until exact support ready**
- **Fallback if fail**：
  - 若 `feat_4h_bias20` 仍無 patch，下輪只能做這件事，不再接受重跑式 heartbeat
  - 若 q15 support-progress 仍未進入 summary 歷史鏈，下輪把這件事升級成 heartbeat governance blocker
  - 若 current live bucket 再切換，先重寫 current-state docs，再決定是否回到 q35 或其他 lane
- **Carry-forward input for next heartbeat**：
  1. 先讀最新 `data/recent_drift_report.json`，確認 sibling-window `new_compressed` 是否仍為 `feat_4h_bias20`。
  2. 再讀最新 `data/q15_support_audit.json`，逐條檢查：
     - `support_progress.status`
     - `support_progress.current_rows`
     - `support_progress.minimum_support_rows`
     - `support_progress.delta_vs_previous`
     - `support_progress.stagnant_run_count`
     - `support_progress.escalate_to_blocker`
  3. 若 q15 rows 仍低於 50，禁止把 `feat_4h_bias50` 單點 floor-cross 敘事寫成可 deploy；必須保持 `reference_only_until_exact_support_ready`。
  4. 再讀 `data/q15_bucket_root_cause.json`；若 verdict 仍是 `same_lane_neighbor_bucket_dominates`，下一輪只能做 current row vs dominant q35 neighbor 的最小 component counterfactual，優先檢查 `feat_4h_bb_pct_b`。
