# ISSUES.md — Current State Only

_最後更新：2026-04-14 11:22 UTC — Heartbeat #724 (fast + leaderboard auto lane selection)_

本文件只保留**目前有效的問題與下一步**，不保留歷史 issue 日誌。

---

## 目前系統狀態

### 程式 / 測試
- `PYTHONPATH=. pytest tests/test_model_leaderboard.py -q`
  - **17 passed**
- `PYTHONPATH=. pytest tests/test_train_target_metrics.py tests/test_hb_parallel_runner.py tests/test_bull_4h_pocket_ablation.py -q`
  - **20 passed**
- `PYTHONPATH=. python model/train.py`
  - **通過**；已確認訓練會套用 `core_plus_macro`，且 `model/last_metrics.json.feature_profile_meta.source = bull_4h_pocket_ablation.support_aware_profile`
- `python scripts/hb_parallel_runner.py --fast`
  - **通過**；現在會自動刷新：
    - `data/feature_group_ablation.json`
    - `docs/analysis/feature_group_ablation.md`
    - `data/bull_4h_pocket_ablation.json`
    - `docs/analysis/bull_4h_pocket_ablation.md`
    - `data/live_decision_quality_drilldown.json`
    - `docs/analysis/live_decision_quality_drilldown.md`
- `python tests/comprehensive_test.py`
  - 本輪未重跑（沿用上一輪 6/6 PASS 狀態）
- 新增治理 patch：
  - `model/train.py` 現在接受 extended ablation profiles（`core_macro_plus_stable_4h` / `current_full_no_bull_collapse_4h`），不再因 schema 不相容 silently 回退到 `code_default`
  - 當 live bull exact structure bucket support = 0 時，訓練會改採 `bull_supported_neighbor_buckets_proxy` 推出的 support-aware profile，而不是盲目吃 global `core_only`
  - `backtesting/model_leaderboard.py` 現在會對每個模型自動比較固定 deployment lane 候選（`standard` / `high_conviction_bear_top10` / `bear_top5` / `balanced_conviction` / `quality_filtered_all_regimes` 中的相容子集），再選出當前 best lane；不再只吃單一 hand-tuned preset

### 資料 / 新鮮度 / IC
來自 Heartbeat #723 fast run：
- Raw / Features / Labels: **21403 / 12832 / 42857**
- 本輪增量: **+1 raw / +1 features / +5 labels**
- simulated_pyramid_win: **0.5741**
- 240m latest target lag vs raw: **3.4h**（符合 horizon lookahead）
- 1440m latest target lag vs raw: **23.0h**（符合 horizon lookahead）
- Global IC: **17/30 pass**
- TW-IC: **23/30 pass**
- Regime IC: **Bear 4/8 / Bull 6/8 / Chop 4/8**
- recent drift: **100-row canonical window = 100x simulated_pyramid_win=1, chop 100%**，但 `recent_drift_report` 判定為 **supported_extreme_trend**（不可拿來放寬 live bull lane）

### 模型現況
來自 `model/last_metrics.json`：
- target: `simulated_pyramid_win`
- train accuracy: **0.6333**
- cv accuracy: **0.7530**
- cv std: **0.0935**
- cv worst: **0.6121**
- samples: **12,355**
- features: **10**
- feature profile: **`core_plus_macro`**
- feature profile source: **`bull_4h_pocket_ablation.support_aware_profile`**（support cohort=`bull_supported_neighbor_buckets_proxy`, rows=84, exact_live_bucket_rows=0）
- positive ratio: **0.6324**
- calibration compatibility bug 已修正：predictor 現在能正確吃舊版 isotonic payload 的 `x/y` keys，不會默默跳過 calibration

