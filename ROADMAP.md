# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 22:23 UTC — Heartbeat #743（本輪已把 leaderboard candidate governance 從「只看舊 snapshot」升級成「區分 current inputs 與 artifact recency」；同時重跑 train + fast heartbeat，確認目前主 blocker 是 **q35 exact-supported 已恢復，但 train artifact 仍停在 support-aware `core_plus_macro`**。）_

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
  - numbered summary：`data/heartbeat_743_summary.json`

### 本輪新完成：candidate probe 能分清 current inputs 與舊 snapshot
- `scripts/hb_leaderboard_candidate_probe.py` 已升級：
  - 新增 `alignment_evaluated_at`
  - 新增 `current_alignment_inputs_stale`
  - 新增 `current_alignment_recency`
  - 新增 `artifact_recency`
- `dual_profile_state` 現在不再因 `leaderboard_snapshot_created_at` 舊就一律回報 stale；
  - current inputs 新鮮時，會直接暴露當前治理差異；
  - 舊 snapshot 只保留在 `artifact_recency` 當背景訊號。
- `scripts/hb_parallel_runner.py` 已同步把上述欄位帶進 heartbeat summary / console。
- `ARCHITECTURE.md` 已同步這條 current-vs-snapshot alignment recency contract。

### 驗證能力
- `source venv/bin/activate && python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py tests/test_strategy_lab.py -q` → **38 passed**
- `source venv/bin/activate && python model/train.py` → **通過**
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 743` → **通過**

### 資料與 canonical target
- canonical target 仍統一為 **`simulated_pyramid_win`**
- 最新 DB 狀態（#743）：
  - Raw / Features / Labels = **21433 / 12862 / 43047**
  - simulated_pyramid_win = **0.5766**
- label freshness 正常：
  - 240m lag 約 **3.2h**
  - 1440m lag 約 **23.3h**

### IC / drift / live contract
- Global IC：**19/30**
- TW-IC：**26/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- drift primary window：**100**
  - interpretation：**supported_extreme_trend**
  - dominant regime：**bull 89.0%**
- live predictor：
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**D**
  - decision-quality label：**B**
  - allowed layers：**0**
  - current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows=90**
  - `decision_quality_exact_live_lane_bucket_verdict`：**`toxic_sub_bucket_identified`**
  - `decision_quality_exact_live_lane_toxic_bucket`：**`CAUTION|structure_quality_caution|q15` rows=4 / win_rate=0.0**

### 模型 / shrinkage / support-aware ranking
- global recommended profile：**`core_only`**
- bull all cohort recommended profile：**`core_plus_macro_plus_4h_structure_shift`**
- train selected profile：**`core_plus_macro`**
  - source：**`bull_4h_pocket_ablation.support_aware_profile`**
  - support cohort：**`bull_exact_live_lane_proxy`**
  - support rows：**396**
  - exact live bucket rows（train 使用時看到的）：**4**
- leaderboard selected profile：**`core_plus_macro_plus_4h_structure_shift`**
  - source：**`bull_4h_pocket_ablation.exact_supported_profile`**
  - support cohort：**`bull_all`**
  - support rows：**759**
  - exact live bucket rows：**90**
- dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
- alignment recency：
  - `current_alignment_inputs_stale = false`
  - `artifact_recency.alignment_snapshot_stale = true`
- bull pocket artifact（當前 live bucket）
  - `blocker_state = exact_live_bucket_supported`
  - `exact_bucket_root_cause = exact_bucket_supported`
  - `support_governance_route = exact_live_bucket_supported`
  - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
  - `exact_lane_bucket_verdict = toxic_sub_bucket_identified`

### Source blocker
- `fin_netflow` 仍是 **auth_missing**
- 未補 `COINGLASS_API_KEY` 前，不會進入主決策成熟特徵

---

## 當前主目標

### 目標 A：修 train artifact freshness / exact-supported train-frame parity
目前已確認：
- q35 exact-supported 已恢復；
- leaderboard 已回到 exact-supported `core_plus_macro_plus_4h_structure_shift`；
- train 仍停在 support-aware `core_plus_macro`。

下一步主目標：
- **讓 train 一定吃到最新 bull pocket / feature ablation artifact，而不是在 exact-supported 恢復後仍沿用 support-aware 舊 artifact**；
- 讓 train / leaderboard 對 exact-supported bull lane 使用同一個 profile，或至少把不能收斂的技術限制寫成 machine-readable contract。

### 目標 B：維持 q15 toxic pocket 與 q35 supported 的雙重語義
目前已明確：
- q35：**exact support 已到位且健康**
- q15：**lane-internal toxic sub-bucket**
- runtime deployment：**仍保守（allowed_layers=0）**，原因是 gate/entry-quality，不是 q35 support deficit

下一步主目標：
- 在 train / leaderboard profile 收斂時，仍維持所有 surface 明講：
  - q35 support 已到位；
  - q15 仍是 veto 候選；
  - blocked / hold 的原因不是 q35 support deficit。

### 目標 C：把 current-vs-snapshot recency contract 制度化
本輪已完成：
- probe / summary / ARCHITECTURE 已能把 current inputs 與 historical snapshot 拆開。

下一步主目標：
- 繼續讓所有 governance surface 優先讀 current inputs；
- 不再因 `leaderboard_snapshot_created_at` 舊就誤判當前 blocker。

### 目標 D：維持 source auth blocker 與 bull pathology 分離治理
- `fin_netflow` 仍是 **auth_missing**
- 這是外部 source blocker，不可混進 bull exact-supported profile 收斂敘事

---

## 接下來要做

### 1. 修 train 與 bull pocket artifact 的 freshness 順序
要做：
- 直接檢查 `model/train.py` 與 heartbeat 執行順序，找出 train 為何仍讀到 `generated_at=21:45:38` 的舊 bull pocket artifact；
- 若需要，加入 freshness gate / rerun order / on-demand artifact refresh；
- 修完後重跑 train，確認 `model/last_metrics.json.feature_profile_meta.source` 能回到 exact-supported lane。

### 2. 維持 exact-supported contract 零漂移
要做：
- 持續檢查 artifact / leaderboard probe / heartbeat summary / docs 的：
  - `support_blocker_state = exact_live_bucket_supported`
  - `support_governance_route = exact_live_bucket_supported`
  - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
  - `current_alignment_inputs_stale = false`
  - `dual_profile_state` 是否仍準確反映當前 train / leaderboard 差異
- 任何一條路徑把 stale snapshot 當成唯一 blocker，都視為 regression。

### 3. 維持 q15 toxic pocket 與 q35 supported 的分工
要做：
- 持續檢查：
  - `exact_lane_bucket_verdict`
  - `decision_quality_exact_live_lane_toxic_bucket`
  - `allowed_layers`
- 若 current bucket 仍是 q35，blocked / hold 原因不得回退成 support deficit；
- 若 current bucket 掉進 q15，runtime 必須直接 veto。

### 4. 維持 source blocker 顯式治理
要做：
- 在 `COINGLASS_API_KEY` 未補前，持續把 `fin_netflow` 保持為 blocked source；
- 不把它重包裝成 bull governance 內部問題。

---

## 暫不優先

以下本輪後仍不排最前面：
- 直接放寬 live execution guardrail
- 把 exact-supported 已達標解讀成立即可部署
- 新增更多 feature family
- UI 美化與 fancy controls

原因：
> 現在真正的瓶頸不是資料量不夠，也不是 snapshot 舊；而是 **train artifact 沒跟上當前 exact-supported bull governance**。

---

## 成功標準

接下來幾輪工作的成功標準：
1. next run 必須留下至少一個與 **train artifact freshness / exact-supported train-frame parity** 直接相關的真 patch / run / verify。
2. `data/bull_4h_pocket_ablation.json`、`data/live_predict_probe.json`、`data/leaderboard_feature_profile_probe.json`、`data/heartbeat_743_summary.json` 的 exact-supported 語義持續零漂移。
3. 若 q35 current bucket rows 仍 **≥50**，train 不得再默默停在 support-aware profile 而沒有明確原因。
4. q15 toxic pocket 仍必須維持 lane-internal veto contract。
5. `fin_netflow` 繼續被正確標成 source auth blocker。

---

## Next gate

- **Next focus:**
  1. 修 train artifact freshness / rerun order，讓 exact-supported bull lane 的 train / leaderboard profile 收斂；
  2. 若 q35 rows 仍 ≥50，持續驗證 `exact_bucket_supported_proxy_not_required` 與 q15 toxic contract 在所有 surface 零漂移；
  3. 繼續把 `fin_netflow` 當外部 source blocker 管理。

- **Success gate:**
  1. next run 必須留下至少一個與 **train artifact freshness / exact-supported train-frame parity** 直接相關的 patch / artifact / verify；
  2. `support_blocker_state / support_governance_route / exact_bucket_root_cause / proxy_boundary_verdict / exact_lane_bucket_verdict / dual_profile_state / current_alignment_inputs_stale / allowed_layers` 對 bull lane 的敘述零漂移；
  3. 若 q35 exact rows 仍 ≥50，train 必須收斂到 exact-supported profile 或同輪明確輸出技術限制與門檻。

- **Fallback if fail:**
  - 若 train 仍停在 support-aware profile，下一輪升級為 `exact_supported_train_frame_parity_blocker`；
  - 若 current alignment 又被舊 snapshot 誤導，視為 recency governance regression；
  - 若 source auth 未修，繼續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 train artifact freshness contract 再擴充）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_743_summary.json`
  2. 再讀：
     - `model/last_metrics.json`
     - `data/leaderboard_feature_profile_probe.json`
     - `data/bull_4h_pocket_ablation.json`
     - `data/live_predict_probe.json`
  3. 若 `current_live_structure_bucket = CAUTION|structure_quality_caution|q35`、`current_live_structure_bucket_rows >= 50`、`support_blocker_state = exact_live_bucket_supported`、`support_governance_route = exact_live_bucket_supported`、`proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`、`decision_quality_exact_live_lane_bucket_verdict = toxic_sub_bucket_identified`、`decision_quality_exact_live_lane_toxic_bucket.bucket = CAUTION|structure_quality_caution|q15`、`current_alignment_inputs_stale = false`、`artifact_recency.alignment_snapshot_stale = true`、`train_selected_profile = core_plus_macro`、`leaderboard_selected_profile = core_plus_macro_plus_4h_structure_shift` 仍同時成立，下一輪不得再把「snapshot 舊」當主結論；必須直接推進 **train artifact freshness / exact-supported train-frame parity / q15 toxic pocket 保守治理**。
