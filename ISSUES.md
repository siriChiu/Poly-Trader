# ISSUES.md — Current State Only

_最後更新：2026-04-14 12:12 UTC — Heartbeat #726（fast，leaderboard feature-profile candidate integration）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#725）要求本輪處理
- **Next focus**：
  1. 把 `core_only`（global）與 `core_plus_macro`（bull support-aware）一起接進正式 train / leaderboard candidate 流；
  2. 對 bull live `CAUTION|structure_quality_caution|q35` 做更細的 support/bucket shrinkage，不准再用 chop spillover 放寬；
  3. 持續把 `fin_netflow` 保留為 source auth blocker，直到憑證修復。
- **Success gate**：
  1. exact live structure bucket 不再是 0 rows，**或**已被正式升級成 machine-readable deployment blocker 並被 train/leaderboard path 消費；
  2. candidate evaluation 同時能比較 `core_only` 與 `core_plus_macro`，且結果進入正式 artifact / ranking；
  3. heartbeat summary / ISSUES / ROADMAP 對 bull blocker 與 source blocker 的敘述完全一致。
- **Fallback if fail**：若 exact live bucket 仍 0 support，維持 runtime guardrail 保守擋單，且把 blocker 直接寫成 deployment blocker；不得用 broader spillover lane 假裝已解。

### 本輪承接結果
- **已處理**：
  - 已把 `core_only` / `core_plus_macro` / `current_full` 正式接入 `backtesting/model_leaderboard.py` 候選評估，leaderboard 不再默默只跑 dense `current_full`。
  - `/api/models/leaderboard` 現在會輸出 `selected_feature_profile / selected_feature_profile_source / feature_profiles_evaluated / feature_profile_support_*`。
  - 新增 `scripts/hb_leaderboard_candidate_probe.py`，並產出 `data/leaderboard_feature_profile_probe.json`，讓心跳可以 machine-read leaderboard 選到的 feature profile。
- **未處理完成**：
  - bull live exact structure bucket 仍是 **0 rows**，runtime guardrail 仍必須維持 `0 layers`。
  - leaderboard 雖已能比較 feature profiles，但**尚未把 exact-bucket support rows 直接吃進 ranking / selection score**，目前仍屬 metadata-aware，而不是 blocker-aware ranking。
- **本輪明確不做**：
  - 不新增新 feature family。
  - 不放寬 bull live guardrail。
  - 不把 `fin_netflow` auth blocker 誤包裝成本地 feature-engine 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `backtesting/model_leaderboard.py`
    - 新增 feature-profile candidate flow，正式比較 `core_only` / support-aware `core_plus_macro` / `current_full`
    - leaderboard status 現在記錄 `selected_feature_profile`、`feature_profiles_evaluated`、support metadata
  - `server/routes/api.py`
    - `/api/models/leaderboard` payload 新增 feature-profile governance 欄位
  - `scripts/hb_leaderboard_candidate_probe.py`
    - 新 probe，輸出 `data/leaderboard_feature_profile_probe.json`
  - `tests/test_model_leaderboard.py`
    - 新 regression tests，鎖住 feature-profile candidate selection 與 API payload
  - `ARCHITECTURE.md`
    - 同步新增 leaderboard feature-profile candidate contract

- **驗證（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_model_leaderboard.py -q` → **18 passed**
  - `source venv/bin/activate && python -m pytest tests/test_train_target_metrics.py tests/test_model_leaderboard.py -q` → **26 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 726` → **通過**
  - `source venv/bin/activate && python scripts/hb_leaderboard_candidate_probe.py` → **通過，已產出 probe artifact**

### 資料 / 新鮮度 / canonical target
來自 Heartbeat #726：
- Raw / Features / Labels：**21407 / 12836 / 42902**
- 本輪增量：**+1 raw / +1 features / +2 labels**
- canonical target `simulated_pyramid_win`：**0.5747**
- 240m labels：**21553 rows / target_rows 12631 / lag_vs_raw 3.4h**
- 1440m labels：**12264 rows / target_rows 12264 / lag_vs_raw 23.4h**
- recent raw age：**約 2 分鐘**
- continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**17/30 pass**
- TW-IC：**23/30 pass**
- TW 歷史：**#726=23/30，#725=23/30，#720=22/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 100%**
  - avg_quality：**0.6647**
  - avg_pnl：**+0.0205**
  - avg_drawdown_penalty：**0.0356**
