# ISSUES.md — Current State Only

_最後更新：2026-04-14 08:06 UTC — Heartbeat #720_

本文件只保留**目前有效的問題與下一步**，不保留歷史 issue 日誌。

---

## 目前系統狀態

### 程式 / 驗證
- `PYTHONPATH=. pytest tests/test_api_feature_history_and_predictor.py tests/test_model_leaderboard.py -q`
  - **42 passed**
- `PYTHONPATH=. pytest tests/test_train_target_metrics.py -q`
  - **3 passed**
- `python tests/comprehensive_test.py`
  - **6/6 PASS**
- 新增可重跑分析腳本：
  - `scripts/feature_group_ablation.py`
  - `scripts/live_decision_quality_drilldown.py`
- 新增分析 artifact：
  - `data/feature_group_ablation.json`
  - `docs/analysis/feature_group_ablation.md`
  - `data/live_decision_quality_drilldown.json`
  - `docs/analysis/live_decision_quality_drilldown.md`

### 資料 / 新鮮度 / IC
來自 Heartbeat #720 fast run：
- Raw / Features / Labels: **21394 / 12823 / 42728**
- 本輪增量: **+1 raw / +1 feature / +8 labels**
- simulated_pyramid_win: **0.5719**
- 240m latest target lag vs raw: **3.0h**（符合 horizon lookahead）
- 1440m latest target lag vs raw: **23.8h**（符合 horizon lookahead）
- Global IC: **17/30 pass**
- TW-IC: **22/30 pass**
- Regime IC: **Bear 4/8 / Bull 6/8 / Chop 5/8**

### 模型現況
來自 `model/last_metrics.json`：
- target: `simulated_pyramid_win`
- train accuracy: **0.7025**
- cv accuracy: **0.7223**
- cv std: **0.1364**
- cv worst: **0.5466**
- samples: **11,275**
- features: **89**
- positive ratio: **0.6420**

### Feature ablation（Heartbeat #720 新增）
來自 `data/feature_group_ablation.json`（recent 5000 rows, TimeSeriesSplit=5）：
- `core_plus_macro` (**10 features**) → **cv_mean 0.7364 / cv_std 0.1769 / cv_worst 0.4610**
- `core_only` (**8 features**) → **0.7239 / 0.1857 / 0.4538**
- `current_full` (**131 features**) → **0.6533 / 0.1598 / 0.4538**
- removal checks all beat `current_full` on cv_mean:
  - `full_no_lags` → **0.6586**
  - `full_no_cross` → **0.6600**
  - `full_no_4h` → **0.6624**
  - `full_no_technical` → **0.6641**
  - `full_no_macro` → **0.6783**

**目前判讀**
- 不是「feature 越多越好」
- 現在的 full stack 明顯比小型 family 組合更不穩、更難泛化
- **core + macro** 是目前最乾淨的 accuracy baseline
- lag / cross / 4H family 至少有一部分正在拉低泛化表現，必須做 shrinkage / pruning，而不是盲目保留全量

### Live predictor 現況
來自 `data/live_predict_probe.json` + `data/live_decision_quality_drilldown.json`：
- signal: **HOLD**
- confidence: **0.6996**
- regime: **bull**
- gate: **ALLOW**
- entry quality: **0.5219 (D)**
- calibration scope: **`regime_label`**
- allowed layers: **0 → 0**
- should trade: **false**
- execution guardrail: **`decision_quality_below_trade_floor; unsupported_live_structure_bucket_blocks_trade`**

**新增 drill-down 結論**
- exact live lane `regime_label+regime_gate+entry_quality_label` 只有 **14 rows**，`win_rate=0.5`，但 **current live bucket `ALLOW|base_allow|q65` support rows = 0**
- chosen scope `regime_label` 有 **194 rows**，但 recent pathology 已降到 **win_rate=0.0 / quality=-0.2789** 的 100-row 病灶窗
- narrow bull-only D lane `regime_label+entry_quality_label`：
  - **147 rows / win_rate 0.0748 / quality -0.2098 / dd 0.2833 / tuw 0.804**
