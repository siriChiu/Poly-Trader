# ISSUES.md — Current State Only

_最後更新：2026-04-14 13:08 UTC — Heartbeat #728（leaderboard candidate 對齊進入 fast heartbeat）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#727）要求本輪處理
- **Next focus**：
  1. 追蹤 bull `CAUTION|structure_quality_caution|q35` exact bucket 是否仍為 0 rows；
  2. 持續維持 `core_only`（leaderboard winner）與 `core_plus_macro`（train fallback）雙軌語義對齊；
  3. 持續把 `fin_netflow` 當外部 source blocker 管理。
- **Success gate**：
  1. next run 能直接指出 `core_plus_macro` 是否仍被 `unsupported_exact_live_structure_bucket` 擋下；
  2. bull live exact bucket 0-support 的狀態，在 live probe / bull pocket artifact / leaderboard probe / docs 之間零漂移；
  3. 若 exact bucket rows 有變化，四條路徑能同輪同步更新結論。
- **Fallback if fail**：
  - exact bucket 若仍 0 support，維持 `0 layers`；
  - 若 blocker-aware diagnostics 缺欄位或漂移，下一輪先修 contract，不准退回人工解讀；
  - source auth 若未修，繼續標記 blocked，不准假裝 coverage 會自然恢復。

### 本輪承接結果
- **已處理**：
  - `scripts/hb_leaderboard_candidate_probe.py` 現在會把 **leaderboard winner / global shrinkage winner / train support-aware fallback / blocked candidates / live bull bucket state** 一次對齊輸出到 `data/leaderboard_feature_profile_probe.json`。
  - `scripts/hb_parallel_runner.py --fast` 現在會自動執行 leaderboard candidate probe，並把 `leaderboard_candidate_diagnostics` 寫進 numbered heartbeat summary。
  - `ARCHITECTURE.md` 已同步 fast heartbeat 的 leaderboard candidate governance contract。
- **仍未解**：
  - bull live exact bucket `CAUTION|structure_quality_caution|q35` 仍是 **0 rows**，runtime 仍必須維持 `0 layers`。
  - `core_plus_macro` 仍只是 **train support-aware fallback**，不是可部署的 leaderboard winner。
  - `fin_netflow` 仍是 **auth_missing**。
- **本輪明確不做**：
  - 不放寬 bull live guardrail。
  - 不把 broader spillover lane 當成 exact bucket 已修好。
  - 不把 `fin_netflow` auth blocker 誤包裝成本地 calibration 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_leaderboard_candidate_probe.py`
    - 新增 `alignment` 區塊，持久化：
      - `global_recommended_profile`
      - `train_selected_profile`
      - `train_selected_profile_source`
      - `train_support_cohort / train_support_rows / train_exact_live_bucket_rows`
      - `dual_profile_state`
      - `blocked_candidate_profiles`
      - `live_current_structure_bucket / rows`
      - `bull_support_aware_profile / bull_support_neighbor_rows`
  - `scripts/hb_parallel_runner.py`
    - fast heartbeat 新增自動執行 `scripts/hb_leaderboard_candidate_probe.py`
    - summary 新增 `leaderboard_candidate_diagnostics`
    - console 摘要現在直接顯示 `leaderboard / train / global / dual_profile_state / live_bucket_rows / blocked candidate`
  - `tests/test_hb_parallel_runner.py`
    - 新增/更新 regression coverage，驗證 summary 與 diagnostics 會保存 candidate-alignment 狀態
  - `ARCHITECTURE.md`
    - 補上 Heartbeat #728 fast-heartbeat leaderboard candidate governance contract

- **驗證（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py -q` → **9 passed**
  - `source venv/bin/activate && python scripts/hb_leaderboard_candidate_probe.py` → **通過，alignment 已輸出**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 728` → **通過**

### 資料 / 新鮮度 / canonical target
來自 Heartbeat #728：
- Raw / Features / Labels：**21409 / 12838 / 42912**
- 本輪增量：**+1 raw / +1 features / +7 labels**
- canonical target `simulated_pyramid_win`：**0.5749**
- 240m labels：**21557 rows / target_rows 12635 / lag_vs_raw 3.1h**
- 1440m labels：**12270 rows / target_rows 12270 / lag_vs_raw 23.1h**
- recent raw age：**約 4.4 分鐘**
- continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**17/30 pass**
- TW-IC：**26/30 pass**
- TW 歷史：**#728=26/30，#727=24/30，#726=23/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 100%**
  - avg_quality：**0.6660**
  - avg_pnl：**+0.0206**
  - avg_drawdown_penalty：**0.0354**
- 判讀：近期 canonical 視窗仍是**被支持的極端趨勢視窗**，不是 bull live pocket 已修好的證據。

### 模型 / shrinkage / leaderboard candidate 對齊
- `model/last_metrics.json`
  - train profile：**`core_plus_macro`**
  - source：**`bull_4h_pocket_ablation.support_aware_profile`**
  - support cohort：**`bull_supported_neighbor_buckets_proxy`**
  - support rows：**84**
  - exact live bucket rows：**0**
  - train accuracy / CV：**0.6333 / 0.7530**
- `data/feature_group_ablation.json`
  - global recommended profile：**`core_only`**
  - `current_full` cv：**0.5803**
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_only`**
  - dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
  - blocked candidate：**`core_plus_macro` → `unsupported_exact_live_structure_bucket`**
  - bull support-aware profile：**`core_plus_macro`**
  - bull supported-neighbor rows：**84**
  - live current structure bucket rows：**0**
