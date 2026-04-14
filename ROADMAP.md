# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 13:08 UTC — Heartbeat #728（leaderboard candidate 對齊納入 fast heartbeat）_

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
  - numbered summary：`data/heartbeat_728_summary.json`
- **本輪新完成**：fast heartbeat 會同步刷新：
  - `data/leaderboard_feature_profile_probe.json`
  - summary 內的 `leaderboard_candidate_diagnostics`

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**。
- 最新 DB 狀態（#728）：
  - Raw / Features / Labels = **21409 / 12838 / 42912**
  - simulated_pyramid_win = **0.5749**
- label freshness 正常：
  - 240m lag 約 **3.1h**
  - 1440m lag 約 **23.1h**

### 模型 / shrinkage / bull blocker governance
- global feature ablation 仍指向：
  - global winner = **`core_only`**
  - `current_full` 明顯較差（cv ≈ **0.5803**）
- train path 仍保留 support-aware fallback 語義：
  - current production-oriented profile = **`core_plus_macro`**
  - source = **`bull_4h_pocket_ablation.support_aware_profile`**
  - support cohort = **`bull_supported_neighbor_buckets_proxy`**
  - support rows = **84**
  - exact live bucket rows = **0**
- leaderboard candidate governance 已經有三條 machine-readable 證據鏈：
  1. `data/feature_group_ablation.json`：global shrinkage winner = **`core_only`**
  2. `model/last_metrics.json`：train fallback = **`core_plus_macro`**
  3. `data/leaderboard_feature_profile_probe.json`：
     - selected profile = **`core_only`**
     - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
     - blocked candidate = **`core_plus_macro` → unsupported_exact_live_structure_bucket**
- 這代表：
  - leaderboard winner、train fallback、bull live blocker 三條語義已**可直接被 heartbeat machine-read**。

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

### 目標 A：把 bull exact bucket 0-support 持續當成 deployment blocker，而不是分析註腳
目前已完成的是：
- live probe、bull pocket artifact、leaderboard candidate probe、heartbeat summary 都能說出 **current live structure bucket rows = 0**。

接下來主目標不是再補一份文字說明，而是：
- 每輪先確認 exact bucket rows 是否仍為 0；
- 若仍為 0，就維持 `0 layers`；
- 若 >0，四條路徑必須同輪同步更新結論。

### 目標 B：維持 `core_only`（global winner）與 `core_plus_macro`（train fallback）雙軌語義清楚
目前雙軌已經不是口頭描述，而是 machine-readable contract：
- global winner = **`core_only`**
- bull support-aware train fallback = **`core_plus_macro`**
- blocked candidate reason = **`unsupported_exact_live_structure_bucket`**
- dual profile state = **`leaderboard_global_winner_vs_train_support_fallback`**

接下來主目標不是消滅其中一條，而是保持：
- heartbeat / probe / summary / docs 全部沿用同一套語義；
- 不允許 `core_plus_macro` 被誤寫成正式 leaderboard winner；
- 不允許 `current_full` 因歷史慣性回到安全預設。

### 目標 C：把 fast heartbeat 保持成可直接交接下一輪的閉環輸出
本輪新增後，fast heartbeat 已能自動帶出：
- collect / IC / drift
- live predictor / drilldown
- feature-group ablation
- bull 4H pocket ablation
- leaderboard candidate alignment

接下來要做的是：
- 確保這些 artifact 不漂移；
- 若 bull blocker 長期不變，下一輪直接推 patch，不再重複手動交叉比對。

### 目標 D：維持 source auth blocker 與模型 blocker 分離治理
- `fin_netflow` 目前仍是 **auth_missing**。
- 這是外部 source blocker，不可混進 leaderboard / calibration / feature-profile patch 的成功敘事。

---

## 接下來要做

### 1. 每輪先檢查 bull exact bucket 是否仍為 0 rows
要做：
- 先讀 `data/heartbeat_728_summary.json`
- 再核對：
  - `data/live_predict_probe.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
- 若 `current_live_structure_bucket_rows` 仍為 0：維持 blocker；若 >0：同輪同步更新 probe / summary / docs

### 2. 維持 dual-profile 語義一致
要做：
- 保持下列兩條語義分開，但都留在正式工件中：
  - global winner = **`core_only`**
  - bull support-aware fallback = **`core_plus_macro`**
- heartbeat summary 必須能直接 machine-read：
  - `selected_feature_profile`
  - `global_recommended_profile`
  - `train_selected_profile`
  - `dual_profile_state`
  - `blocked_candidate_profiles`

### 3. 視需要處理 leaderboard probe / fast heartbeat warning hygiene
要做：
- 觀察 `scripts/hb_leaderboard_candidate_probe.py` 是否持續被 sklearn feature-name warnings 淹沒
- 若 warnings 開始遮蔽真正錯誤，再把 warning hygiene 升級為正式 patch 目標

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source
- 不把它重新包裝成即將可用的主決策特徵

---

## 暫不優先

以下本輪後仍不排最前面：
- 放寬 bull live guardrail
- 用 broader spillover lane 幫 exact bucket 解套
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸仍是 **bull exact bucket 0-support**；本輪已把觀測與對齊機制補齊，但根因還沒消失。

---

## 成功標準

接下來幾輪工作的成功標準：
1. `leaderboard_candidate_diagnostics` 持續能 machine-read：`leaderboard / global / train / live_bucket_rows / blocked_candidate_profiles`。
2. bull live exact structure bucket 若仍 0-support，heartbeat / live probe / bull pocket / leaderboard probe / docs 都明確維持 blocker 語義；若不再 0，四條路徑要同輪同步更新。
3. `core_only` 與 `core_plus_macro` 的雙軌語義零漂移：前者是 global winner，後者是 bull support-aware fallback。
4. `current_full` 不再因歷史慣性被默認為安全預設。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 追蹤 bull `CAUTION|structure_quality_caution|q35` exact bucket 是否仍為 0 rows；
  2. 持續維持 `core_only`（leaderboard winner）與 `core_plus_macro`（train fallback）雙軌語義對齊；
  3. 視需要處理 leaderboard probe / fast heartbeat 的 warning hygiene。

- **Success gate:**
  1. next run 能直接指出 `leaderboard_candidate_diagnostics.dual_profile_state` 與 `blocked_candidate_profiles`；
  2. bull live exact bucket 0-support 的狀態，在 live probe / bull pocket artifact / leaderboard probe / docs 之間零漂移；
  3. 若 exact bucket rows 有變化，四條路徑能同輪同步更新結論。

- **Fallback if fail:**
  - exact bucket 若仍 0 support，維持 `0 layers`；
  - 若 candidate probe 或 summary 缺欄位 / 漂移，下一輪先修 contract；
  - 若 warning hygiene 未修，至少不得讓 warnings 蓋掉真正錯誤。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 fast-heartbeat / candidate-governance contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_728_summary.json`。
  2. 再讀：
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
  3. 若 `selected_feature_profile`、`dual_profile_state`、`live_current_structure_bucket_rows`、`blocked_candidate_profiles[0].blocker_reason`、`execution_guardrail_reason` 五項有四項以上完全不變，下一輪不得只重跑 fast heartbeat；必須直接推進 **bull exact bucket 支持樣本治理** 或 **warning hygiene** 其中之一。