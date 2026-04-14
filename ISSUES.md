# ISSUES.md — Current State Only

_最後更新：2026-04-14 19:12 UTC — Heartbeat #741（bull `CAUTION|structure_quality_caution|q35` exact support 已跨過 minimum support；本輪已修掉 proxy contract 在 exact-supported 狀態下仍殘留 `proxy_boundary_inconclusive` 的語義漂移，接下來主題轉成 exact-bucket post-threshold verification，而不是繼續把 support 不足當主 blocker。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#740）要求本輪處理
- **Next focus**：
  1. 追蹤 `CAUTION|structure_quality_caution|q35` exact rows 是否從 42 → ≥50；
  2. 若仍 <50，持續驗證 `proxy_governance_reference_only_exact_support_blocked` 與 q15 toxic contract 在所有 surface 零漂移；
  3. 持續維持 `fin_netflow` external auth blocker 顯式治理。
- **Success gate**：
  1. 必須留下至少一個與 q35 support 驗證或 proxy / toxic contract 對齊直接相關的 patch / artifact / verify；
  2. `support_blocker_state`、`support_governance_route`、`exact_bucket_root_cause`、`proxy_boundary_verdict`、`exact_lane_bucket_verdict`、`decision_quality_exact_live_lane_toxic_bucket`、`allowed_layers` 在 artifact / probe / docs / summary 間零漂移；
  3. 若 q35 exact rows ≥50，必須切換到解除 blocker 驗證，而不是直接部署。
- **Fallback if fail**：
  - 若 q35 rows 仍卡在 42 附近，升級成 stalled investigation；
  - 若任一路徑回退成 `proxy_boundary_inconclusive`，視為 governance regression；
  - `fin_netflow` auth 未修前持續標記 blocked。

### 本輪承接結果
- **已處理**：
  - q35 exact support 已從 **42 → 61**，正式跨過 minimum support=50；
  - `scripts/bull_4h_pocket_ablation.py` 已修正：當 `exact_bucket_root_cause=exact_bucket_supported` 時，summary 不再殘留 `proxy_boundary_inconclusive`，而是明確輸出 **`exact_bucket_supported_proxy_not_required`**；
  - `tests/test_bull_4h_pocket_ablation.py`、`tests/test_hb_leaderboard_candidate_probe.py` 已補 exact-supported regression；
  - `python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **19 passed**；
  - `python scripts/hb_parallel_runner.py --fast --hb 741` 已重建 artifact / probe / summary，確認 `leaderboard_feature_profile_probe.json` 與 `heartbeat_741_summary.json` 都已改成 `exact_bucket_supported_proxy_not_required`。
- **本輪前提更新**：
  - bull live path 的主 blocker 已**不再是 support 不足**；
  - `support_blocker_state=exact_live_bucket_supported`、`support_governance_route=exact_live_bucket_supported`；
  - `allowed_layers` 仍是 **0**，但原因已轉成 **live regime_gate=CAUTION + entry_quality=D + runtime sizing guard**，不是 q35 support 不足；
  - `train_selected_profile` 仍是 **`core_plus_macro`**，而 bull artifact 最新建議已是 **`core_plus_macro_plus_4h_structure_shift`**，表示進入「post-threshold verification / train-path sync」階段。
- **本輪明確不做**：
  - 不因 exact support 達標就直接放寬 live execution；
  - 不把 q15 toxic pocket 視為已消失；
  - 不把 `fin_netflow` auth blocker 混成 bull support 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/bull_4h_pocket_ablation.py`
    - 新增 exact-supported 收斂邏輯：當 current live structure bucket 已達 minimum support 時，`proxy_boundary_verdict` 強制改成 **`exact_bucket_supported_proxy_not_required`**，reason 也改為「後續治理以 exact bucket 為主，proxy 只保留輔助比較」。
  - `tests/test_bull_4h_pocket_ablation.py`
    - 新增 `exact_bucket_supported_proxy_not_required` regression。
  - `tests/test_hb_leaderboard_candidate_probe.py`
    - 新增 leaderboard alignment 在 exact-supported 狀態下同步輸出新 verdict 的 regression。
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_bull_4h_pocket_ablation.py tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **19 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 741` → **通過**；
  - 已刷新：
    - `data/heartbeat_741_summary.json`
    - `data/bull_4h_pocket_ablation.json`
    - `docs/analysis/bull_4h_pocket_ablation.md`
    - `data/leaderboard_feature_profile_probe.json`
    - `data/live_predict_probe.json`
    - `data/live_decision_quality_drilldown.json`

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #741：
  - Raw / Features / Labels：**21425 / 12854 / 43005**
  - 本輪增量：**+2 raw / +2 features / +20 labels**（兩次 fast run 合計）
  - canonical target `simulated_pyramid_win`：**0.5762**
  - 240m labels：**21573 rows / target_rows 12651 / lag_vs_raw 3.3h**
  - 1440m labels：**12347 rows / target_rows 12347 / lag_vs_raw 23.0h**
  - recent raw age：**約 4.3 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**25/30 pass**
- TW 歷史：**#741=25/30，#740=25/30，#739=25/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 100**
  - alerts：`constant_target`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 61.0%**
  - win_rate：**1.0000**
  - avg_quality：**0.7018**
  - avg_pnl：**+0.0219**
  - avg_drawdown_penalty：**0.0406**
- 判讀：近期 canonical pocket 仍是健康的 supported extreme trend；本輪沒有新的 recent-window pathology blocker。

### Live predictor / bull lane
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.1831**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.4062 (D)**
  - decision-quality label：**C**
  - expected win / quality：**0.8333 / 0.5429**
  - allowed layers：**0 → 0**
  - execution guardrail：**未額外觸發**（`allowed_layers_raw` 本來就是 0）
  - chosen calibration scope：**`regime_label+regime_gate+entry_quality_label` / sample_size=78**
  - exact live lane：**78 rows / win_rate 0.8333 / quality 0.5429**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=61 / win_rate 1.0000 / quality 0.7152 左右**
  - `decision_quality_exact_live_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
  - `decision_quality_exact_live_lane_toxic_bucket.bucket`：**`CAUTION|structure_quality_caution|q15`（4 rows / win_rate 0.0）**