- 判讀：**雙軌語義現在已 machine-readable 對齊**；train fallback 與 leaderboard winner 的分工更清楚，但 exact bucket 仍未解。

### Live predictor / bull blocker
來自 `data/live_predict_probe.json`：
- signal：**HOLD**
- confidence：**0.149944**
- regime：**bull**
- gate：**CAUTION**
- entry quality：**0.3931 (D)**
- allowed layers：**0 → 0**
- should trade：**false**
- calibration scope：**`regime_label`**
- execution guardrail：
  - `decision_quality_below_trade_floor`
  - `unsupported_exact_live_structure_bucket_blocks_trade`
- exact live lane：**17 rows / win_rate 0.2353 / quality -0.0626 / true_negative_rows 13 (76.47%)**
- worst narrowed scope：**`regime_label+entry_quality_label` = 147 rows / win_rate 0.0748 / quality -0.2098**
- current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows = 0**
- 判讀：guardrail 仍是在**正確擋壞 pocket**，不是 guardrail 過度保守。

### Source blockers
- blocked sparse features：**8 個**
- blocker 分布：
  - `archive_required`: **3**
  - `snapshot_only`: **4**
  - `short_window_public_api`: **1**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）
- 判讀：這仍是**外部授權 blocker**。

---

## 目前有效問題

### P1. bull live exact bucket 仍是 0-support，runtime 必須維持 0 layers
**現象**
- live 仍是 **bull / CAUTION / D / 0 layers**。
- `unsupported_exact_live_structure_bucket_blocks_trade` 仍成立。
- current live structure bucket：`CAUTION|structure_quality_caution|q35`
- `data/bull_4h_pocket_ablation.json`：**current_live_structure_bucket_rows = 0**
- `data/live_predict_probe.json`：exact live lane **17 rows**，且 quality 為負。

**判讀**
- 目前 blocker 不是文件不一致，而是**exact bucket 本身沒有可用支持樣本**。
- 任何 broader lane 的較高 win rate，都不能當成 exact bucket 已可部署。

**下一步方向**
- 維持 `0 layers`。
- 下一輪優先核對 exact bucket rows 是否從 0 變成 >0；若沒有，繼續把它當 deployment blocker，而不是再補故事。

---

### P1. train fallback 與 leaderboard winner 仍是雙軌，現在已可 machine-read，但尚未收斂到同一條可部署路徑
**現象**
- train path：**`core_plus_macro`**（support-aware fallback）
- leaderboard winner：**`core_only`**（global shrinkage winner）
- `data/leaderboard_feature_profile_probe.json` 已明確輸出：
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `blocked_candidate_profiles[0].blocker_reason = unsupported_exact_live_structure_bucket`

**判讀**
- 這代表語義治理已經落地，但**根本衝突仍存在**：train fallback 仍依賴 exact bucket=0 的 bull neighbor proxy。
- 目前可以觀測，不代表已可收斂成單一路徑。

