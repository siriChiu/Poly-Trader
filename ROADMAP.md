# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 12:12 UTC — Heartbeat #726（leaderboard feature-profile governance synced）_

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
  - numbered summary：`data/heartbeat_726_summary.json`
- Heartbeat #726 新增：
  - `scripts/hb_leaderboard_candidate_probe.py`
  - `data/leaderboard_feature_profile_probe.json`

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**。
- 最新 DB 狀態（#726）：
  - Raw / Features / Labels = **21407 / 12836 / 42902**
  - simulated_pyramid_win = **0.5747**
- label freshness 仍正常：
  - 240m lag 約 **3.4h**
  - 1440m lag 約 **23.4h**

### 模型 / shrinkage / candidate governance
- train path 已固定保留 support-aware feature profile 語義：
  - current production-oriented profile = **`core_plus_macro`**
  - source = **`bull_4h_pocket_ablation.support_aware_profile`**
  - support cohort = **`bull_supported_neighbor_buckets_proxy`**
  - support rows = **84**
  - exact live bucket rows = **0**
- global feature ablation 仍明確指出：
  - global winner = **`core_only`**
  - `current_full` 明顯較差
- **本輪新完成**：leaderboard / API 已正式接入 feature-profile candidate flow
  - 正式比較：**`core_only` / `core_plus_macro` / `current_full`**
  - `/api/models/leaderboard` 現在會回傳：
    - `selected_feature_profile`
    - `selected_feature_profile_source`
    - `feature_profiles_evaluated`
    - `feature_profile_support_cohort`
    - `feature_profile_support_rows`
    - `feature_profile_exact_live_bucket_rows`
- probe 已證明這不是口頭承諾：
  - `data/leaderboard_feature_profile_probe.json` 可 machine-read 目前 leaderboard 實際選到的 feature profile 與 support metadata

### Live guardrail / bull blocker
- live predictor 仍正確保守：
  - regime = **bull**
  - gate = **CAUTION**
  - entry quality = **D**
  - allowed layers = **0**
  - guardrail reason = `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade`
- `bull_4h_pocket_ablation.live_context.current_live_structure_bucket_rows` 仍是 **0**。

---

## 當前主目標

### 目標 A：把 feature-profile candidate flow 從「可見」推進成「會決定 ranking / deployment」
現在已經完成的，是把 `core_only` 與 `core_plus_macro` 接進 leaderboard 正式比較，並把結果序列化到 API / probe。

接下來真正的主目標不是再補一份分析，而是讓：
- `feature_profile_support_rows`
- `feature_profile_exact_live_bucket_rows`
- `support_cohort`
真正影響 candidate ranking / reject decision。

也就是說，下一步要把 leaderboard 從 **metadata-aware** 推進到 **blocker-aware**。

### 目標 B：把 bull live exact bucket 0-support 變成正式 deployment / ranking blocker
目前 live path 仍是：
- **bull / CAUTION / D / 0 layers**
- exact live lane **17 rows**
- current live structure bucket **0 support rows**

因此接下來的主目標不是放寬 guardrail，而是：
- 只在 exact bucket / supported-neighbor-buckets 兩條證據鏈上繼續治理；
- 若 exact bucket 仍無支持樣本，就讓 ranking / deployment contract 明確把它視為 blocker。

### 目標 C：維持 source auth blocker 與模型 blocker 分離治理
- `fin_netflow` 目前仍是 **auth_missing**。
- 這是外部 source blocker，不可被重新混進 leaderboard / calibration / feature-profile patch 成果中。

---

## 接下來要做

### 1. 將 support metadata 接入 leaderboard selection key / reject rule
要做：
- 在 leaderboard candidate 評估中正式消費：
  - `selected_feature_profile`
  - `feature_profile_support_rows`
  - `feature_profile_exact_live_bucket_rows`
  - `support_cohort`
- 讓 `0-support exact bucket` 能被視為 deployment blocker，而不是只出現在說明欄位。

為什麼這是最高優先：
- 本輪已解掉「沒有正式 candidate flow」；下一步若不把 support/blocker metadata 接進 selection，本質上仍會停在分析懂了、決策路徑半同步。

### 2. 繼續 bull exact bucket support-aware 治理
要做：
- 針對 current live bucket `CAUTION|structure_quality_caution|q35`：
  - 持續觀察 exact bucket support
  - 持續比較 supported-neighbor-buckets
  - 若 exact bucket 還是 0 rows，就正式維持 blocker
- 禁止：
  - 用 broader `regime_gate+entry_quality_label` spillover lane 放寬 bull live path
  - 把 chop-dominated lane 當成 bull calibration 代理

### 3. 維持雙 baseline 語義一致
要做：
- 保持下列兩條語義分開，但共同存在於正式工件中：
  - global winner = **`core_only`**
  - bull support-aware fallback = **`core_plus_macro`**
- 不允許 `current_full` 因歷史慣性再被視為安全預設。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source。
- 不把它重新包裝成即將可用的主決策特徵。

---

## 暫不優先

以下本輪後仍不排最前面：
- 新增更多 feature family
- 放寬 bull live guardrail
- UI 美化與 fancy controls
- 用 broader spillover lane 替 bull live path 解套

原因：
> 現在真正的瓶頸不是功能不夠，而是**feature-profile candidate flow 已正式化後，support/blocker 語義是否真正進入 ranking / deployment 決策本身**。

---

## 成功標準

接下來幾輪工作的成功標準：
1. leaderboard payload 不只顯示 `selected_feature_profile`，還能顯示某些候選如何因 `0-support exact bucket` 被降級或拒絕。
2. bull live exact structure bucket 不再只是 heartbeat 備註，而是正式 ranking / deployment contract 的一部分。
3. `core_only` 與 `core_plus_macro` 持續存在於正式 candidate flow，不再回退成只跑 dense `current_full`。
4. heartbeat / ISSUES / ROADMAP / ARCHITECTURE / probe 對 feature-profile selection 與 bull blocker 的敘述完全一致。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 將 `feature_profile_support_rows / exact_live_bucket_rows / support_cohort` 接進 leaderboard candidate ranking / reject 規則；
  2. 對 bull `CAUTION|structure_quality_caution|q35` 繼續做 support-aware / bucket-aware 治理；
  3. 持續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 能直接指出 leaderboard 哪些 feature-profile candidates 被 support/blocker 規則降級或淘汰；
  2. bull live exact bucket 0-support 已正式變成 ranking / deployment blocker 語義，而不是只在 heartbeat 報告中出現；
  3. 文件與 artifact 對 blocker / feature-profile selection 零漂移。

- **Fallback if fail:**
  - exact bucket 若仍 0 support，維持 `0 layers`；
  - 若 blocker-aware ranking 還沒落地，至少保留目前 machine-readable feature-profile probe，不允許回退到不可觀測狀態；
  - source auth 若未修，繼續標記 blocked，不准假裝 coverage 會自然恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 leaderboard ranking/reject contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_726_summary.json`。
  2. 再讀：
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
  3. 若 `selected_feature_profile`、`feature_profiles_evaluated`、`current_live_structure_bucket_rows` 三者都沒有新變化，下一輪必須直接推動 blocker-aware leaderboard ranking / reject rule，不得只重跑 fast heartbeat。