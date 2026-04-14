# ISSUES.md — Current State Only

_最後更新：2026-04-14 22:23 UTC — Heartbeat #743（本輪已修補 leaderboard candidate probe 的 current-vs-snapshot recency 判讀：舊 snapshot 不再覆蓋當前治理狀態；同時重跑 train + fast heartbeat，確認目前真實 blocker 是 **q35 exact-supported 已恢復，但 train 仍停在 support-aware `core_plus_macro`，與 leaderboard 的 exact-supported `core_plus_macro_plus_4h_structure_shift` 未收斂**。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#742）要求本輪處理
- **Next focus**：
  1. 追 `post_threshold_profile_governance_stalled` 的 root cause：為何 leaderboard 已選 `core_plus_macro_plus_4h_structure_shift`，但 train 仍落在 `core_plus_macro`；
  2. 驗證 q15 toxic pocket 在 profile 收斂後仍維持 lane-internal veto；
  3. 持續把 `fin_netflow` 當外部 auth blocker 管理。
- **Success gate**：
  1. 至少留下 1 個與 **exact-supported train-frame parity / leaderboard convergence** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state / support_governance_route / exact_bucket_root_cause / proxy_boundary_verdict / exact_lane_bucket_verdict / dual_profile_state / allowed_layers` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 train 仍無法切到 leaderboard 同一 profile，必須明確寫出技術限制與 verify 門檻。
- **Fallback if fail**：
  - 若仍找不到 train / leaderboard 不一致 root cause，升級為 `exact_supported_train_frame_parity_blocker`；
  - 若 proxy contract 回退成 pre-threshold blocker 文案，視為 governance regression；
  - `fin_netflow` auth 未修前持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - `scripts/hb_leaderboard_candidate_probe.py`
    - 新增 `alignment_evaluated_at / current_alignment_inputs_stale / current_alignment_recency / artifact_recency`；
    - 修正 `dual_profile_state` 判讀：**舊 leaderboard snapshot 只能作背景訊號，不可覆蓋當前治理差異**；只有 current inputs 真的過期時才標 `stale_alignment_snapshot`。
  - `scripts/hb_parallel_runner.py`
    - fast heartbeat summary / console 現在會同步暴露 `current_alignment_recency` 與 `artifact_recency`，避免 summary 把「舊 snapshot」誤當成「當前 blocker 已解」。
  - `tests/test_hb_leaderboard_candidate_probe.py`
    - 新增 regression test，鎖住「inputs 已新鮮時，仍須回報當前治理差異」；
  - `tests/test_hb_parallel_runner.py`
    - 修正 JSON fixture 布林值 typo，讓新 recency contract 測試可穩定執行。
  - `ARCHITECTURE.md`
    - 同步寫入 current-vs-snapshot alignment recency contract。
- **驗證已完成**：
  - `source venv/bin/activate && python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py tests/test_strategy_lab.py -q` → **38 passed**
  - `source venv/bin/activate && python model/train.py` → **通過**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 743` → **通過**
- **本輪前提更新**：
  - q35 current live structure bucket 已恢復 exact-supported：
    - `support_blocker_state = exact_live_bucket_supported`
    - `support_governance_route = exact_live_bucket_supported`
    - `exact_bucket_root_cause = exact_bucket_supported`
    - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
    - `current_live_structure_bucket = CAUTION|structure_quality_caution|q35`
    - `current_live_structure_bucket_rows = 90`
  - q15 toxic pocket 仍存在且必須保留 lane-internal veto：
    - `exact_lane_bucket_verdict = toxic_sub_bucket_identified`
    - toxic bucket = `CAUTION|structure_quality_caution|q15`（4 rows / win_rate 0.0）
  - **真實未收斂點已被重新定位**：
    - leaderboard 目前選 `core_plus_macro_plus_4h_structure_shift`
    - train 目前選 `core_plus_macro`
    - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
    - `current_alignment_inputs_stale = false`
    - `artifact_recency.alignment_snapshot_stale = true`
