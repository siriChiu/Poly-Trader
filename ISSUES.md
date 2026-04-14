# ISSUES.md — Current State Only

_最後更新：2026-04-14 19:42 UTC — Heartbeat #742（本輪已把 train / probe 的 bull exact-supported 分支真正接上：training 不再在 exact bucket 已 supported 時直接回退到 global `core_only`，probe 也會把 exact-supported 但 train / leaderboard 尚未收斂的狀態明確標成 `post_threshold_profile_governance_stalled`。下一輪焦點不再是 support 是否足夠，而是把 exact-supported 後的 train / leaderboard profile 真正收斂。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#741）要求本輪處理
- **Next focus**：
  1. 針對 **exact-bucket-supported** 狀態執行 bull post-threshold verification：train / leaderboard / bull artifact 應採哪個 profile；
  2. 驗證 q15 toxic pocket 在 exact-supported 後仍維持 lane-internal veto；
  3. 持續把 `fin_netflow` 當外部 auth blocker 管理。
- **Success gate**：
  1. 必須留下至少一個與 **exact-bucket post-threshold verification / train-path sync / leaderboard governance** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`exact_lane_bucket_verdict`、`decision_quality_exact_live_lane_toxic_bucket`、`allowed_layers` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 q35 exact rows ≥50，不得再把 support 不足當 blocker。
- **Fallback if fail**：
  - 若 train / leaderboard 無法收斂，升級為 `post_threshold_profile_governance_stalled`；
  - 若任一路徑回退成 `proxy_boundary_inconclusive`，視為 governance regression；
  - `fin_netflow` auth 未修前持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - `model/train.py`
    - 補上 exact-supported profile 選擇分支：當 `exact_bucket_root_cause=exact_bucket_supported` 時，training 不再直接回退到 global `feature_group_ablation.recommended_profile`，而是優先走 `bull_4h_pocket_ablation.exact_supported_profile`；
    - `_build_feature_profile_columns()` 現在可真正接受 bull 4H ablation 報告中的 extended profiles：
      - `core_plus_macro_plus_4h_structure_shift`
      - `core_plus_macro_plus_4h_trend`
      - `core_plus_macro_plus_4h_momentum`
      - `core_plus_macro_plus_all_4h`
  - `scripts/hb_leaderboard_candidate_probe.py`
    - 當 exact bucket 已 supported，但 leaderboard 與 train 仍未收斂時，`dual_profile_state` 會明確輸出 **`post_threshold_profile_governance_stalled`**，不再沿用 pre-threshold fallback 語義。
  - 測試通過：
    - `source venv/bin/activate && python -m pytest tests/test_train_target_metrics.py tests/test_hb_leaderboard_candidate_probe.py -q` → **13 passed**
    - `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py tests/test_model_leaderboard.py -q` → **29 passed**
  - 驗證通過：
    - `source venv/bin/activate && python model/train.py`
    - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 742`
- **本輪前提更新**：
  - support blocker 仍已解除：
    - `support_blocker_state=exact_live_bucket_supported`
    - `support_governance_route=exact_live_bucket_supported`
    - `proxy_boundary_verdict=exact_bucket_supported_proxy_not_required`
  - exact-supported 後的新狀態已從「support 不足」切成**治理收斂問題**：
    - `leaderboard_selected_profile = core_plus_macro_plus_4h_structure_shift`
    - `train_selected_profile = core_plus_macro`
    - `dual_profile_state = post_threshold_profile_governance_stalled`
  - q15 toxic pocket 仍保留：
    - `exact_lane_bucket_verdict = toxic_sub_bucket_identified`
    - toxic bucket = `CAUTION|structure_quality_caution|q15`（4 rows / win_rate 0.0）
- **本輪明確不做**：
  - 不因 exact support 已達標就直接放寬 live layers；
  - 不把 q15 toxic bucket 視為已消失；
  - 不把 `fin_netflow` auth blocker 混進 bull profile governance 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `model/train.py`
    - 新增 exact-supported profile 選擇路徑；
    - 新增 bull 4H extended feature profiles 到 training registry，讓 bull ablation 推薦的 profile 不再因 registry 缺欄位而無法被訓練端使用。
  - `scripts/hb_leaderboard_candidate_probe.py`
    - 新增 `post_threshold_profile_governance_stalled` 狀態，讓 probe / summary 能直接區分「還在 support fallback」與「support 已足但 train/leaderboard 尚未收斂」。
  - `tests/test_train_target_metrics.py`
  - `tests/test_hb_leaderboard_candidate_probe.py`
  - `ARCHITECTURE.md`
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_train_target_metrics.py tests/test_hb_leaderboard_candidate_probe.py -q` → **13 passed**
  - `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py tests/test_model_leaderboard.py -q` → **29 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python model/train.py`
    - Train=`63.9%`
    - CV=`73.3% ± 8.7pp`
    - `feature_profile = core_plus_macro`
    - `feature_profile_meta.source = bull_4h_pocket_ablation.exact_supported_profile`
    - `support_cohort = bull_exact_live_lane_proxy`
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 742` → **通過**
  - 已刷新：
    - `data/heartbeat_742_summary.json`
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
- 來自 Heartbeat #742：
  - Raw / Features / Labels：**21426 / 12855 / 43031**
  - 本輪增量：**+1 raw / +1 feature / +26 labels**
  - canonical target `simulated_pyramid_win`：**0.5766**
  - 240m labels：**21575 rows / target_rows 12653 / lag_vs_raw 3.2h**
  - 1440m labels：**12371 rows / target_rows 12371 / lag_vs_raw 23.0h**
  - recent raw age：**約 5.2 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**25/30 pass**
