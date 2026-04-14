# ISSUES.md — Current State Only

_最後更新：2026-04-14 12:38 UTC — Heartbeat #727（leaderboard blocker-aware ranking）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#726）要求本輪處理
- **Next focus**：
  1. 把 `feature_profile_support_rows / exact_live_bucket_rows / support_cohort` 接進 leaderboard candidate ranking / reject 規則；
  2. 對 bull `CAUTION|structure_quality_caution|q35` 繼續做 support-aware / bucket-aware 治理；
  3. 持續把 `fin_netflow` 當外部 source blocker 管理。
- **Success gate**：
  1. next run 能直接指出 leaderboard 哪些 feature-profile candidates 被 support/blocker 規則降級或淘汰；
  2. bull live exact bucket 0-support 已正式變成 ranking / deployment blocker 語義；
  3. 文件與 artifact 對 blocker / feature-profile selection 零漂移。
- **Fallback if fail**：
  - exact bucket 若仍 0 support，維持 `0 layers`；
  - 若 blocker-aware ranking 還沒落地，至少保留 machine-readable probe，不允許回退到不可觀測狀態；
  - source auth 若未修，繼續標記 blocked。

### 本輪承接結果
- **已處理**：
  - `backtesting/model_leaderboard.py` 已把 feature-profile candidate selection 升級為 **blocker-aware ranking**。
  - `/api/models/leaderboard` 與 `data/leaderboard_feature_profile_probe.json` 現在可 machine-read：
    - `selected_feature_profile_blocker_applied`
    - `selected_feature_profile_blocker_reason`
    - `feature_profile_candidate_diagnostics`
  - `core_plus_macro` 在 `support_rows=84`、但 `exact_live_bucket_rows=0` 的情況下，已被正式標成 `unsupported_exact_live_structure_bucket` 並在排序上降級；top profile 已切回 `core_only`。
- **未處理完成**：
  - bull live exact bucket `CAUTION|structure_quality_caution|q35` 仍是 **0 rows**，runtime guardrail 仍必須維持 `0 layers`。
  - `fin_netflow` 仍是 `auth_missing`，不是本地 ranking patch 可以解的問題。
- **本輪明確不做**：
  - 不放寬 bull live guardrail。
  - 不新增新 feature family。
  - 不把 `fin_netflow` auth blocker 誤寫成 calibration 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `backtesting/model_leaderboard.py`
    - 新增 `feature_profile_blocker_assessment()`
    - candidate selection key 現在先吃 `blocker_applied / exact_live_bucket_rows / support_rows`
    - `last_model_statuses` 新增 `selected_feature_profile_blocker_*` 與 `feature_profile_candidate_diagnostics`
  - `server/routes/api.py`
    - `/api/models/leaderboard` payload 新增 blocker-aware ranking 欄位與 candidate diagnostics
  - `scripts/hb_leaderboard_candidate_probe.py`
    - probe 現在會把 blocker state 與 candidate diagnostics 一起持久化
  - `tests/test_model_leaderboard.py`
    - 新 regression test：即使 `core_plus_macro` 分數更高，只要 `exact_live_bucket_rows=0` 仍必須被降級
  - `ARCHITECTURE.md`
    - 同步補上 Heartbeat #727 blocker-aware ranking contract

- **驗證（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_model_leaderboard.py -q` → **19 passed**
  - `source venv/bin/activate && python -m pytest tests/test_train_target_metrics.py tests/test_model_leaderboard.py -q` → **27 passed**
  - `source venv/bin/activate && python scripts/hb_leaderboard_candidate_probe.py` → **通過，probe 已顯示 blocked candidate diagnostics**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 727` → **通過**

### 資料 / 新鮮度 / canonical target
來自 Heartbeat #727：
- Raw / Features / Labels：**21408 / 12837 / 42905**
- 本輪增量：**+1 raw / +1 features / +3 labels**
- canonical target `simulated_pyramid_win`：**0.5747**
- 240m labels：**21554 rows / target_rows 12632 / lag_vs_raw 3.4h**
- 1440m labels：**12266 rows / target_rows 12266 / lag_vs_raw 23.4h**
- recent raw age：**約 2 分鐘**
- continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**17/30 pass**
- TW-IC：**24/30 pass**
- TW 歷史：**#727=24/30，#726=23/30，#725=23/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 100%**
  - avg_quality：**0.6650**
  - avg_pnl：**+0.0205**
  - avg_drawdown_penalty：**0.0358**
