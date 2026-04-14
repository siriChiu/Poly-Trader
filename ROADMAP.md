# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 12:38 UTC — Heartbeat #727（leaderboard blocker-aware ranking synced）_

本文件只保留**目前已落地能力、當前主目標、下一步 gate**，不保留歷史 roadmap 敘事。

---

## 已完成

### Canonical heartbeat / diagnostics
- fast heartbeat 持續刷新：
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `issues.json`
  - numbered summary：`data/heartbeat_727_summary.json`
- leaderboard candidate probe 持續刷新：
  - `data/leaderboard_feature_profile_probe.json`

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**。
- 最新 DB 狀態（#727）：
  - Raw / Features / Labels = **21408 / 12837 / 42905**
  - simulated_pyramid_win = **0.5747**
- label freshness 正常：
  - 240m lag 約 **3.4h**
  - 1440m lag 約 **23.4h**

### 模型 / shrinkage / leaderboard governance
- global feature ablation 仍指向：
  - global winner = **`core_only`**
  - `current_full` 明顯較差（cv ≈ **0.5861**）
- train path 仍保留 support-aware fallback 語義：
  - current production-oriented profile = **`core_plus_macro`**
  - source = **`bull_4h_pocket_ablation.support_aware_profile`**
  - support cohort = **`bull_supported_neighbor_buckets_proxy`**
  - support rows = **84**
  - exact live bucket rows = **0**
- **本輪新完成**：leaderboard 已從 metadata-aware 升級為 **blocker-aware ranking**
  - 正式比較：**`core_only` / `current_full` / `core_plus_macro`**
  - 若 candidate 依賴 support cohort，但 `exact_live_bucket_rows <= 0`，會被標成 blocker 並在排序上降級
  - `/api/models/leaderboard` 與 probe 現在會回傳：
    - `selected_feature_profile_blocker_applied`
    - `selected_feature_profile_blocker_reason`
    - `feature_profile_candidate_diagnostics`
- probe 已證明這不是口頭承諾：
  - `data/leaderboard_feature_profile_probe.json` 顯示 top model 現在選到 **`core_only`**
  - 同時保留 `core_plus_macro` diagnostics：
    - `support_rows=84`
    - `exact_live_bucket_rows=0`
    - `blocker_reason=unsupported_exact_live_structure_bucket`

### Live guardrail / bull blocker
- live predictor 仍正確保守：
  - regime = **bull**
  - gate = **CAUTION**
  - entry quality = **D**
  - allowed layers = **0**
  - guardrail reason = `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade`
- `bull_4h_pocket_ablation.live_context.current_live_structure_bucket_rows` 仍是 **0**。
- exact live lane 仍只有 **17 rows**，而且 quality 為負。

### Source blocker
- `fin_netflow` 仍是 **auth_missing**。
- forward archive 雖持續累積，但未補 `COINGLASS_API_KEY` 前，coverage 不會改善。

---

## 當前主目標

### 目標 A：維持 leaderboard blocker-aware ranking，避免 0-support fallback 再次被誤選
現在已經完成的，是把 `core_only`、`current_full`、`core_plus_macro` 正式放進 candidate flow，並讓 `core_plus_macro` 在 `exact_live_bucket_rows=0` 時被 blocker-aware 排序降級。

接下來主目標不是再補一份解釋，而是持續確保：
- `feature_profile_candidate_diagnostics`
- `selected_feature_profile_blocker_*`
- `feature_profile_support_rows`
- `feature_profile_exact_live_bucket_rows`
在 heartbeat / API / probe / docs 中維持同一語義。

### 目標 B：bull live exact bucket 0-support 仍是正式 deployment blocker
目前 live path 仍是：
- **bull / CAUTION / D / 0 layers**
- exact live lane **17 rows**
- current live structure bucket **0 support rows**

因此接下來主目標仍不是放寬 guardrail，而是：
- 繼續把 exact bucket 0-support 視為正式 blocker；
- 只在 exact bucket / supported-neighbor-buckets 證據鏈上繼續治理；
- 如果 exact bucket 還是 0 rows，就維持 `0 layers`，不准拿 broader spillover lane 假裝已解。

