# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 13:39 UTC — Heartbeat #729（warning hygiene 已修，下一步轉向 bull exact bucket 支持樣本治理）_

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
  - `data/leaderboard_feature_profile_probe.json`
  - `issues.json`
  - numbered summary：`data/heartbeat_729_summary.json`

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**。
- 最新 DB 狀態（#729）：
  - Raw / Features / Labels = **21410 / 12839 / 42914**
  - simulated_pyramid_win = **0.5749**
- label freshness 正常：
  - 240m lag 約 **3.0h**
  - 1440m lag 約 **23.4h**

### 模型 / shrinkage / bull blocker governance
- global feature ablation 仍指向：
  - global winner = **`core_only`**
  - `current_full` cv ≈ **0.5767**，明顯弱於 shrinkage baseline
- train path 仍保留 support-aware fallback 語義：
  - current production-oriented profile = **`core_plus_macro`**
  - source = **`bull_4h_pocket_ablation.support_aware_profile`**
  - support cohort = **`bull_supported_neighbor_buckets_proxy`**
  - support rows = **84**
  - exact live bucket rows = **0**
- leaderboard candidate governance 仍有三條 machine-readable 證據鏈：
  1. `data/feature_group_ablation.json`：global shrinkage winner = **`core_only`**
  2. `model/last_metrics.json`：train fallback = **`core_plus_macro`**
  3. `data/leaderboard_feature_profile_probe.json`：
     - selected profile = **`core_only`**
     - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
     - blocked candidate = **`core_plus_macro` → unsupported_exact_live_structure_bucket**

### Live guardrail / bull blocker
- live predictor 仍正確保守：
  - regime = **bull**
  - gate = **CAUTION**
  - entry quality = **D**
  - allowed layers = **0**
  - guardrail reason = `decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade`
- `bull_4h_pocket_ablation.live_context.current_live_structure_bucket_rows` 仍是 **0**。
- exact live lane 仍只有 **17 rows**，而且 quality 為負。

### Warning hygiene（本輪新完成）
- `scripts/hb_leaderboard_candidate_probe.py` 已抑制已知 sklearn feature-name warnings。
- 驗證：`python scripts/hb_leaderboard_candidate_probe.py` → **stderr 0 行**。
- 這代表 fast heartbeat / cron 現在更容易看見**真正錯誤**，而不是被 probe 評估期間的無害 warnings 淹沒。

### Source blocker
- `fin_netflow` 仍是 **auth_missing**。
- forward archive 雖持續累積，但未補 `COINGLASS_API_KEY` 前，coverage 不會改善。

---

## 當前主目標

### 目標 A：把 bull exact bucket 0-support 從「持續觀測」推進到「支持樣本治理」
目前已完成的是：
- live probe、bull pocket artifact、leaderboard candidate probe、heartbeat summary 都能一致指出 **current live structure bucket rows = 0**。

下一步主目標不是再補第五份說明，而是：
- 直接推進 **bull exact bucket 支持樣本治理**；
- 若 exact bucket 仍 0，就留下新的治理 artifact / contract / patch，而不是再做同一句 blocker 重報；
- 若 >0，四條路徑必須同輪同步更新結論與 deployment 語義。

### 目標 B：維持 `core_only`（global winner）與 `core_plus_macro`（train fallback）雙軌語義清楚
目前雙軌已是 machine-readable contract：
- global winner = **`core_only`**
- bull support-aware train fallback = **`core_plus_macro`**
- blocked candidate reason = **`unsupported_exact_live_structure_bucket`**
- dual profile state = **`leaderboard_global_winner_vs_train_support_fallback`**

下一步主目標：
- heartbeat / probe / summary / docs 全部沿用同一套語義；
- 不允許 `core_plus_macro` 被誤寫成正式 leaderboard winner；
- 不允許 `current_full` 因歷史慣性回到安全預設。

### 目標 C：把 fast heartbeat 保持成可直接交接下一輪的閉環輸出
本輪完成後，fast heartbeat 已能穩定輸出：
- collect / IC / drift
- live predictor / live drilldown
- feature-group ablation
- bull 4H pocket ablation
- leaderboard candidate alignment
- **乾淨的 probe stderr（warning hygiene 已修）**

下一步主目標：
- 把 console / cron 可讀性優勢用在真正的 bull blocker root-cause 推進；
- 若 bull blocker 長期不變，下一輪直接推治理 patch，而不是再做手動交叉比對。

### 目標 D：維持 source auth blocker 與模型 blocker 分離治理
- `fin_netflow` 目前仍是 **auth_missing**。
- 這是外部 source blocker，不可混進 leaderboard / calibration / feature-profile patch 的成功敘事。

---

## 接下來要做

### 1. 直接推進 bull exact bucket 支持樣本治理
要做：
- 先讀 `data/heartbeat_729_summary.json`
- 再核對：
  - `data/live_predict_probe.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
- 若 `current_live_structure_bucket_rows` 仍為 0：下一輪要留下新的治理 artifact / patch / contract；若 >0：同輪同步更新 probe / summary / docs

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

### 3. 維持 warning hygiene 已修狀態，不再回退
要做：
- 若 `hb_leaderboard_candidate_probe.py` 或 fast heartbeat 再次出現 sklearn feature-name warnings，直接視為 regression；
- 讓 stderr 保持留給真實失敗訊號，不讓無害警告重新污染 cron 報告。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重新包裝成即將可用的主決策特徵。

---

## 暫不優先

以下本輪後仍不排最前面：
- 放寬 bull live guardrail
- 用 broader spillover lane 幫 exact bucket 解套
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸仍是 **bull exact bucket 0-support**；本輪已把 warning hygiene 清掉，但根因仍未消失。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **bull exact bucket 支持樣本治理** 直接相關的 patch / artifact / verify。
2. bull live exact structure bucket 若仍 0-support，heartbeat / live probe / bull pocket / leaderboard probe / docs 都明確維持 blocker 語義；若不再 0，四條路徑要同輪同步更新。
3. `core_only` 與 `core_plus_macro` 的雙軌語義零漂移：前者是 global winner，後者是 bull support-aware fallback。
4. `current_full` 不再因歷史慣性被默認為安全預設。
5. `fin_netflow` 繼續被正確標成 source auth blocker。
6. leaderboard candidate probe / fast heartbeat 的 warning hygiene 不回退。

---

## Next gate

- **Next focus:**
  1. 直接推進 **bull exact bucket 支持樣本治理**；
  2. 持續維持 `core_only`（leaderboard winner）與 `core_plus_macro`（train fallback）雙軌語義對齊；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下 bull exact bucket 治理的真 patch / 新 artifact / 驗證，不得只重跑 fast heartbeat；
  2. bull live exact bucket 0-support 的狀態，在 live probe / bull pocket artifact / leaderboard probe / docs 之間零漂移；
  3. 若 exact bucket rows 有變化，四條路徑能同輪同步更新結論。

- **Fallback if fail:**
  - exact bucket 若仍 0 support，維持 `0 layers`；
  - 若無法直接補樣本，至少把治理路徑 machine-readable 化，不能退回 warning hygiene 或敘述性報告；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull exact bucket governance contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_729_summary.json`。
  2. 再讀：
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/bull_4h_pocket_ablation.json`
  3. 若 `selected_feature_profile`、`dual_profile_state`、`live_current_structure_bucket_rows`、`blocked_candidate_profiles[0].blocker_reason`、`execution_guardrail_reason` 五項有四項以上完全不變，下一輪不得只重跑 fast heartbeat；必須直接推進 **bull exact bucket 支持樣本治理**。