- `data/bull_4h_pocket_ablation.json`
  - blocker_state：**`exact_live_bucket_supported`**
  - support_governance_route：**`exact_live_bucket_supported`**
  - exact bucket root cause：**`exact_bucket_supported`**
  - current bucket gap to minimum：**0**
  - historical exact-bucket proxy：**114 rows**
  - exact live lane proxy：**377 rows**
  - `proxy_boundary_verdict`：**`exact_bucket_supported_proxy_not_required`**
  - `exact_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_only`**
  - train selected profile：**`core_plus_macro`**
  - blocked candidate：**none**
  - dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
  - `proxy_boundary_verdict` 已與 bull artifact 對齊為 **`exact_bucket_supported_proxy_not_required`**
- 判讀：**support blocker 已解除，但 exact-bucket 達標後的訓練/leaderboard 路徑尚未完成重新驗證；現在的卡點是 post-threshold verification，不是 support accumulation。**

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. bull exact support 已達標，但 post-threshold verification 尚未完成
**現象**
- `current_live_structure_bucket_rows=61`，已高於 minimum support=50；
- `support_blocker_state=exact_live_bucket_supported`；
- 但 `train_selected_profile` 仍停在 **`core_plus_macro`**，而 bull artifact 最新 `bull_recommended_profile` 已是 **`core_plus_macro_plus_4h_structure_shift`**；
- `leaderboard_selected_profile` 仍是 **`core_only`**。

**判讀**
- q35 support accumulation 任務已完成；
- 下一步不應再問「support 夠不夠」，而是要做 **exact-bucket post-threshold verification**：
  - exact bucket 達標後，train / leaderboard / runtime 應採哪個 profile？
  - exact-supported 狀態下，哪些語義仍需維持保守（例如 q15 toxic pocket 與 CAUTION gate）？

**下一步方向**
- 以 q35 exact-supported 狀態重做 bull profile / train-path 驗證；
- 不得直接把達標 support 視為可部署。

---

### P1. q15 toxic pocket 仍是 bull exact lane 內部病灶
**現象**
- `exact_lane_bucket_verdict = toxic_sub_bucket_identified`
- toxic bucket：**`CAUTION|structure_quality_caution|q15`**
- rows：**4**；win_rate：**0.0000**

**判讀**
- 雖然 q35 exact bucket 已達標，但 lane 內部仍保有明確 toxic sub-bucket；
- 這代表 exact-supported 只解決了 sample-support 問題，**沒有解決 lane-internal pathology**。

**下一步方向**
- exact-supported 驗證時必須保留 q15 veto 語義；
- 若 current bucket 轉成 q15，runtime 仍應直接 veto。

---

### P1. train / leaderboard 仍維持 dual-profile 狀態
**現象**
- global recommended：**`core_only`**
- train selected：**`core_plus_macro`**
- bull artifact 最新 bull all cohort 推薦：**`core_plus_macro_plus_4h_structure_shift`**
- leaderboard visible winner：**`core_only`**

**判讀**
- 這不是 support 不足造成的 blocked candidate，而是**達標後尚未重做 profile governance / retrain verification**；
- 若不處理，文件會宣稱 exact bucket 已 supported，但 train-path 仍停留在 pre-threshold fallback 狀態。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1554)**

**判讀**
- 這仍是**外部憑證 blocker**，不是 bull support 問題。

---

## 本輪已清掉的問題