- **本輪明確不做**：
  - 不把「舊 snapshot 過期」直接當成已解或未解的唯一結論；
  - 不因 q35 rows 已達標就放寬 live layers；
  - 不把 `fin_netflow` auth blocker 混進 bull profile governance 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_leaderboard_candidate_probe.py`
  - `scripts/hb_parallel_runner.py`
  - `tests/test_hb_leaderboard_candidate_probe.py`
  - `tests/test_hb_parallel_runner.py`
  - `ARCHITECTURE.md`
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py tests/test_strategy_lab.py -q` → **38 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python model/train.py`
    - Train=`63.8%`
    - CV=`73.5% ± 8.4pp`
    - `feature_profile = core_plus_macro`
    - `feature_profile_meta.source = bull_4h_pocket_ablation.support_aware_profile`
    - `support_cohort = bull_exact_live_lane_proxy`
    - `exact_live_bucket_rows = 4`（train 使用的是較舊 bull pocket artifact）
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 743` → **通過**
  - 已刷新：
    - `data/heartbeat_743_summary.json`
    - `data/full_ic_result.json`
    - `data/ic_regime_analysis.json`
    - `data/recent_drift_report.json`
    - `data/live_predict_probe.json`
    - `data/live_decision_quality_drilldown.json`
    - `data/feature_group_ablation.json`
    - `data/bull_4h_pocket_ablation.json`
    - `data/leaderboard_feature_profile_probe.json`
    - `model/last_metrics.json`

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #743：
  - Raw / Features / Labels：**21433 / 12862 / 43047**
  - 本輪增量：**+1 raw / +1 feature / +1 label**
  - canonical target `simulated_pyramid_win`：**0.5766**
  - 240m labels：**21582 rows / target_rows 12660 / lag_vs_raw 3.2h**
  - 1440m labels：**12380 rows / target_rows 12380 / lag_vs_raw 23.3h**
  - recent raw age：**約 5.2 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**26/30 pass**
- TW 歷史：**#743=26/30，#742=25/30，#741=25/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 100**
  - alerts：`label_imbalance`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 89.0%**
  - win_rate：**0.9900**
  - avg_quality：**0.6954**
  - avg_pnl：**+0.0218**
  - avg_drawdown_penalty：**0.0326**
- 判讀：近期 canonical pocket 仍健康；本輪沒有新的 recent-window pathology blocker。