- shared collapse shifts 仍集中在：
  - `feat_4h_dist_swing_low`
  - `feat_4h_dist_bb_lower`
  - `feat_4h_bb_pct_b`

**判讀**
- blocker 已經不是 cross-regime spillover 語義錯位
- blocker 也不是 runtime guardrail 失效（guardrail 目前有正確擋單）
- 真正 blocker 是：**bull-only 4H 結構 pocket 本身仍然很差，而且 exact ALLOW lane 對當前 q65 結構沒有足夠支持樣本**

---

## 目前有效問題

### P1. bull live decision-quality 仍被 4H 結構 collapse pocket 卡住
**現象**
- live path 仍是 `bull / ALLOW / D`，但 runtime 已壓到 **0 layers**
- exact live lane 只有 **14 rows**，而且**沒有當前 q65 structure bucket 支持樣本**
- narrow bull-only D lane 的歷史結果極差：**147 rows / win_rate 7.48% / quality -0.2098**
- 共享 shift 一直指向同一組 4H 特徵：
  - `feat_4h_dist_swing_low`
  - `feat_4h_dist_bb_lower`
  - `feat_4h_bb_pct_b`

**判讀**
- 這不是 generic calibration 調參能先解掉的問題
- 需要直接處理 **bull 4H structure bucket 定義 / shrinkage / sample support**
- runtime guardrail 應繼續保守，直到 bull q65 lane 有足夠支持證據

**下一步方向**
- 先做 bull negative pocket 的 4H feature shrinkage / ablation
- 確認哪些 4H family 對 bull q65 lane 是噪音、哪些是必要訊號
- 若 exact lane 長期低樣本，需把「exact lane support 不足」正式視為 deploy-blocker，而不是拿 14-row pocket 當正面證據

---

### P1. current_full feature stack 明顯比小型 family baseline 更差
**現象**
- `core_plus_macro` 在 recent 5000 rows 上是目前最佳：**0.7364**
- `current_full` 只有 **0.6533**
- 幾乎所有 `full_no_*` removal tests 都比 `current_full` 更好

**判讀**
- 目前的問題不是「feature 不夠多」
- 而是 **family 組合過重，lag / cross / 4H / technical 裡至少有一批正在放大 variance**
- 這也解釋了為什麼 live bull lane 的 calibration / decision-quality 很容易被局部 pocket 拉壞

**下一步方向**
- 將 `feature_group_ablation.py` 升級成 train/leaderboard shrinkage candidate 產生器
- 優先測：
  - `core + macro`
  - `core + macro + selected 4H`
  - `current_full - lags`
  - `current_full - cross`
- 不再假設 full stack 是預設最優

---

### P2. leaderboard 的 deployment profile 仍是手工 preset，不是自動 lane selection
**現象**
- leaderboard 已比以前合理，且保留 `deployment_profile`
- 但 profile 仍是 evidence-driven hand-tuned presets

**風險**
- 會受人工偏好影響
- 還不能直接回答「哪個模型在什麼部署 lane 最穩」

**下一步方向**
- 讓 leaderboard 自動比較固定候選 lane：
  - `standard`
  - `bear_top10`
  - `bear_top5`
  - `balanced_conviction`
- 再輸出 best lane / stable lane，而不是只吃單一 preset

---

## 現在最重要的下一步

### 最高優先
**先把 bull live blocker 與 full-stack variance 連到同一條 shrinkage 路線：減少噪音 family，保留能解釋 bull q65 結構的必要特徵。**

### 建議執行順序
1. 用 `feature_group_ablation.py` 挑出 shrinkage 候選（先從 `core_plus_macro` 當 baseline）
2. 對 bull negative pocket 做 4H family 細分 ablation，優先看：
   - `feat_4h_dist_swing_low`
   - `feat_4h_dist_bb_lower`
   - `feat_4h_bb_pct_b`
3. 若 shrinkage 後 bull q65 支持仍不足，將 exact live lane support 不足升級為顯式 deployment blocker
4. 之後才做 leaderboard 自動 lane selection