### 目標 C：保持 train fallback 與 leaderboard winner 的雙軌語義清楚
目前存在兩條都正確、但不能混寫的語義：
- global shrinkage winner = **`core_only`**
- bull support-aware train fallback = **`core_plus_macro`**

接下來要做的，不是消滅其中一條，而是把兩條語義在 heartbeat / probe / docs 中持續對齊，避免又回到「文件看不出誰是 winner、誰只是 fallback」的漂移狀態。

### 目標 D：維持 source auth blocker 與模型 blocker 分離治理
- `fin_netflow` 目前仍是 **auth_missing**。
- 這是外部 source blocker，不可混進 leaderboard / calibration / feature-profile patch 的成功敘事中。

---

## 接下來要做

### 1. 追蹤 bull exact bucket 是否從 0 rows 轉為可用 support
要做：
- 每輪先讀 `data/bull_4h_pocket_ablation.json` 與 `data/live_predict_probe.json`
- 確認 `current_live_structure_bucket_rows` 是否仍為 0
- 若仍為 0：維持 blocker；若 >0：同步更新 leaderboard / probe / docs

### 2. 維持 blocker-aware candidate diagnostics 的 machine-readable contract
要做：
- 確保 `data/leaderboard_feature_profile_probe.json` 每輪都能看到：
  - `selected_feature_profile`
  - `selected_feature_profile_blocker_*`
  - `feature_profile_candidate_diagnostics`
- 若 probe、API、heartbeat 任一條少欄位或語義不一致，下一輪優先修 contract，而不是補新分析

### 3. 維持雙 baseline 語義一致
要做：
- 保持下列兩條語義分開，但同時存在於正式工件中：
  - global winner = **`core_only`**
  - bull support-aware fallback = **`core_plus_macro`**
- 不允許 `current_full` 因歷史慣性回到安全預設
- 不允許 heartbeat 把 `core_plus_macro` 被 blocker 擋下的情況寫成「已被正式選中」

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source
- 不把它重新包裝成即將可用的主決策特徵

---

## 暫不優先

以下本輪後仍不排最前面：
- 新增更多 feature family
- 放寬 bull live guardrail
- UI 美化與 fancy controls
- 用 broader spillover lane 替 bull live path 解套

原因：
> 現在真正的瓶頸不是功能不夠，而是**bull exact bucket 仍無支持樣本，且雙軌 feature-profile 語義必須維持嚴格同步**。

---

## 成功標準

接下來幾輪工作的成功標準：
1. `data/leaderboard_feature_profile_probe.json` 持續能 machine-read blocked candidate diagnostics。
2. bull live exact structure bucket 若仍 0-support，heartbeat / leaderboard / probe / docs 都明確維持 blocker 語義；若不再 0，四條路徑要同輪同步更新。
3. `core_only` 與 `core_plus_macro` 的雙軌語義零漂移：前者是 global winner，後者是 bull support-aware fallback。
4. `current_full` 不再因歷史慣性被默認為安全預設。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 追蹤 bull `CAUTION|structure_quality_caution|q35` exact bucket 是否仍為 0 rows；
  2. 持續維持 `core_only`（leaderboard winner）與 `core_plus_macro`（train fallback）雙軌語義對齊；
  3. 持續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 能直接指出 `core_plus_macro` 是否仍被 `unsupported_exact_live_structure_bucket` 擋下；
  2. bull live exact bucket 0-support 的狀態，在 live probe / bull pocket artifact / leaderboard probe / docs 之間零漂移；
  3. 若 exact bucket rows 有變化，四條路徑能同輪同步更新結論。

- **Fallback if fail:**
  - exact bucket 若仍 0 support，維持 `0 layers`；
  - 若 blocker-aware diagnostics 缺欄位或漂移，下一輪先修 contract，不准退回人工解讀；
  - source auth 若未修，繼續標記 blocked，不准假裝 coverage 會自然恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 feature-profile / blocker contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_727_summary.json`。
  2. 再讀：
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
  3. 若 `selected_feature_profile`、`feature_profile_candidate_diagnostics[*].blocker_reason`、`current_live_structure_bucket_rows`、`execution_guardrail_reason` 四項有三項以上完全不變，下一輪不得只重跑 fast heartbeat；必須直接推進 **bull exact bucket 支持樣本治理 / 雙軌語義對齊**。