- 判讀：recent 250 仍是**被支持的極端趨勢視窗**；不能拿這個 chop-dominated 視窗替 bull live pocket 解套。

### 模型 / shrinkage / leaderboard blocker-aware ranking
- `model/last_metrics.json`
  - target：`simulated_pyramid_win`
  - train accuracy：**0.6333**
  - cv accuracy：**0.7530**
  - cv std：**0.0935**
  - cv worst：**0.6121**
  - train path feature profile：**`core_plus_macro`**
  - source：**`bull_4h_pocket_ablation.support_aware_profile`**
  - support cohort：**`bull_supported_neighbor_buckets_proxy`**
  - support rows：**84**
  - exact live bucket rows：**0**
- `data/feature_group_ablation.json`
  - `recommended_profile`：**`core_only`**
  - `core_only` cv：**0.7484**
  - `current_full` cv：**0.5861**
- `data/leaderboard_feature_profile_probe.json`
  - top model：**`rule_baseline`**
  - selected feature profile：**`core_only`**
  - selected feature profile source：**`feature_group_ablation.recommended_profile`**
  - feature profiles evaluated：**[`core_only`, `current_full`, `core_plus_macro`]**
  - `core_plus_macro` candidate diagnostics：
    - `support_rows=84`
    - `exact_live_bucket_rows=0`
    - `blocker_applied=true`
    - `blocker_reason=unsupported_exact_live_structure_bucket`
- 判讀：**carry-forward 要求的 blocker-aware ranking 已落地**；leaderboard 不再只是顯示 metadata，而是正式把 0-support exact bucket 視為 candidate blocker。

### Live predictor / bull blocker
來自 `data/live_predict_probe.json`：
- signal：**HOLD**
- confidence：**0.139525**
- regime：**bull**
- gate：**CAUTION**
- entry quality：**0.3651 (D)**
- allowed layers：**0 → 0**
- should trade：**false**
- calibration scope：**`regime_label`**
- execution guardrail：
  - `decision_quality_below_trade_floor`
  - `unsupported_exact_live_structure_bucket_blocks_trade`
- exact live lane：**17 rows / win_rate 0.2353 / quality -0.0626 / true_negative_rows 13 (76.47%)**
- worst narrowed scope：**`regime_label+entry_quality_label` = 147 rows / win_rate 0.0748 / quality -0.2098**
- `bull_4h_pocket_ablation.live_context.current_live_structure_bucket_rows`：**0**
- 判讀：runtime guardrail 仍是在**正確擋壞 pocket**；問題不是 guardrail 太保守，而是 exact bucket 仍無支持樣本。

### Source blockers
- blocked sparse features：**8 個**
- blocker 分布：
  - `archive_required`: **3**
  - `snapshot_only`: **4**
  - `short_window_public_api`: **1**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）
- 判讀：這仍是**外部授權 blocker**，不是本地 leaderboard / calibration patch 的後續工作。

---

## 目前有效問題

### P1. bull live exact bucket 仍是 0-support，runtime 仍需 0 layers
**現象**
- live 仍是 **bull / CAUTION / D / 0 layers**。
- `unsupported_exact_live_structure_bucket_blocks_trade` 仍成立。
- current live structure bucket：`CAUTION|structure_quality_caution|q35`
- **current live structure bucket rows = 0**。
- exact live lane 僅 **17 rows**，而且勝率 / quality 都差。

**判讀**
- guardrail 現在是在**正確阻擋壞 pocket**，不是 guardrail 故障。
- 現在 blocker 已經同步進 leaderboard ranking；但 live pocket 本身仍未獲得新支持樣本。

