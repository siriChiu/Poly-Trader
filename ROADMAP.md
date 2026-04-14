# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 — Heartbeat #724 (fast + leaderboard auto lane selection)_

本文件只保留**當前進度**與**接下來要做的事情**，不保留歷史 roadmap 演進紀錄。

---

## 已完成

### 平台與工作區
- Strategy Lab (`/lab`) 已成為正式回測工作區
- 舊 `/backtest` 已退役並導向 `/lab`
- 已完成 async backtest job + top progress 顯示
- 已完成價格圖 / 權益圖分離與同步顯示

### 圖表與效能
- `CandlestickChart` 已支援 local cache + incremental kline refresh
- `FeatureChart` 已支援 local cache + incremental kline refresh
- benchmark 後處理已做平行化
- blind benchmark 已加入 process fallback

### 模型與 leaderboard
- 已新增 `docs/analysis/model-shortlist-current.md`，整理目前最適合 Poly-Trader 環境與概念的核心 / 對照 / 研究模型分層
- leaderboard 已吃到真正的 4H context：
  - `feat_4h_bias200`
  - `regime_label`
  - `feat_4h_bb_pct_b`
  - `feat_4h_dist_bb_lower`
  - `feat_4h_dist_swing_low`
- leaderboard 已加入 `deployment_profile`
- 已導入 evidence-driven deployment presets
- **Heartbeat #724**：leaderboard 會自動比較固定 deployment lane 候選（`standard` / `high_conviction_bear_top10` / `bear_top5` / `balanced_conviction` / `quality_filtered_all_regimes` 的相容子集），並持久化當前 best lane
- top-k walk-forward precision 報告可產出 `model/topk_walkforward_precision.json`
- predictor 已修正 isotonic calibration payload 相容性，舊版 `x/y` keys 不再被忽略

### 決策語義
- target 已統一以 `simulated_pyramid_win` 為主
- 4H regime gate / entry quality / allowed layers 已串進主要 decision path
- live predictor / Strategy Lab / leaderboard 的 4H 語義已比以前一致
- predictor runtime 現在已改成 **support-aware structure-bucket blocker**：exact live bucket support=0 直接阻擋，neighbor buckets 只作保守參考，不再用 broader same-bucket scope 放行
- 已用 `scripts/hb_predict_probe.py` 實測驗證：artifact 現在會明確落出 `unsupported_exact_live_structure_bucket_blocks_trade`
- Heartbeat #719 已把 live decision-quality calibration 從 **cross-regime broader lane** 收斂到 **same-regime fallback**，避免 neutral-dominated `regime_gate+entry_quality_label` 再假代表 bull runtime path
- Heartbeat #720 新增 reusable drill-down artifact：
  - `data/live_decision_quality_drilldown.json`
  - `docs/analysis/live_decision_quality_drilldown.md`
  讓每輪可以直接比對 chosen scope / exact live lane / narrow same-regime lane / broad same-gate lane
- Heartbeat #721：`hb_parallel_runner.py --fast` 現在會在 `hb_predict_probe.py` 後**自動刷新**上述 drill-down artifact，避免 heartbeat summary 還在引用舊的 live lane snapshot

### 分析治理（Heartbeat #722 → #723）
- `scripts/feature_group_ablation.py` 現在會固定輸出：
  - `recommended_profile`
  - bull_top10 指標
- `scripts/bull_4h_pocket_ablation.py` 已新增：
  - 會輸出 `data/bull_4h_pocket_ablation.json`
  - 會輸出 `docs/analysis/bull_4h_pocket_ablation.md`
  - 專門比較 bull_all / bull_collapse_q35 / exact-live-lane proxy / live-bucket proxy / supported-neighbor-bucket proxy 的 4H family 組合
- **Heartbeat #722 patch**：`scripts/hb_parallel_runner.py --fast` 現在也會自動刷新這兩份 ablation artifact，並把結果寫進 `data/heartbeat_fast_summary.json`，避免 heartbeat 只更新 collect/IC/drift 而 feature-family 證據仍是舊 snapshot
- **Heartbeat #723 patch**：`model/train.py` 不再因 extended ablation profile 名稱（如 `core_macro_plus_stable_4h` / `current_full_no_bull_collapse_4h`）與 training-side profile registry 不一致而 silently 回退到 `code_default`
- **Heartbeat #723 patch**：當 live bull exact structure bucket support=0 時，training 會改採 `bull_supported_neighbor_buckets_proxy` 的 support-aware profile（目前落在 `core_plus_macro`），而不是盲目沿用 global `core_only`
- Heartbeat #723 實測：`PYTHONPATH=. python model/train.py` → `feature_profile=core_plus_macro`, `feature_profile_meta.source=bull_4h_pocket_ablation.support_aware_profile`, `cv_accuracy=0.7530`, `cv_worst=0.6121`
- Heartbeat #722 / #723 的 recent 5000 rows 驗證：
  - `core_only` → **0.7248 / 0.1812 / 0.4538**
  - `core_plus_macro` → **0.6849 / 0.2161 / 0.4538**
  - `current_full` → **0.5604 / 0.2523 / 0.4538**
  - bull_all best profile → **`core_plus_macro_plus_all_4h`**（brier **0.2241**）
  - bull_collapse_q35 best profile → **`core_plus_macro`**（**0.7073 / 0.0797 / 0.6098**）

---

## 當前主目標

## 目標 A：提高模型準確度與 OOS 穩定度

這仍然是最重要的事情。

### 原則
- **優先提高 accuracy / stability / calibration**
- **不要再優先增加更多使用者看不懂的參數**
- 若某改善只能靠加入一堆複雜參數才成立，優先順序要下降
- **先 shrinkage / 治理 feature family，再談新增更多 feature**

