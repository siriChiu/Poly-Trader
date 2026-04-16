# ISSUES.md — Current State Only

_最後更新：2026-04-16 11:18 UTC_

只保留目前仍有效的問題；不保留歷史敘事。

---

## Step 0.5 承接（把上輪結論當本輪輸入）
- 上輪 carry-forward 主軸：`feat_4h_bias20 recent-window unexpected compression root cause`、`q15 support_progress history + accumulation`、`q15 same-lane neighbor dominance minimal component counterfactual`。
- 本輪逐條對照結果：
  1. **`feat_4h_bias20` 已不再是 primary recent blocker**：重跑 `scripts/recent_drift_report.py` 後，primary window 仍是 recent 100 bull pocket，但 sibling-window `new_compressed` 已從上一輪文件中的 `feat_4h_bias20` 改為 **`feat_4h_bb_pct_b`**。表示上輪要求追的 bias20 已不是 current-live 需要先拆的主病灶。
  2. **q15 support_progress 已從「無可比歷史」進入「累積中」**：`scripts/hb_q15_support_audit.py` 現在回報 `support_progress.status = accumulating`、`current_rows = 4`、`delta_vs_previous = +4`，上輪要求的歷史鏈已成立，不再是 `no_recent_comparable_history`。
  3. **q15 same-lane neighbor dominance 仍成立，且焦點已收斂到同一個 component**：`scripts/hb_q15_bucket_root_cause.py` 仍回報 `same_lane_neighbor_bucket_dominates`，候選 patch feature 仍是 **`feat_4h_bb_pct_b`**；這次又與 recent drift 的 `new_compressed=feat_4h_bb_pct_b` 收斂到同一個結構欄位，代表下一輪不能再回退到 generic q35/bias50 敘事。
  4. **q35 仍是 reference-only**：current live row 仍是 `bull / CAUTION / q15`；`feat_4h_bias50` 雖然在 floor-cross 數學上可跨門檻，但 `support_route` 仍是 `exact_bucket_present_but_below_minimum`，因此 q35 / bias50 不能接管當前 blocker。

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
- q15 boundary replay：`boundary_replay_not_applicable`
- comprehensive test：**6/6 PASS**

---

## Step 1 事實分類

### 已改善
1. **上輪要求追的 `feat_4h_bias20` 已退出 primary unexpected-compressed 主病灶**：本輪 `recent_drift_report.py` 顯示 sibling-window `new_compressed` 已轉成 `feat_4h_bb_pct_b`。
2. **q15 support history 鏈已正式成立**：`support_progress.status` 從上一輪文件中的 `no_recent_comparable_history` 變成 **`accumulating`**，而且 `delta_vs_previous = +4`。
3. **本輪留下真實 patch 而不是只重跑**：
   - `scripts/recent_drift_report.py` 新增 **`feat_4h_rsi14` expected-compression provenance**，避免把 short-trend oscillator 的一致性壓縮誤判成單點 projection blocker。
   - 同步補上缺 proxy 欄位時的 guard，避免測試／精簡資料集因缺欄崩潰。
   - `tests/test_recent_drift_report.py` 新增對 `feat_4h_rsi14` provenance 的回歸測試。
   - `ARCHITECTURE.md` 已同步 4H RSI14 provenance contract。
4. **驗證閉環完整**：
   - `python -m pytest tests/test_recent_drift_report.py -q` → **17 passed**
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
1. **recent canonical pathology 仍未解除**：recent 100 仍是 `100x1 bull pocket`，primary interpretation 仍是 `distribution_pathology`。
2. **主病灶已收斂到 `feat_4h_bb_pct_b`**：這比上一輪更聚焦，但也代表下一輪若還不碰 `feat_4h_bb_pct_b` counterfactual，就會再次變成報告式空轉。

### 卡住不動
1. **q15 exact support 仍遠低於 deployment minimum**：當前仍只有 **4 / 50**，runtime 必須維持 `allowed_layers = 0`。
2. **boundary replay 仍不能用**：`boundary_replay_not_applicable`，表示不能用 bucket 邊界重標來掩蓋 exact support 缺口。
3. **bias50 仍只能當 reference-only floor-cross 候選**：雖然 `feat_4h_bias50` 在數學上能跨 floor，但在 q15 support 未達標前仍不得直接放行。

---

## Open Issues

### P0. `feat_4h_bb_pct_b` 已成為 recent drift 與 q15 root-cause 的共同主病灶
**現象**
- `recent_drift_report.py`：primary window sibling 比較的 `new_compressed = feat_4h_bb_pct_b`
- `hb_q15_bucket_root_cause.py`：`candidate_patch_feature = feat_4h_bb_pct_b`
- current live row 與 dominant q35 neighbor 的最小差距也落在 `feat_4h_bb_pct_b`

**影響**
- drift 診斷與 q15 structure gap 現在指向同一個 component；若不做 `feat_4h_bb_pct_b` 最小 counterfactual，下一輪就沒有理由再重跑相同 artifact

**本輪證據**
- `python scripts/recent_drift_report.py`
- `python scripts/hb_q15_bucket_root_cause.py`
- `data/recent_drift_report.json`
- `data/q15_bucket_root_cause.json`