**下一步方向**
- 先維持 `0 layers`。
- 下一輪要把 candidate diagnostics 與 bull pocket artifact 對齊到 heartbeat 報告，持續追 exact bucket 是否從 0 變成可用樣本。

---

### P1. train path 與 leaderboard path 仍處於「support-aware fallback vs global winner」雙軌狀態
**現象**
- train path 仍採 **`core_plus_macro`**（因 bull support-aware fallback）。
- leaderboard top candidate 已改回 **`core_only`**（因 `core_plus_macro` 被 0-support blocker 降級）。

**判讀**
- 這不是文件漂移，而是系統刻意保留的兩條語義：
  - global shrinkage winner = `core_only`
  - bull support-aware fallback = `core_plus_macro`
- 但 exact bucket 仍 0 rows，代表 support-aware fallback **目前不可直接作為 leaderboard / deployment winner**。

**下一步方向**
- 繼續保留雙 baseline，但必須讓後續 artifact 明確區分「train fallback」與「leaderboard winner」，避免再次混寫成同一個結論。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage 仍為 **0.0%**。
- latest status：**auth_missing**。
- forward archive 已 ready，但內容仍是 auth_missing snapshot。

**判讀**
- 這仍是**外部憑證缺失 blocker**。
- 在未補憑證前，不應列為主決策成熟特徵。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 leaderboard candidate ranking 正式升級為 blocker-aware**，讓 0-support exact bucket 會真的被降級。✅
2. **把 blocker 診斷持久化到 API / probe**，讓 heartbeat 可 machine-read 哪個 feature profile 為何被擋。✅
3. **用 #727 最新事實覆寫 ISSUES / ROADMAP / ARCHITECTURE**，同步 train fallback、leaderboard winner、live guardrail、source blocker 四條語義。✅

### 本輪不做
- 不放寬 bull live guardrail。
- 不新增新 feature family。
- 不把 `fin_netflow` auth blocker 當本地 code issue。

---

## 下一輪 gate

- **Next focus:**
  1. 持續追 `CAUTION|structure_quality_caution|q35` exact bucket 是否從 **0 rows** 轉為可支撐樣本；
  2. 把 train fallback（`core_plus_macro`）與 leaderboard winner（`core_only`）的雙軌語義持續同步到 heartbeat / probe / 文件；
  3. 持續把 `fin_netflow` 保留為 source auth blocker。

- **Success gate:**
  1. `data/leaderboard_feature_profile_probe.json` 持續能 machine-read blocked candidate reason；
  2. 若 bull exact bucket 仍 0 rows，heartbeat 必須明確維持 `0 layers` 並指出 blocker 未解；若不再是 0，必須同步反映在 leaderboard / live probe / docs；
  3. heartbeat / ISSUES / ROADMAP / ARCHITECTURE / probe 對 `core_only`、`core_plus_macro`、bull blocker、source blocker 的敘述完全一致。

- **Fallback if fail:**
  - 若 exact bucket 仍 0 support，繼續維持 `0 layers`，不得拿 broader spillover lane 假裝已解；
  - 若 train / leaderboard 雙軌語義又開始漂移，下一輪優先修文件與 probe contract，而不是再補新分析；
  - 若 `COINGLASS_API_KEY` 仍缺，繼續把 `fin_netflow` 視為 blocked research source。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 feature-profile / blocker contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_727_summary.json`、`data/leaderboard_feature_profile_probe.json`、`data/live_predict_probe.json`、`data/bull_4h_pocket_ablation.json`。
  2. 逐條確認：
     - `leaderboard_feature_profile_probe.top_model.selected_feature_profile` 是否仍為 `core_only`；
     - `feature_profile_candidate_diagnostics` 是否仍把 `core_plus_macro` 標成 `unsupported_exact_live_structure_bucket`；
     - `bull_4h_pocket_ablation.live_context.current_live_structure_bucket_rows` 是否仍為 0；
     - `execution_guardrail_reason` 是否仍包含 `unsupported_exact_live_structure_bucket_blocks_trade`。
  3. 若以上四項有三項以上完全不變，下一輪不得只重報數字；必須直接推進 **bull exact bucket 支持樣本治理 / 雙軌語義對齊**。