### 目前聚焦指標
- train accuracy
- cv accuracy
- cv std
- cv worst-fold
- walk-forward bear top-k precision
- decision quality consistency
- bull exact-live-lane support rows / support share

---

## 接下來要做

### 1. Feature-family shrinkage（最高優先）
目標：找出哪些特徵群真的幫助泛化，哪些只是在 full stack 裡放大 variance。

Heartbeat #722 最新證據：
- `recommended_profile` → **`core_only`**
- `core_only` → **0.7248 / 0.1812 / 0.4538**
- `core_plus_macro` → **0.6849 / 0.2161 / 0.4538**
- `current_full` → **0.5604 / 0.2523 / 0.4538**
- bull_all best profile → **`core_plus_macro_plus_all_4h`**（brier **0.2241**）
- bull_collapse_q35 best profile → **`core_plus_macro`**（**0.7073 / 0.0797 / 0.6098**）
- bull_exact_live_lane_proxy → **306 rows / best=`core_plus_macro`**
- bull_live_exact_lane_bucket_proxy → **43 rows / no stable profile yet**
- bull_supported_neighbor_buckets_proxy → **84 rows / best=`core_plus_macro`**

這代表：
- full stack 目前不是最佳 baseline
- 不能再預設「保留全部 feature 最安全」
- training path 已先落地 shrinkage auto-selection
- bull blocker **不是**靠直接刪掉三個 4H collapse features 就能解掉
- bull 全體與 bull collapse pocket 的最佳 4H 組合不一樣，下一步要往 bucket/support 分層治理
- live exact bucket support 明顯比 neighbor buckets 更薄，下一步要直接把 support 分層帶進 deployment/blocker 規則

要做：
- 以 `core_plus_macro` 當小型強 baseline
- 比較：
  - `current_full - lags`
  - `current_full - cross`
  - 更細的 4H bucket-specific shrinkage / support-based pruning
  - leaderboard candidate sets derived from ablation winners
- 產出：
  - CV mean
  - CV std
  - worst fold
  - top10 / bear top10 / bull top10 precision

### 2. Bull live pocket 4H collapse drill-down
目標：直接處理 bull live blocker，而不是只做 generic calibration 調參。

Heartbeat #721 drill-down 已證明：
- chosen scope = `regime_label`
- exact live lane 只有 **17 rows**，且 **current live structure bucket support = 0**
- narrow bull-only D lane **147 rows / win_rate 0.0748 / quality -0.2098**
- broader `regime_gate+entry_quality_label` 雖然健康，但 recent500 幾乎全是 **chop spillover**，不能代表 live bull path
- shared collapse features 仍是：
  - `feat_4h_dist_swing_low`
  - `feat_4h_dist_bb_lower`
  - `feat_4h_bb_pct_b`

要做：
- 以 `scripts/bull_4h_pocket_ablation.py` 的 q35 collapse cohort 與 exact-live-bucket proxy 為基準，細分 structure bucket / support ablation
- 確認哪些 4H feature 應降權 / 分桶重做，而不是整族硬刪
- 若 exact live bucket 持續低支持，而 neighbor buckets 有 support，明確把這種 support 落差升級為 deployment blocker / fallback 規則

### 3. Multi-lane leaderboard evaluation
目標：讓 leaderboard 比的是「模型 × 合理部署方式」，而不是單一僵硬 preset。

目前狀態：
- Heartbeat #724 已讓 `backtesting/model_leaderboard.py` 自動比較固定 lane 候選，而不是只吃單一 hand-tuned preset
- 目前會輸出選中的 `deployment_profile`，並在 status metadata 留下 `deployment_profiles_evaluated`
- 但 lane 候選仍是**固定集合**，還沒有吃進 bull pocket support / structure bucket support 的更細分治理

要做：
- 把 auto lane selection 從 fixed candidates 延伸到 support-aware / bucket-aware lanes
- 將 lane evaluation 結果直接回灌到 leaderboard candidate / production lane 決策
- 產出：
  - best lane
  - stable lane
  - production lane
  - lane-selection evidence（support rows / structure bucket coverage / worst-fold stability）

### 4. 降低最差 fold 崩掉的問題
目標：不要只看平均分數。

目前已知：
- `current_full` 與小型 baseline 差距，主要體現在 fold instability
- 所以下一輪不能只追整體 mean，必須直接盯 worst fold

要做：
- 分析最差 fold 的 regime / feature family 組成
- 檢查是否由 lag / cross / 4H 某一批特徵在特定 fold 放大噪音
- 把 shrinkage 結果回灌到正式 train / leaderboard candidate set

### 5. 圖表穩定性收尾
目標：把上下圖同步與下圖 marker 問題真正收乾淨。

要做：
- 實機驗證 wheel zoom sync
- 驗證下圖 marker 是否完全穩定
- 若還有右側抖動，再補更嚴格的 marker bucket 規則

---

## 暫不優先

以下項目先不排最前面：
- 新增更多使用者參數
- 再做更多 UI fancy controls
- 擴張太多新的研究特徵
- 把 leaderboard 做得更花俏但沒有提升 accuracy

原因很簡單：

> 目前最需要的是 **更準、更穩**，不是更複雜。

---

## 成功標準

接下來幾輪工作的成功標準：
1. `current_full` 不再明顯輸給 shrinkage baseline
2. `cv_std` 明顯下降
3. `cv_worst` 明顯上升
4. bull live q65 lane 出現可用支持樣本，或被明確治理成 deploy blocker
5. bear top-k OOS precision 維持或提升
6. 不靠新增一堆前端參數也能改善結果

---

## 目前一句話總結

> 平台層已足夠；接下來要做的是把 feature family 治理與 bull 4H pocket root-cause 收斂成真正能提升 accuracy / stability 的 shrinkage 路線。 