### RESOLVED. exact-supported 狀態下 artifact / probe / summary 仍殘留 `proxy_boundary_inconclusive`
**現象（修前）**
- q35 exact support 已達 minimum support，但 `leaderboard_feature_profile_probe.json` 與 `heartbeat_741_summary.json` 仍保留 `proxy_boundary_inconclusive`；
- 這會把已解除的 support blocker 誤寫成 proxy 邊界未決，造成治理語義落後於真實狀態。

**本輪 patch + 證據**
- `scripts/bull_4h_pocket_ablation.py`
  - exact-supported 時，summary 現在固定輸出 `exact_bucket_supported_proxy_not_required`；
- `tests/test_bull_4h_pocket_ablation.py`
  - 新增 exact-supported regression；
- `tests/test_hb_leaderboard_candidate_probe.py`
  - 新增 leaderboard alignment regression；
- `python scripts/hb_parallel_runner.py --fast --hb 741`
  - 已重建 bull artifact / leaderboard probe / heartbeat summary；
- 驗證結果：
  - `data/leaderboard_feature_profile_probe.json.alignment.proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
  - `data/heartbeat_741_summary.json.bull_4h_pocket.support_pathology_summary.proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`

**狀態**
- **已修復**；現在所有主要 surface 都明確表示：
  - q35 exact bucket 已 supported；
  - proxy 不再是 blocker 判讀核心；
  - 之後治理應直接回到 exact bucket 驗證。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **確認 q35 exact support 是否正式跨過 50。** ✅
2. **把 exact-supported 狀態下的 proxy contract 從舊 blocker 文案改成明確非 blocker 文案。** ✅
3. **重跑 fast heartbeat，驗證 artifact / probe / summary 已零漂移。** ✅

### 本輪不做
- 不直接開放 live layers；
- 不把 q15 toxic pocket 視為已清除；
- 不把 source auth blocker 與 bull support 驗證混在一起。

---

## 下一輪 gate

- **Next focus:**
  1. 針對 **exact-bucket-supported** 狀態執行 bull post-threshold verification：train / leaderboard / bull artifact 應採哪個 profile，並留下至少一個真 patch / verify；
  2. 驗證 q15 toxic pocket 在 exact-supported 後仍維持 lane-internal veto，不得因 q35 support 達標而被淡化；
  3. 持續把 `fin_netflow` 當外部 auth blocker 管理。

- **Success gate:**
  1. next run 必須留下至少一個與 **exact-bucket post-threshold verification / train-path sync / leaderboard governance** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state=exact_live_bucket_supported`、`support_governance_route=exact_live_bucket_supported`、`exact_bucket_root_cause=exact_bucket_supported`、`proxy_boundary_verdict=exact_bucket_supported_proxy_not_required`、`exact_lane_bucket_verdict=toxic_sub_bucket_identified`、`allowed_layers` 在 artifact / probe / docs / summary 間持續零漂移；
  3. 若 current bucket 仍是 q35 且 rows ≥50，不得再把「support 不足」當 blocker；若 rows 再次跌回 <50，必須同輪恢復 under-minimum blocker 語義。

- **Fallback if fail:**
  - 若 train / leaderboard 無法收斂到 exact-supported 後的治理語義，下一輪升級為 `post_threshold_profile_governance_stalled`；
  - 若任一 surface 回退成 `proxy_boundary_inconclusive` 或 `proxy_governance_reference_only_exact_support_blocked`，立即視為 exact-supported governance regression；
  - 若 current bucket rows 再度跌破 50，必須恢復 support blocker 文案，不得硬保留 supported 結論。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 exact-supported 後的治理 contract 再擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀：
     - `data/heartbeat_741_summary.json`
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `docs/analysis/bull_4h_pocket_ablation.md`
     - `data/leaderboard_feature_profile_probe.json`
  2. 逐條確認：
     - `current_live_structure_bucket` 是否仍是 **`CAUTION|structure_quality_caution|q35`**；
     - `current_live_structure_bucket_rows` 是否仍 **≥50**，若否目前是多少；
     - `support_blocker_state` 是否仍是 **`exact_live_bucket_supported`**；
     - `support_governance_route` 是否仍是 **`exact_live_bucket_supported`**；
     - `proxy_boundary_verdict` 是否仍是 **`exact_bucket_supported_proxy_not_required`**；
     - `decision_quality_exact_live_lane_bucket_verdict` 是否仍是 **`toxic_sub_bucket_identified`**；
     - `decision_quality_exact_live_lane_toxic_bucket.bucket` 是否仍是 **`CAUTION|structure_quality_caution|q15`**；
     - `train_selected_profile` 是否仍停在 **`core_plus_macro`**，或已切到 exact-supported 後的新驗證結果；
     - `live_predict_probe.allowed_layers` 是否仍是 **0**，其原因是 gate/quality 還是其他 guardrail。
  3. 若以上條件大多仍成立，下一輪不得再把「support 達標」當成功；必須直接推進 **exact-bucket post-threshold verification / train-path sync / q15 toxic pocket 保守治理**。