### Feature ablation（Heartbeat #722 更新）
來自 `data/feature_group_ablation.json`（recent 5000 rows, TimeSeriesSplit=5）：
- `recommended_profile`: **`core_only`**
- `core_only` (**8 features**) → **cv_mean 0.7248 / cv_std 0.1812 / cv_worst 0.4538 / bull_top10 0.1293**
- `core_plus_macro` (**10 features**) → **0.6849 / 0.2161 / 0.4538 / bull_top10 0.1810**
- `current_full` (**131 features**) → **0.5604 / 0.2523 / 0.4538 / bull_top10 0.1983**
- 新增 bull collapse pocket 細分 ablation（`data/bull_4h_pocket_ablation.json`）：
  - bull_all best profile → **`core_plus_macro_plus_all_4h`**（20 features, brier **0.2241**）
  - bull_collapse_q35 best profile → **`core_plus_macro`**（10 features, **0.7073 / 0.0797 / 0.6098**）
  - bull_exact_live_lane_proxy → **306 rows / win_rate 0.7908 / best=`core_plus_macro`**
  - bull_live_exact_lane_bucket_proxy → **43 rows / no stable profile yet**
  - bull_supported_neighbor_buckets_proxy → **84 rows / best=`core_plus_macro` (single_holdout 0.7308)**
  - collapse thresholds(q35):
    - `feat_4h_dist_swing_low <= 1.7661`
    - `feat_4h_dist_bb_lower <= 0.4307`
    - `feat_4h_bb_pct_b <= 0.1267`

**目前判讀**
- 不是「feature 越多越好」；**full stack 在最新 recent-5000 視窗明顯退化**
- 這輪最乾淨的 global baseline 已進一步收斂到 **`core_only`**，代表 macro/4H/lag/cross family 在當前窗口裡仍有 variance 放大風險
- bull_all 視角下，加入完整 4H family 對 brier 仍有邊際幫助，但 **bull_collapse_q35 / supported-neighbor buckets 仍站在 `core_plus_macro`**
- exact live bucket 仍然 **0 support rows**；因此現在的 blocker 是 **support-aware deployment + bucket-specific shrinkage**，不是 generic calibration
- 結論：下一輪應該優先把 `core_only` / `core_plus_macro` 轉成正式 train-or-leaderboard 候選，並把 4H 結構 bucket support 納入 selection 規則

### Live predictor 現況
來自 `data/live_predict_probe.json` + `data/live_decision_quality_drilldown.json`：
- signal: **BUY**
- confidence: **0.9045**
- regime: **bull**
- gate: **CAUTION**
- entry quality: **0.4172 (D)**
- calibration scope: **`regime_label`**
- allowed layers: **0 → 0**
- should trade: **false**
- execution guardrail: **`decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade`**
- fast heartbeat 現在會**自動刷新** drill-down artifact，且會一起刷新 feature ablation / bull pocket ablation evidence，不再留舊 snapshot


**新增 drill-down 結論**
- exact live lane `regime_label+regime_gate+entry_quality_label` 只有 **17 rows**，`win_rate=0.2353 / quality=-0.0626`，而且 **current live bucket support rows = 0**
- chosen scope `regime_label` 有 **194 rows**，但 recent pathology 仍是 **100-row / win_rate=0.0 / quality=-0.2789**
- narrow bull-only D lane `regime_label+entry_quality_label`：
  - **147 rows / win_rate 0.0748 / quality -0.2098 / dd 0.2833 / tuw 0.804**
- broader `regime_gate+entry_quality_label` 雖有 **2764 rows / quality 0.3529**，但 recent500 幾乎全是 **chop spillover**，不能拿來代表 live bull path

**判讀**
- blocker 已經不是 cross-regime spillover 語義錯位
- blocker 也不是 runtime guardrail 失效（guardrail 目前有正確擋單）
- 真正 blocker 是：**bull-only 4H 結構 pocket 本身仍然很差，而且 exact CAUTION lane 對當前 live bucket 依然沒有支持樣本**

---

## 目前有效問題

### P1. bull live decision-quality 仍被 4H 結構 collapse pocket 卡住
**現象**
- live path 目前是 `bull / CAUTION / D`，runtime 已壓到 **0 layers**
- exact live lane 只有 **17 rows**，而且**沒有當前 live structure bucket 支持樣本**
- narrow bull-only D lane 的歷史結果極差：**147 rows / win_rate 7.48% / quality -0.2098**
- 共享 shift 仍集中在：
  - `feat_4h_dist_swing_low`
  - `feat_4h_dist_bb_lower`
  - `feat_4h_bb_pct_b`
