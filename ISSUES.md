# ISSUES.md — Current State Only

_最後更新：2026-04-16 11:36 UTC_

只保留目前仍有效的問題；不保留歷史敘事。

---

## Step 0.5 承接（把上輪結論當本輪輸入）
- 上輪 carry-forward 主軸：`feat_4h_bb_pct_b minimal component counterfactual`、`q15 support accumulation 4→?`、`keep bias50/q35 reference-only until exact support ready`。
- 本輪逐條對照結果：
  1. **已完成 `feat_4h_bb_pct_b` 最小反事實**：`scripts/hb_q15_boundary_replay.py` 現在明確輸出 `verdict = same_lane_counterfactual_bucket_proxy_only`，證明把 `feat_4h_bb_pct_b` 從 `0.3974 → 0.7745` 只會把 current row 從 `q15 → q35`，但 `entry_quality` 只從 `0.4227 → 0.4547`，`allowed_layers` 仍是 `0`。
  2. **q15 support accumulation 沒有退步，但仍未達 deployable**：`support_progress.current_rows = 4`、`minimum_support_rows = 50`、`gap_to_minimum = 46`、`status = accumulating`。
  3. **bias50 / q35 仍不能接管成可部署主敘事**：`floor_cross_legality.verdict = math_cross_possible_but_illegal_without_exact_support`；`feat_4h_bias50` 仍是唯一可單點跨 floor 的 component，但 support 未達標前只能是 reference-only。
  4. **本輪已把上輪模糊結論收斂成 machine-readable 治理語義**：不再只留下 `boundary_replay_not_applicable`；現在 artifact 會直接告訴下一輪：`feat_4h_bb_pct_b` 是 bucket proxy，不是 deployable floor fix。

---

## 系統現況
- 本輪最新 DB：**Raw / Features / Labels = 30527 / 18664 / 43750**
- 最新時間：
  - Raw：`2026-04-16 10:49:08.303092`
  - Features：`2026-04-16 10:49:08.303092`
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
  - sibling-window `new_compressed = feat_4h_bb_pct_b`
- current live probe：
  - regime / gate / bucket：**bull / CAUTION / q15**
  - `entry_quality = 0.4227`
  - `entry_quality_label = D`
  - `allowed_layers_raw = 0`
  - `allowed_layers = 0`
  - `deployment_blocker = under_minimum_exact_live_structure_bucket`
  - exact current-bucket rows = **4**
- q15 support audit：
  - `support_route.verdict = exact_bucket_present_but_below_minimum`
  - `support_progress.status = accumulating`
  - `support_progress.current_rows / minimum = 4 / 50`
  - `support_progress.delta_vs_previous = +4`
  - `support_progress.gap_to_minimum = 46`
  - `floor_cross_legality.verdict = math_cross_possible_but_illegal_without_exact_support`
  - `best_single_component = feat_4h_bias50`
  - `best_single_component_required_score_delta = 0.4243`
  - `component_experiment.verdict = reference_only_until_exact_support_ready`
- q15 root-cause artifact：
  - `verdict = same_lane_neighbor_bucket_dominates`
  - `candidate_patch_type = structure_component_scoring`
  - `candidate_patch_feature = feat_4h_bb_pct_b`
  - `gap_to_q35_boundary = 0.1282`
  - `dominant_neighbor_bucket = CAUTION|structure_quality_caution|q35`
  - `near_boundary_rows = 58`
- q15 boundary replay / 最小反事實：
  - `verdict = same_lane_counterfactual_bucket_proxy_only`
  - `component_counterfactual.feature = feat_4h_bb_pct_b`
  - `raw_delta_to_cross_q35 = +0.3771`
  - `entry_quality_after = 0.4547`
  - `trade_floor_gap_after = -0.0953`
  - `allowed_layers_after = 0`
- comprehensive test：**6/6 PASS**
- targeted regression：`python -m pytest tests/test_q15_boundary_replay.py -q` → **3 passed**

---

## Step 1 事實分類