### Live predictor / bull lane
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.5110**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.3843 (D)**
  - decision-quality label：**B**
  - expected win / quality：**0.8785 / 0.5816**
  - allowed layers：**0 → 0**
  - execution guardrail：**未額外觸發**（`allowed_layers_raw` 本來就是 0）
  - chosen calibration scope：**`regime_label+regime_gate+entry_quality_label` / sample_size=107**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=90**
  - `decision_quality_exact_live_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
  - `decision_quality_exact_live_lane_toxic_bucket.bucket`：**`CAUTION|structure_quality_caution|q15`（4 rows / win_rate 0.0）**
- `data/bull_4h_pocket_ablation.json`
  - blocker_state：**`exact_live_bucket_supported`**
  - support_governance_route：**`exact_live_bucket_supported`**
  - exact bucket root cause：**`exact_bucket_supported`**
  - current bucket gap to minimum：**0**
  - bull all cohort recommended profile：**`core_plus_macro_plus_4h_structure_shift`**
  - exact live lane proxy recommended profile：**`core_plus_macro`**
  - `proxy_boundary_verdict`：**`exact_bucket_supported_proxy_not_required`**
  - `exact_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_plus_macro_plus_4h_structure_shift`**
  - train selected profile：**`core_plus_macro`**
  - global recommended profile：**`core_only`**
  - dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
  - `current_alignment_inputs_stale = false`
  - `artifact_recency.alignment_snapshot_stale = true`
- 判讀：**本輪已證實 current live bucket 重新回到 exact-supported，但 train 仍沿用 support-aware 路徑；這是目前真正的治理未收斂點。舊 leaderboard snapshot 只是背景訊號，不是本輪主 blocker。**

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. train 仍未切到 exact-supported bull profile（真實 blocker）
**現象**
- q35 current live bucket 已 supported：**90 rows ≥ 50**；
- leaderboard 已選 **`core_plus_macro_plus_4h_structure_shift`**；
- train 剛重跑後仍是 **`core_plus_macro`**；
- `train_selected_profile_source = bull_4h_pocket_ablation.support_aware_profile`。

**判讀**
- 這不是 support 不足，也不是 probe 讀錯 snapshot；
- 這是 **train artifact 與最新 bull pocket / leaderboard artifact 的收斂失敗**；
- 目前最可能的直接根因是：train 執行時吃到的是較舊 bull pocket artifact（`generated_at=21:45:38`），而 fast heartbeat 之後 bull pocket 已刷新到 q35 supported（`generated_at=22:08:34`）。

**下一步方向**
- 直接修 train/heartbeat 的 artifact 順序或 freshness gate，避免 train 在 exact-supported 恢復後仍吃到 support-aware 舊 artifact；
- 修完後必須重跑 train + probe，確認 train / leaderboard 同步收斂到 exact-supported profile，或明確輸出新的技術限制。

---

### P1. q15 toxic pocket 仍是 bull exact lane 內部病灶
**現象**
- `exact_lane_bucket_verdict = toxic_sub_bucket_identified`
- toxic bucket：**`CAUTION|structure_quality_caution|q15`**
- rows：**4**；win_rate：**0.0000**

**判讀**
- q35 current bucket 已 supported 且健康（90 rows / win_rate 1.0）；
- 但 lane 內部的 q15 仍必須維持 veto 候選，不可因 q35 supported 就一起放行。

**下一步方向**
- profile 收斂時，必須同步驗證 q15 veto 仍保留；
- 不得讓 exact-supported profile 收斂把 q15 toxic sub-bucket 一併稀釋掉。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1562)**

**判讀**
- 這仍是**外部憑證 blocker**，不是 bull profile governance 問題。

---

## 本輪已清掉的問題

### RESOLVED. 舊 leaderboard snapshot 會遮蔽當前治理狀態
**現象（修前）**
- probe 只要看到 `leaderboard_snapshot_created_at` 舊，就容易把當前 mismatch 一律包成 stale，導致 heartbeat 無法分辨：
  - 只是舊 snapshot 過期；或
  - train / leaderboard 真的還沒收斂。

**本輪 patch + 證據**
- `scripts/hb_leaderboard_candidate_probe.py`
  - 補 `alignment_evaluated_at / current_alignment_inputs_stale / current_alignment_recency / artifact_recency`
  - `dual_profile_state` 現在優先依 current inputs 判讀，而不是直接被舊 snapshot 吃掉
- `scripts/hb_parallel_runner.py`
  - summary / console 同步暴露 recency metadata
- 測試：
  - `pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py tests/test_strategy_lab.py -q` → **38 passed**

**狀態**
- **已修復**：heartbeat 現在能分清「舊 snapshot」與「當前真 blocker」；
- **因此本輪重新確認的真 blocker**：train 仍未切到 exact-supported bull profile。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **先修 probe / summary 的 recency contract，避免舊 snapshot 遮蔽真 blocker。** ✅
2. **重跑 train + fast heartbeat，重新量測 train / leaderboard / q15 contract 的當前狀態。** ✅
3. **把 blocker 從模糊的 stale snapshot 重新收斂為 train artifact parity 問題。** ✅

### 本輪不做
- 不直接放寬 live layers；
- 不把 q15 toxic pocket 視為已清除；
- 不把 `fin_netflow` auth blocker 與 bull profile governance 混在一起。

---

## 下一輪 gate

- **Next focus:**
  1. 修 `model/train.py` / heartbeat artifact 順序，確保 train 會吃到最新 `bull_4h_pocket_ablation.json` 與 `feature_group_ablation.json`，不再停在 support-aware 舊 artifact；
  2. 重跑 train + probe，驗證 q35 exact-supported 時 train / leaderboard 是否收斂到 `core_plus_macro_plus_4h_structure_shift`；
  3. 繼續保留並驗證 q15 toxic pocket lane-internal veto。

- **Success gate:**
  1. next run 必須留下至少一個與 **train artifact freshness / exact-supported train-frame parity** 直接相關的 patch / artifact / verify；
  2. 若 q35 current bucket rows 仍 **≥50**，`train_selected_profile` 不得再停在 support-aware `core_plus_macro` 而沒有明確原因；
  3. `support_blocker_state / support_governance_route / exact_bucket_root_cause / proxy_boundary_verdict / exact_lane_bucket_verdict / dual_profile_state / current_alignment_inputs_stale / allowed_layers` 在 artifact / probe / docs / summary 間零漂移。

- **Fallback if fail:**
  - 若 train 仍吃到舊 bull pocket artifact，升級為 `exact_supported_train_frame_parity_blocker`；
  - 若 q35 rows 再跌回 <50，必須同輪恢復 under-minimum blocker contract；
  - 若 probe 又把舊 snapshot 誤當成唯一結論，視為 recency governance regression。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 train artifact freshness contract 再擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_743_summary.json`
     - `model/last_metrics.json`
     - `data/leaderboard_feature_profile_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `data/live_predict_probe.json`
  2. 逐條確認：
     - `support_blocker_state` 是否仍是 **`exact_live_bucket_supported`**；
     - `support_governance_route` 是否仍是 **`exact_live_bucket_supported`**；
     - `proxy_boundary_verdict` 是否仍是 **`exact_bucket_supported_proxy_not_required`**；
     - `current_live_structure_bucket` 是否仍是 **`CAUTION|structure_quality_caution|q35`** 且 rows 是否仍 **≥50**；
     - `decision_quality_exact_live_lane_toxic_bucket.bucket` 是否仍是 **`CAUTION|structure_quality_caution|q15`**；
     - `leaderboard_selected_profile` 是否仍是 **`core_plus_macro_plus_4h_structure_shift`**；
     - `train_selected_profile` 是否仍是 **`core_plus_macro`** 還是已收斂；
     - `train_selected_profile_source` 是否仍是 **`bull_4h_pocket_ablation.support_aware_profile`**；
     - `current_alignment_inputs_stale` 是否仍是 **false**；
     - `artifact_recency.alignment_snapshot_stale` 是否仍是 **true**（僅作背景，不可取代當前 blocker 判讀）。
  3. 若以上條件大多仍成立，下一輪不得再把「snapshot 舊」當主結論；必須直接推進 **train artifact freshness / exact-supported train-frame parity / q15 toxic pocket 保守治理**。