- TW 歷史：**#742=25/30，#741=25/30，#740=25/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 100**
  - alerts：`constant_target`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 85.0%**
  - win_rate：**1.0000**
  - avg_quality：**0.7011**
  - avg_pnl：**+0.0221**
  - avg_drawdown_penalty：**0.0415**
- 判讀：近期 canonical pocket 仍是健康的 supported extreme trend；本輪沒有新的 recent-window pathology blocker。

### Live predictor / bull lane
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.4420**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.4091 (D)**
  - decision-quality label：**C**
  - expected win / quality：**0.8725 / 0.5760**
  - allowed layers：**0 → 0**
  - execution guardrail：**未額外觸發**（`allowed_layers_raw` 本來就是 0）
  - chosen calibration scope：**`regime_label+regime_gate+entry_quality_label` / sample_size=102**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=85**
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
  - dual profile state：**`post_threshold_profile_governance_stalled`**
  - blocked candidate：**none**
- 判讀：**本輪已把 train path 從 global fallback 拉回 exact-supported 分支，但 train 與 leaderboard 仍未收斂到同一個 exact-supported profile。真正 blocker 已是 post-threshold governance stall，而不是 support 缺口。**

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. exact-supported 後的 train / leaderboard profile 仍未收斂
**現象**
- current q35 bucket：**85 rows**，已高於 minimum support=50；
- leaderboard 已切到 **`core_plus_macro_plus_4h_structure_shift`**；
- train path 雖已改走 `bull_4h_pocket_ablation.exact_supported_profile`，但目前仍停在 **`core_plus_macro`**；
- `dual_profile_state = post_threshold_profile_governance_stalled`。

**判讀**
- 這代表「exact-supported 後要用哪個 profile」的治理語義仍未完成閉環；
- 已不再是 sample support 問題，而是 **exact-supported train-path / leaderboard-path 收斂問題**。

**下一步方向**
- 直接比對 train frame 為何仍只選到 `bull_exact_live_lane_proxy/core_plus_macro`；
- 驗證是否能讓 train path 真正消化 `core_plus_macro_plus_4h_structure_shift`，或明確寫出不能切換的條件與門檻。

---

### P1. q15 toxic pocket 仍是 bull exact lane 內部病灶
**現象**
- `exact_lane_bucket_verdict = toxic_sub_bucket_identified`
- toxic bucket：**`CAUTION|structure_quality_caution|q15`**
- rows：**4**；win_rate：**0.0000**

**判讀**
- q35 exact bucket 已 supported，只代表外層 sample-support 問題已解；
- lane 內部仍有明確 toxic 子 bucket，不能因 train / leaderboard profile 已升級就放掉 veto。

**下一步方向**
- 持續保留 q15 veto；
- exact-supported profile 收斂時，也必須驗證 q15 仍不會被 current q35 一起誤放行。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1555)**

**判讀**
- 這仍是**外部憑證 blocker**，不是 bull exact-supported governance 問題。

---

## 本輪已清掉的問題

### RESOLVED. training 在 exact-supported 狀態下仍直接回退到 global `core_only`
**現象（修前）**
- 即使 `exact_bucket_root_cause=exact_bucket_supported`，train path 仍會沿用 global `feature_group_ablation.recommended_profile`；
- 這使得 exact-supported 後的 train / leaderboard 差異被掩蓋成「看起來只是 global winner 不同」，無法真正進入 post-threshold verification。