### 已改善
1. **上輪要求的 `feat_4h_bb_pct_b` 最小 counterfactual 已真正落地**：現在不再只是口頭說「應該要驗」，而是有 machine-readable artifact 直接證明它只能 rebucket、不能過 floor。
2. **q15 boundary artifact 的治理語義更精確**：`scripts/hb_q15_boundary_replay.py` 已新增 `same_lane_counterfactual_bucket_proxy_only`，避免同一份 JSON 一邊說 boundary 不適用、一邊又埋著 counterfactual 結果，造成下一輪讀錯主線。
3. **測試與文件已同步新語義**：
   - `tests/test_q15_boundary_replay.py` 新增 same-lane bucket-proxy regression
   - `ARCHITECTURE.md` 已同步 q15 boundary-replay contract
4. **驗證閉環完整**：
   - `python scripts/recent_drift_report.py`
   - `python scripts/full_ic.py`
   - `python scripts/regime_aware_ic.py`
   - `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
   - `python scripts/live_decision_quality_drilldown.py`
   - `python scripts/hb_q15_support_audit.py`
   - `python scripts/hb_q15_bucket_root_cause.py`
   - `python scripts/hb_q15_boundary_replay.py`
   - `python -m pytest tests/test_q15_boundary_replay.py -q` → **3 passed**
   - `python tests/comprehensive_test.py` → **6/6 PASS**

### 惡化
1. **recent canonical pathology 仍未解除**：recent 100 仍是 `100x1 bull pocket`，primary interpretation 仍是 `distribution_pathology`。
2. **當前 q15 runtime blocker 沒有因 bb_pct_b counterfactual 而鬆動**：即使最小 counterfactual 成功 rebucket，`entry_quality_after` 仍只有 `0.4547`，代表 blocker 已從「未知結構差距」進一步收斂成「trade-floor component + exact-support」雙重問題。

### 卡住不動
1. **q15 exact support 仍遠低於 deployment minimum**：當前仍只有 **4 / 50**，runtime 必須維持 `allowed_layers = 0`。
2. **bias50 仍是唯一可單點跨 floor 的 component，但法律上不可放行**：support 未達標前，這仍只能是 reference-only 研究結果。
3. **q35 仍是 same-lane reference bucket，不是 current-live closure**：current live row 仍停在 `q15`，不得把 q35 neighbor 寫成已修復路徑。

---

## Open Issues

### P0. q15 真正的 deploy blocker 已從 `feat_4h_bb_pct_b` 收斂到 `feat_4h_bias50 + exact-support accumulation`
**現象**
- `hb_q15_boundary_replay.py`：`verdict = same_lane_counterfactual_bucket_proxy_only`
- `component_counterfactual.verdict = bucket_proxy_only_not_trade_floor_fix`
- `feat_4h_bb_pct_b` 補到跨 q35 後，`entry_quality_after = 0.4547 < 0.55`、`allowed_layers_after = 0`
- `hb_q15_support_audit.py`：`best_single_component = feat_4h_bias50`、`required_score_delta = 0.4243`

**影響**
- 這代表 `feat_4h_bb_pct_b` 現在只能當 bucket proxy / structure diagnosis，不是 deployable 修補
- 下一輪若還把主線寫成「處理 bb_pct_b 就能解 q15」，就會變成空轉

**本輪 patch / 證據**
- `scripts/hb_q15_boundary_replay.py`
- `tests/test_q15_boundary_replay.py`
- `data/q15_boundary_replay.json`
- `docs/analysis/q15_boundary_replay.md`
- `ARCHITECTURE.md`

**下一步**
- 直接檢查 `feat_4h_bias50` / base stack 在 q15 exact lane 的 floor-gap 角色
- 保留 `feat_4h_bb_pct_b` 為 structure proxy，不再把它當 deploy patch 候選

### P1. q15 support 已開始累積，但仍只有 4/50
**現象**
- `support_progress.status = accumulating`
- `current_rows = 4`
- `delta_vs_previous = +4`
- `gap_to_minimum = 46`

**影響**
- 這不再是「完全無歷史」問題，而是明確的 exact-support 累積問題
- runtime 仍必須維持 `allowed_layers = 0`

**本輪證據**
- `scripts/hb_q15_support_audit.py`
- `data/q15_support_audit.json`

**下一步**
- 下一輪必須持續追 `support_progress.current_rows` 是否增加
- 若 rows 停在 4 且 `stagnant_run_count` 上升，升級成 stalled support blocker

### P1. recent drift 的主病灶仍是 bull-pocket distribution pathology
**現象**
- `recent_drift_report.py`：primary window 仍是 recent 100
- alerts = `constant_target`, `regime_concentration`, `regime_shift`
- sibling-window `new_compressed = feat_4h_bb_pct_b`

**影響**
- drift artifact 仍指向 bull pocket 的極端分布，不可把 recent TW-IC / live lane 當成穩定可部署常態
- 但本輪已證明 `feat_4h_bb_pct_b` 單點修補不足以過 floor，所以下一輪不能只在 drift 報表裡重複它

**下一步**
- 讓 drift / q15 / live probe 三條證據都回到同一個主結論：`bb_pct_b` 是 structure proxy，真正部署 blocker 是 `bias50 + support accumulation`

### P2. q35 保持 reference-only，不得重回 current-live 主敘事
**現象**
- current live bucket 仍是 q15
- q35 是 dominant same-lane neighbor bucket，不是 current-live closure

**影響**
- q35 只能作 comparison/reference lane，不得重寫成當前 deployment closure

**下一步**
- 只有在 current live row 真正回到 q35，才重啟 q35 scaling / deployment 主線

---

## Not Issues
- **`feat_4h_bb_pct_b` 單點反事實已足以解除 q15 blocker**：不是。它只會 rebucket，不會跨 trade floor。
- **本輪主線仍應該先做 boundary review**：不是。artifact 已明確改寫成 `same_lane_counterfactual_bucket_proxy_only`。
- **`feat_4h_bias50` 可以立刻放寬 runtime gate**：不是。`math_cross_possible_but_illegal_without_exact_support` 仍成立。
- **q35 應回來接管本輪主線**：不是。current live 仍在 q15。

---

## Current Priority
1. **直接檢查 `feat_4h_bias50 / base stack` 為何仍把 q15 exact lane 壓在 floor 下方**
2. **持續監看 q15 support accumulation（4/50 是否繼續增加）**
3. **維持 `feat_4h_bb_pct_b` 為 structure proxy、維持 q35 為 reference-only**

---

## Next Gate Input
- **Next focus**：`feat_4h_bias50 floor-gap audit`、`q15 support accumulation 4→?`、`keep feat_4h_bb_pct_b as structure proxy only`
- **Success gate**：
  - 產出 1 個直接回答 `feat_4h_bias50` 是否為 q15 exact-lane 主 floor-gap blocker 的 artifact 或 patch
  - `data/q15_support_audit.json` 的 `support_progress.current_rows` 相比本輪 **不下降**
  - `ISSUES.md` / `ROADMAP.md` / `ARCHITECTURE.md` / `data/q15_boundary_replay.json` 對主結論一致：**`feat_4h_bb_pct_b` 不是 deployable patch；當前主 blocker 是 `bias50 + exact support`**
- **Fallback if fail**：
  - 若下一輪還把主線寫成 boundary review / bb_pct_b deploy patch，直接升級成 `#HEARTBEAT_EMPTY_PROGRESS` 類 blocker
  - 若 q15 rows 停在 4 且 `support_progress` 轉 stalled/regressed，升級成 support accumulation blocker
  - 若 current live bucket 切換，先重寫 current-state docs，再決定是否切回 q35 或其他 lane
- **Carry-forward input for next heartbeat**：
  1. 先讀最新 `data/q15_boundary_replay.json`，確認 `verdict` 是否仍是 `same_lane_counterfactual_bucket_proxy_only`。
  2. 若仍是，禁止把 `feat_4h_bb_pct_b` 寫成可部署修補；直接轉去檢查 `feat_4h_bias50` / base stack floor-gap root cause。
  3. 再讀最新 `data/q15_support_audit.json`，逐條檢查：
     - `support_progress.status`
     - `support_progress.current_rows`
     - `support_progress.delta_vs_previous`
     - `support_progress.stagnant_run_count`
     - `support_progress.escalate_to_blocker`
  4. 若 q15 rows 仍低於 50，禁止把 bias50 單點 floor-cross 敘事寫成可 deploy；必須維持 `reference_only_until_exact_support_ready`。