- 判讀：recent 250 仍是**被支持的極端趨勢視窗**，不是 generic corruption；不能拿它當 bull live lane 放寬依據。

### 模型 / shrinkage / leaderboard candidate integration
- `model/last_metrics.json`
  - target：`simulated_pyramid_win`
  - train accuracy：**0.6333**
  - cv accuracy：**0.7530**
  - cv std：**0.0935**
  - cv worst：**0.6121**
  - feature profile：**`core_plus_macro`**
  - feature profile source：**`bull_4h_pocket_ablation.support_aware_profile`**
  - support cohort：**`bull_supported_neighbor_buckets_proxy`**
  - support rows：**84**
  - exact live bucket rows：**0**
- `data/feature_group_ablation.json`
  - `recommended_profile`：**`core_only`**
  - `core_only` cv：**0.7510**
  - `current_full` cv：**0.5902**
- **新 machine-readable leaderboard 證據**：`data/leaderboard_feature_profile_probe.json`
  - top model：**`rule_baseline`**
  - selected deployment profile：**`standard`**
  - selected feature profile：**`core_plus_macro`**
  - selected feature profile source：**`bull_4h_pocket_ablation.support_aware_profile`**
  - feature profiles evaluated：**[`core_plus_macro`, `core_only`, `current_full`]**
  - support cohort：**`bull_supported_neighbor_buckets_proxy`**
  - support rows：**84**
  - exact live bucket rows：**0**
- 判讀：**carry-forward 要求的「`core_only` 與 `core_plus_macro` 一起進入正式 candidate flow」已完成**；現在缺口已收斂成「leaderboard 何時把 support/blocker metadata 變成 ranking 決策，而不只是可見欄位」。

### Live predictor / bull blocker
來自 `data/live_predict_probe.json`：
- signal：**HOLD**
- confidence：**0.152131**
- regime：**bull**
- gate：**CAUTION**
- entry quality：**0.3589 (D)**
- allowed layers：**0 → 0**
- should trade：**false**
- calibration scope：**`regime_label`**
- execution guardrail：
  - `decision_quality_below_trade_floor`
  - `unsupported_exact_live_structure_bucket_blocks_trade`
- exact live lane：**17 rows / win_rate 0.2353 / quality -0.0626 / true_negative_rows 13 (76.47%)**
- worst narrowed scope：**`regime_label+entry_quality_label` = 147 rows / win_rate 0.0748 / quality -0.2098**
- `bull_4h_pocket_ablation.live_context.current_live_structure_bucket_rows`：**0**

### Source blockers
- blocked sparse features：**8 個**
- blocker 分布：
  - `archive_required`: **3**
  - `snapshot_only`: **4**
  - `short_window_public_api`: **1**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）
- 判讀：這仍是**外部授權 blocker**，不是本地 calibration / leaderboard patch 能解的問題。

---

## 目前有效問題

### P1. bull live decision-quality blocker 仍未解除
**現象**
- live 仍是 **bull / CAUTION / D / 0 layers**。
- `unsupported_exact_live_structure_bucket_blocks_trade` 仍成立。
- current live structure bucket：`CAUTION|structure_quality_caution|q35`
- **current live structure bucket rows = 0**。
- exact live lane 僅 **17 rows**，而且勝率 / quality 都差。

**判讀**
- guardrail 現在是在**正確阻擋壞 pocket**，不是 guardrail 故障。
- blocker 仍是 **bull exact bucket 無支持樣本 + same-regime narrowed lane 品質極差**。

**下一步方向**
- 讓 leaderboard / ranking reason 直接吃進 `exact_live_bucket_rows` / `support_rows`，把 0-support 由 metadata 升級為 ranking / deployment blocker。

---

### P1. leaderboard 已接入 feature-profile candidates，但還不是 blocker-aware ranking
**現象**
- leaderboard 已正式比較 `core_only` / `core_plus_macro` / `current_full`。
- API / probe 已能 machine-read `selected_feature_profile` 與 support metadata。
- 目前 top probe 顯示選到 **`core_plus_macro` + `bull_supported_neighbor_buckets_proxy`**，exact live bucket rows 仍 **0**。