- 本輪新證據也顯示：
  - bull_all best profile 是 **`core_plus_macro_plus_all_4h`**，但只反映整體 bull cohort 的邊際 brier 改善
  - bull_collapse_q35 best profile 仍是 **`core_plus_macro`**（代表 collapse pocket 內新增 4H family 沒有帶來額外泛化收益）
  - exact live lane proxy 有 **306 rows / win_rate 0.7908**，但 live exact bucket proxy 只有 **43 rows** 且仍無穩定 profile
  - supported neighbor buckets 已有 **84 rows / win_rate 0.6905**，比 live bucket 更接近可用 support baseline

**判讀**
- 這不是 generic calibration 調參能先解掉的問題
- 也不是「把三個 toxic 4H features 直接刪掉」或「把整批 4H 特徵加回來」就能解掉的問題
- 需要直接處理 **bull 4H structure bucket 定義 / support blocker / 更細的 shrinkage**
- runtime guardrail 應繼續保守，直到 exact lane 或 same-bucket lane 有足夠支持證據

**下一步方向**
- 重新跑 live probe / heartbeat，驗證新的 support-aware blocker 是否如預期把 `unsupported_exact_live_structure_bucket_blocks_trade` 帶到 artifact
- 若要做 fallback，明確只允許 `supported neighbor buckets` 走保守 fallback，而不是 broader same-bucket 放行
- 只保留能解釋 bull q35 / CAUTION pocket 的 4H 訊號，其餘留在研究層或降權

---

### P1. current_full feature stack 明顯比小型 family baseline 更差
**現象**
- `core_plus_macro` 在 recent 5000 rows 上仍是目前最佳：**0.7330**
- `current_full` 只有 **0.6567**
- bull_all cohort 最佳 profile 是 `core_plus_macro_plus_all_4h`，但 bull_collapse_q35 cohort 最佳 profile 反而退回 `core_plus_macro`
- 這代表整體 bull cohort 與 collapse pocket 的最優 4H family 並不一致

**判讀**
- 目前的問題不是「feature 不夠多」
- 而是 **family 組合過重，lag / cross / 4H / technical 裡至少有一批正在放大 variance**
- Heartbeat #723 已先修掉一個假進度 root cause：訓練先前其實會因 extended ablation profile 名稱不相容而 silently 回退到 `code_default`；現在已接受 extended profiles，並在 bull exact bucket support=0 時改吃 support-aware `core_plus_macro`
- bull blocker 與 full-stack variance 有關，但不能再假設一套 4H 組合能同時解 bull 全體與 collapse pocket

**下一步方向**
- `feature_group_ablation.py` 繼續維持全域 shrinkage baseline，`bull_4h_pocket_ablation.py` 負責 pocket-specific 4H probes
- 下一步把這些 profile 延伸成 leaderboard candidate / train candidate 產生器
- 優先測：
  - `core + macro`
  - `current_full - lags`
  - `current_full - cross`
  - 更細的 4H bucket-specific shrinkage（而不是整族刪除）
- 不再假設 full stack 是預設最優

---

## 現在最重要的下一步

### 補充參考
- `docs/analysis/model-shortlist-current.md` 已整理目前最適合 Poly-Trader 環境與概念的模型分層，避免後續擴模型時偏離「低頻 / 高信念 / 可解釋 / 少參數」原則。

### 最高優先
**先把 bull live blocker 與 full-stack variance 連到同一條 shrinkage 路線：減少噪音 family，保留能解釋 bull q35 結構的必要特徵。**

### 建議執行順序
1. 用 `feature_group_ablation.py` 挑出 shrinkage 候選（先從 `core_plus_macro` 當 baseline）
2. 對 bull negative pocket 做 4H family 細分 ablation，優先看：
   - `feat_4h_dist_swing_low`
   - `feat_4h_dist_bb_lower`
   - `feat_4h_bb_pct_b`
3. 若 shrinkage 後 bull q65 支持仍不足，將 exact live lane support 不足升級為顯式 deployment blocker
4. 用新的 leaderboard auto lane selection 驗證 shrinkage winners 是否在 OOS lane ranking 也維持優勢，避免只在訓練 artifact 中好看
