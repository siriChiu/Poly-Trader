# ROADMAP.md — Current Plan Only

_最後更新：2026-04-14 — Heartbeat #720_

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
- leaderboard 已吃到真正的 4H context：
  - `feat_4h_bias200`
  - `regime_label`
  - `feat_4h_bb_pct_b`
  - `feat_4h_dist_bb_lower`
  - `feat_4h_dist_swing_low`
- leaderboard 已加入 `deployment_profile`
- 已導入 evidence-driven deployment presets
- top-k walk-forward precision 報告可產出 `model/topk_walkforward_precision.json`

### 決策語義
- target 已統一以 `simulated_pyramid_win` 為主
- 4H regime gate / entry quality / allowed layers 已串進主要 decision path
- live predictor / Strategy Lab / leaderboard 的 4H 語義已比以前一致
- Heartbeat #719 已把 live decision-quality calibration 從 **cross-regime broader lane** 收斂到 **same-regime fallback**，避免 neutral-dominated `regime_gate+entry_quality_label` 再假代表 bull runtime path
- Heartbeat #720 新增 reusable drill-down artifact：
  - `data/live_decision_quality_drilldown.json`
  - `docs/analysis/live_decision_quality_drilldown.md`
  讓每輪可以直接比對 chosen scope / exact live lane / narrow same-regime lane / broad same-gate lane

### 分析治理（Heartbeat #720）
- 新增 `scripts/feature_group_ablation.py`
  - 會輸出 `data/feature_group_ablation.json`
  - 會輸出 `docs/analysis/feature_group_ablation.md`
- 已用 recent 5000 rows + TimeSeriesSplit 驗證：
  - `core_plus_macro` 目前比 `current_full` 更穩、更準
  - `current_full` 不再可被視為預設最佳 baseline

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

Heartbeat #720 最新證據：
- `core_plus_macro` → **0.7364 / 0.1769 / 0.4610**
- `core_only` → **0.7239 / 0.1857 / 0.4538**
- `current_full` → **0.6533 / 0.1598 / 0.4538**

這代表：
- full stack 目前不是最佳 baseline
- 不能再預設「保留全部 feature 最安全」
- 下一輪應先做 **family shrinkage**，不是再擴張 feature list

要做：
- 以 `core_plus_macro` 當小型強 baseline
- 比較：
  - `core + macro + selected 4H`
  - `current_full - lags`
  - `current_full - cross`
  - `current_full - selected weak 4H`
- 產出：
  - CV mean
  - CV std
  - worst fold
  - top10 / bear top10 precision

### 2. Bull live pocket 4H collapse drill-down
目標：直接處理 bull live blocker，而不是只做 generic calibration 調參。

Heartbeat #720 drill-down 已證明：
- chosen scope = `regime_label`
- exact live lane 只有 **14 rows**，且 **q65 structure bucket support = 0**
- narrow bull-only D lane **147 rows / win_rate 0.0748 / quality -0.2098**
- shared collapse features 仍是：
  - `feat_4h_dist_swing_low`
  - `feat_4h_dist_bb_lower`
  - `feat_4h_bb_pct_b`

要做：
- bull-only negative pocket 的 4H family ablation
- 確認哪些 4H feature 應降權 / 移除 / 分桶重做
- 若 exact live lane 長期低樣本，明確把 support 不足升級為 deployment blocker

### 3. Multi-lane leaderboard evaluation
目標：讓 leaderboard 比的是「模型 × 合理部署方式」，而不是單一僵硬 preset。

目前狀態：
- leaderboard 的 deployment profile 已比以前合理
- 但仍是 **手工 evidence-driven presets**
- 還不是自動從資料學出最佳 deployment lane

要做：
- 每個模型比較幾條固定 lane：
  - `standard`
  - `bear_top10`
  - `bear_top5`
  - `balanced_conviction`
- 產出：
  - best lane
  - stable lane
  - production lane

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