**下一步**
- 直接比較 current row 與 `CAUTION|structure_quality_caution|q35` neighbor bucket 的 `feat_4h_bb_pct_b` 分布差值
- 做最小 counterfactual，驗證只調整 `feat_4h_bb_pct_b` 是否能把 current row 推近 q35，且不越權解除 exact-support blocker

### P1. q15 support 已開始累積，但仍只有 4/50
**現象**
- `support_progress.status = accumulating`
- `current_rows = 4`
- `delta_vs_previous = +4`
- `gap_to_minimum = 46`

**影響**
- 這不再是「沒有歷史」問題，而是明確的 exact-support 累積問題
- runtime 仍必須維持 `allowed_layers = 0`

**本輪 patch / 證據**
- `scripts/hb_q15_support_audit.py` 產出的歷史鏈已被本輪重跑驗證
- `data/q15_support_audit.json` 明確留下 `accumulating` 狀態與歷史比較

**下一步**
- 下一輪必須持續保留同一 bucket 的 support history
- 若 rows 停在 4 且 `stagnant_run_count` 持續上升，直接升級成 stalled blocker

### P1. recent drift 的 oscillator 誤報已被修正，但 bull pocket pathology 還在
**現象**
- 本輪 patch 後，`feat_4h_rsi14` 不再是 sibling-window 的新 unexpected compression
- 但 primary window 仍是 `100x1 bull pocket`

**影響**
- 代表 recent pathology 的核心不再是 RSI14 診斷誤報，而是更聚焦的 4H 結構壓縮 / bucket 組成問題

**本輪 patch / 證據**
- `scripts/recent_drift_report.py`
- `tests/test_recent_drift_report.py` → **17 passed**
- `ARCHITECTURE.md` 4H RSI14 provenance contract

**下一步**
- 不要再把 focus 放回 `feat_4h_rsi14`；下一輪直接做 `feat_4h_bb_pct_b` counterfactual / structure scoring 檢查

### P2. q35 保持 reference-only，不得重回 current-live 主敘事
**現象**
- current live bucket 仍是 q15
- dominant neighbor bucket 雖是 q35，但目前只是 comparison lane

**影響**
- q35 只能作 reference neighbor，不得重寫成當前 deployment closure

**下一步**
- 只有在 current live row 真正回到 q35 時，才重啟 q35 scaling / deployment 主線

---

## Not Issues
- **`feat_4h_bias20` 仍是 primary recent blocker**：不是。本輪 `new_compressed` 已變成 `feat_4h_bb_pct_b`。
- **`feat_4h_rsi14` 是新的單點 projection blocker**：不是。本輪已補 provenance，現在它屬於 coherent short-trend oscillator compression，不是 current priority。
- **`feat_4h_bias50` 可以直接解除 q15 blocker**：不是。`floor_cross_legality` 仍是 `math_cross_possible_but_illegal_without_exact_support`。
- **q35 應回來接管本輪主線**：不是。current live 仍在 q15。

---

## Current Priority
1. **直接處理 `feat_4h_bb_pct_b` 的 q15→q35 最小 component counterfactual**
2. **持續監看 q15 support accumulation（4/50 是否繼續增加）**
3. **維持 q35 / bias50 為 reference-only，直到 exact support 達標**

---

## Next Gate Input
- **Next focus**：`feat_4h_bb_pct_b minimal component counterfactual`、`q15 support accumulation 4→?`、`keep bias50/q35 reference-only until exact support ready`
- **Success gate**：
  - 產出 1 個針對 `feat_4h_bb_pct_b` 的最小 counterfactual artifact 或 patch，明確回答它是否足以把 current row 推近 q35
  - `data/q15_support_audit.json` 仍保留同 bucket 歷史，且 `support_progress.current_rows` 相比本輪 **不下降**
  - 若 counterfactual 只改 bucket、不足以合法放行，文件必須明確保留 `reference_only_until_exact_support_ready`
- **Fallback if fail**：
  - 若下一輪仍未對 `feat_4h_bb_pct_b` 動手，直接升級成 `#HEARTBEAT_EMPTY_PROGRESS` 類 blocker
  - 若 q15 rows 停在 4 且 `support_progress` 轉成 stalled/regressed，升級成 support accumulation blocker
  - 若 current live bucket 切換，先重寫 current-state docs，再決定是否切回 q35 或其他 lane
- **Carry-forward input for next heartbeat**：
  1. 先讀最新 `data/recent_drift_report.json`，確認 primary window 的 sibling `new_compressed` 是否仍是 `feat_4h_bb_pct_b`。
  2. 先讀最新 `data/q15_support_audit.json`，逐條檢查：
     - `support_progress.status`
     - `support_progress.current_rows`
     - `support_progress.delta_vs_previous`
     - `support_progress.stagnant_run_count`
     - `support_progress.escalate_to_blocker`
  3. 再讀 `data/q15_bucket_root_cause.json`；若 `candidate_patch_feature` 仍是 `feat_4h_bb_pct_b`，下一輪只能做它的最小 counterfactual / scoring verify，不得回退到 generic q35/bias50 討論。
  4. 若 q15 rows 仍低於 50，禁止把 bias50 單點 floor-cross 敘事寫成可 deploy；必須維持 `reference_only_until_exact_support_ready`。