**下一步方向**
- 下一輪繼續以 exact bucket support 是否改善作為第一判斷。
- 若 exact bucket 仍 0，維持雙 baseline；不得把 `core_plus_macro` 誤寫成已被 leaderboard 正式選中。

---

### P1. leaderboard candidate probe / fast heartbeat 仍有 sklearn feature-name warnings，輸出過於吵雜
**現象**
- `scripts/hb_leaderboard_candidate_probe.py` 與 fast heartbeat 在 stderr 中仍會大量出現：
  - `UserWarning: X has feature names, but LogisticRegression / MLPClassifier was fitted without feature names`

**判讀**
- 這不影響本輪 candidate alignment 事實，但會污染 fast heartbeat console 與 cron 報告可讀性。
- 目前只是 warning hygiene 問題，不是 bull blocker root cause。

**下一步方向**
- 在 bull exact bucket blocker 仍未解前，只列為次優先治理；除非 warnings 開始遮蔽真正錯誤，否則不升級到 P0。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- forward archive 雖然 ready，但內容仍是 auth_missing snapshot。

**判讀**
- 這仍是**外部憑證缺失 blocker**。
- 未補憑證前，不應列為主決策成熟特徵。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 leaderboard winner / train fallback / live bull bucket 狀態收斂成 machine-readable probe**。✅
2. **把該 probe 併入 fast heartbeat summary**，避免下一輪再手動比對多份 artifact。✅
3. **用 #728 事實覆寫 ISSUES / ROADMAP / ARCHITECTURE**，同步 bull blocker 與雙軌語義。✅

### 本輪不做
- 不放寬 bull live guardrail。
- 不把 broader spillover lane 當作 exact bucket 已修好。
- 不把 `fin_netflow` auth blocker 當本地 code 問題。

---

## 下一輪 gate

- **Next focus:**
  1. 先讀 `data/heartbeat_728_summary.json` 與 `data/leaderboard_feature_profile_probe.json`，確認 bull exact bucket 是否仍為 **0 rows**；
  2. 若仍是 0，持續把 `core_only`（leaderboard winner）與 `core_plus_macro`（train fallback）維持雙軌治理；
  3. 評估是否需要處理 leaderboard probe / fast heartbeat 的 sklearn warning hygiene。

- **Success gate:**
  1. `leaderboard_candidate_diagnostics` 能直接 machine-read：`leaderboard/global/train/live_bucket_rows/blocked_candidate_profiles`；
  2. 若 bull exact bucket 仍 0，heartbeat 必須明確維持 `0 layers` 並指出 blocker 未解；若 >0，必須同輪同步更新 live probe / bull pocket / leaderboard probe / docs；
  3. 文件、probe、heartbeat summary 對 `core_only`、`core_plus_macro`、bull blocker 的敘述零漂移。

- **Fallback if fail:**
  - 若 exact bucket 仍 0 support，繼續維持 `0 layers`，不得退回 broader lane 敘事；
  - 若 probe / summary 缺欄位或漂移，下一輪優先修 contract；
  - 若 warning hygiene 尚未修，至少不得讓 warnings 蓋掉真正錯誤訊息。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 fast-heartbeat / candidate-governance contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_728_summary.json`、`data/leaderboard_feature_profile_probe.json`、`data/live_predict_probe.json`、`data/bull_4h_pocket_ablation.json`。
  2. 逐條確認：
     - `leaderboard_candidate_diagnostics.selected_feature_profile` 是否仍為 `core_only`；
     - `leaderboard_candidate_diagnostics.dual_profile_state` 是否仍為 `leaderboard_global_winner_vs_train_support_fallback`；
     - `leaderboard_candidate_diagnostics.live_current_structure_bucket_rows` 是否仍為 0；
     - `leaderboard_candidate_diagnostics.blocked_candidate_profiles[0].blocker_reason` 是否仍為 `unsupported_exact_live_structure_bucket`；
     - `live_predict_probe.execution_guardrail_reason` 是否仍包含 `unsupported_exact_live_structure_bucket_blocks_trade`。
  3. 若以上五項有四項以上完全不變，下一輪不得只重報數字；必須直接推進 **bull exact bucket 支持樣本治理** 或 **leaderboard probe warning hygiene** 其中之一。