**本輪 patch + 證據**
- `model/train.py`
  - 新增 `bull_4h_pocket_ablation.exact_supported_profile` 分支；
  - `_build_feature_profile_columns()` 新增 bull 4H extended profiles，讓 training registry 可接住 ablation 推薦名稱；
- `scripts/hb_leaderboard_candidate_probe.py`
  - 新增 `post_threshold_profile_governance_stalled` 狀態；
- 驗證：
  - targeted pytest **42 passed**（13 + 29）；
  - `model/last_metrics.json.feature_profile_meta.source = bull_4h_pocket_ablation.exact_supported_profile`；
  - `data/leaderboard_feature_profile_probe.json.alignment.dual_profile_state = post_threshold_profile_governance_stalled`。

**狀態**
- **已修復**：train 已不再是 global fallback；
- **仍待後續治理**：exact-supported 後 train / leaderboard 還沒收斂到同一 profile。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 exact-supported training branch 真正接上，不再讓 train 直接回退到 global shrinkage。** ✅
2. **讓 probe / summary 對 exact-supported 但尚未收斂的狀態有明確治理語義。** ✅
3. **重跑 train + fast heartbeat，確認 exact-supported contract 已刷新到 artifact / summary。** ✅

### 本輪不做
- 不直接放寬 live layers；
- 不把 q15 toxic pocket 視為已清除；
- 不把 `fin_netflow` auth blocker 與 bull profile governance 混在一起。

---

## 下一輪 gate

- **Next focus:**
  1. 追 `post_threshold_profile_governance_stalled` 的 root cause：為何 leaderboard 已選 `core_plus_macro_plus_4h_structure_shift`，但 train 仍落在 `core_plus_macro`；
  2. 驗證 q15 toxic pocket 在 profile 收斂後仍維持 lane-internal veto；
  3. 持續把 `fin_netflow` 當外部 auth blocker 管理。

- **Success gate:**
  1. next run 必須留下至少一個與 **train / leaderboard exact-supported profile 收斂** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state=exact_live_bucket_supported`、`support_governance_route=exact_live_bucket_supported`、`exact_bucket_root_cause=exact_bucket_supported`、`proxy_boundary_verdict=exact_bucket_supported_proxy_not_required`、`exact_lane_bucket_verdict=toxic_sub_bucket_identified`、`dual_profile_state` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 train 仍無法切到 leaderboard 同一 profile，必須明確寫出不能切換的技術限制與 verify 門檻，不得只重複說「尚未收斂」。

- **Fallback if fail:**
  - 若下一輪仍找不到 train / leaderboard 不一致的 root cause，升級為 `exact_supported_train_frame_parity_blocker`；
  - 若任一路徑回退成 `proxy_boundary_inconclusive` 或 `leaderboard_global_winner_vs_train_support_fallback`，視為 governance regression；
  - 若 current bucket rows 再跌回 <50，必須同輪恢復 under-minimum blocker contract。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 train/leaderboard 收斂 contract 再擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_742_summary.json`
     - `model/last_metrics.json`
     - `data/leaderboard_feature_profile_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `data/live_predict_probe.json`
  2. 逐條確認：
     - `support_blocker_state` 是否仍是 **`exact_live_bucket_supported`**；
     - `proxy_boundary_verdict` 是否仍是 **`exact_bucket_supported_proxy_not_required`**；
     - `dual_profile_state` 是否仍是 **`post_threshold_profile_governance_stalled`**；
     - `leaderboard_selected_profile` 是否仍是 **`core_plus_macro_plus_4h_structure_shift`**；
     - `train_selected_profile` 是否仍是 **`core_plus_macro`**；
     - `train_selected_profile_source` 是否仍是 **`bull_4h_pocket_ablation.exact_supported_profile`**；
     - `train_support_cohort` 是否仍是 **`bull_exact_live_lane_proxy`**，或已切到更貼近 exact bucket 的 cohort；
     - `current_live_structure_bucket` 是否仍是 **`CAUTION|structure_quality_caution|q35`** 且 rows 是否仍 **≥50**；
     - `decision_quality_exact_live_lane_toxic_bucket.bucket` 是否仍是 **`CAUTION|structure_quality_caution|q15`**；
     - `allowed_layers` 是否仍是 **0**，其原因是 gate/quality 還是其他 guardrail。
  3. 若以上條件大多仍成立，下一輪不得再把「support 已達標」當成功；必須直接追 **exact-supported train-frame parity / leaderboard convergence / q15 toxic pocket 保守治理**。