**判讀**
- 這輪已從「沒有正式 candidate flow」前進到「正式 flow 已存在」。
- 剩下缺口是：**support metadata 還沒成為 ranking score / blocker gating 本身**。

**下一步方向**
- 將 `feature_profile_support_rows / exact_live_bucket_rows / support_cohort` 接進 leaderboard candidate selection key 或 reject rule。
- 讓 heartbeat 不只看到「選了哪個 profile」，還能看到「為什麼某 profile 因 0-support 被降級或擋下」。

---

### P1. `current_full` 仍輸給 shrinkage baseline
**現象**
- `core_only`：**0.7510**
- `current_full`：**0.5902**
- 正式 train 仍採 `core_plus_macro`，原因是 bull support-aware fallback，不是 global winner。

**判讀**
- 問題不是 feature 不夠多，而是 **family 太重導致 variance 被放大**。
- 本輪已把這個 trade-off 正式帶入 leaderboard；下一步是讓 blocker-aware 規則決定何時允許 support-aware fallback 壓過 global winner。

---

### P1. sparse-source auth blocker 仍卡住 `fin_netflow`
**現象**
- `fin_netflow` coverage 仍為 **0.0%**。
- latest status：**auth_missing**。
- forward archive 持續累積，但內容仍是 auth_missing snapshot。

**判讀**
- 這仍是**外部憑證缺失 blocker**。
- 在未補憑證前，不應列為主決策成熟特徵。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 leaderboard 正式升級成 feature-profile candidate flow**，讓 `core_only` 與 `core_plus_macro` 進入正式 ranking。✅
2. **留下可 machine-read 的 leaderboard probe artifact**，讓下一輪不用再靠口頭描述。✅
3. **用 #726 最新事實覆寫 ISSUES / ROADMAP / ARCHITECTURE**，把 blocker、support、source 三條語義重新對齊。✅

### 本輪不做
- 不放寬 bull live guardrail。
- 不新增新 feature family。
- 不把 `fin_netflow` auth blocker 當成本地 patch 問題。

---

## 下一輪 gate

- **Next focus:**
  1. 把 `feature_profile_support_rows / exact_live_bucket_rows / support_cohort` 接進 leaderboard candidate ranking / reject 規則；
  2. 針對 bull exact bucket `CAUTION|structure_quality_caution|q35` 繼續做 support-aware / bucket-aware 治理，但禁止用 broader chop spillover 放寬；
  3. 持續把 `fin_netflow` 保留為 source auth blocker。

- **Success gate:**
  1. leaderboard payload 能 machine-read 哪些 candidate 因 `0-support exact bucket` 被降級、擋下或 fallback；
  2. exact live structure bucket 不再只是 heartbeat 附註，而是正式 ranking / deployment contract 的一部分；
  3. heartbeat / ISSUES / ROADMAP / ARCHITECTURE / probe 對 bull blocker 與 feature-profile selection 的敘述完全一致。

- **Fallback if fail:**
  - 若 exact live bucket 仍 0 support，繼續維持 `0 layers`，不得以 broader spillover lane 假裝已解；
  - 若 leaderboard 暫時無法做 blocker-aware ranking，至少保留 `selected_feature_profile + support metadata` machine-readable，並明示仍屬 metadata-aware fallback；
  - 若 `COINGLASS_API_KEY` 仍缺，繼續將 `fin_netflow` 視為 blocked research source。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 leaderboard ranking / reject contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_726_summary.json`、`data/leaderboard_feature_profile_probe.json`、`data/live_predict_probe.json`、`data/bull_4h_pocket_ablation.json`。
  2. 逐條確認：
     - `leaderboard_feature_profile_probe.top_model.feature_profiles_evaluated` 是否仍包含 `core_only` 與 `core_plus_macro`；
     - `selected_feature_profile_source` 是否仍是 support-aware fallback；
     - `current_live_structure_bucket_rows` 是否仍為 0；
     - `execution_guardrail_reason` 是否仍包含 `unsupported_exact_live_structure_bucket_blocks_trade`。
  3. 若以上四項有三項以上完全不變，下一輪不得只重報數字；必須直接推進 **blocker-aware leaderboard ranking / reject rule**。