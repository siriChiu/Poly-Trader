# Poly-Trader 模型清單（當前環境適配版）

_最後更新：2026-04-14_

本文件只整理**適合目前 Poly-Trader 環境與概念**的模型清單，目的是幫助：

- 訓練主線選型
- leaderboard 分層
- heartbeat 討論時避免把所有模型混為一談

---

## 一、目前環境前提

Poly-Trader 目前不是純 end-to-end 深度學習交易系統，而是：

- **多特徵 tabular 框架**
- 以 `simulated_pyramid_win` 為主 target
- 有明確的：
  - `4H regime gate`
  - `entry_quality`
  - `allowed_layers`
  - `decision_quality`
- 偏好：
  - **低頻、高信念**
  - **高勝率、低回撤**
  - **可解釋**
  - **避免一堆使用者看不懂的參數**

因此，模型評估不應只看平均 accuracy，而要同時看：

- walk-forward / OOS 穩定度
- worst fold
- top-k precision
- drawdown penalty / time underwater
- bucket support adequacy

---

## 二、模型分層建議表

| 分層 | 模型 | 目前定位 | 為何適合 / 不適合 |
|---|---|---|---|
| 核心模型 | `rule_baseline` | 必備對照組 | 驗證是否其實簡單規則已足夠，避免被黑箱模型帶偏 |
| 核心模型 | `random_forest` | production-biased 穩健主力 | 適合 tabular、多特徵、低頻高信念；比激進 boosting 更穩 |
| 核心模型 | `xgboost` | 研究主力模型 | 表達力強，適合 4H + 短線交互，但需嚴格 guardrail / shrinkage / calibration |
| 核心模型 | `logistic_regression` | 乾淨 sanity baseline | 最容易解釋，適合辨識哪些提升是真訊號、哪些只是模型撿噪音 |
| 對照模型 | `lightgbm` | boosting 對照組 | 與 XGBoost 做效率 / 穩定度對照，值得保留但不是第一主線 |
| 對照模型 | `catboost` | noise-friendly 對照組 | 在某些 noisy tabular 場景有價值，適合作為 XGB 補充比較 |
| 對照模型 | `ensemble` | 後段整合候選 | 適合在單模型治理成熟後再進一步疊加，不宜過早主導 |
| 研究模型 | `mlp` | 研究保留 | 目前資料規模與 bucket/support 問題下，成本高、可解釋性差 |
| 研究模型 | `svm` | 研究保留 | 不夠方便擴展與 rolling retrain，對現有主線幫助有限 |

---

## 三、核心模型（最適合目前主線）

### 1. `rule_baseline`
**角色：必備對照組，不是可有可無。**

用途：
- 驗證是否簡單規則已足夠
- 作為 deployment fallback
- 防止模型看起來進步，但其實只是 overfit 某些 pocket

### 2. `random_forest`
**角色：production-biased 穩健主力。**

適合理由：
- 對目前 tabular 多特徵架構友善
- 不需要太多額外參數
- 適合高信念 / top-k / 低頻交易偏好
- 在 bucket / support adequacy 問題上，比激進 boosting 更穩

### 3. `xgboost`
**角色：研究主力。**

適合理由：
- 對 4H + 短線多特徵交互的表達力最強
- 是目前最值得保留的主力候選之一

注意：
- 容易在薄 bucket / 局部 pocket 上過擬合
- 必須搭配：
  - shrinkage
  - walk-forward
  - calibration
  - support-aware guardrail

### 4. `logistic_regression`
**角色：乾淨 sanity baseline。**

適合理由：
- 容易解釋
- 可作為是否真的有訊號的最小基準
- 很適合在 feature family 治理與 bucket purity 問題上當對照組

---

## 四、對照模型（保留，但不宜當前主線）

### `lightgbm`
- 適合做 XGBoost 對照
- 能比較 efficiency / stability
- 不建議目前優先超過 RF / XGB / LR

### `catboost`
- 適合做 noisy tabular 對照
- 可觀察是否在某些 fold / regime 下比 XGB 更穩
- 目前價值大於 MLP / SVM，但仍低於核心四模型

### `ensemble`
- 等單模型治理更乾淨後再強化
- 目前過早上 ensemble，容易只是把噪音平均起來，讓 debug 更難

---

## 五、研究模型（保留，不優先投入）

### `mlp`
- 現階段資料規模、bucket/support 問題、可解釋需求下，成本偏高
- 除非核心模型已穩定，否則不建議優先投入

### `svm`
- 在目前多特徵、walk-forward、rolling retrain 環境下不夠實用
- 可留在 leaderboard，但不應佔用主要研究資源

---

## 六、若未來擴充，最值得新增的模型概念

### 1. `ExtraTrees`
- 可作為 RF 的強對照組
- 通常比先加神經網路更符合現在需求

### 2. `HistGradientBoosting`
- 可作為輕量 boosting 對照組
- 在不引入太多額外複雜度下，補足 XGB/LGBM 比較面

### 3. Two-stage / bucket-aware models
不是單一模型名，而是更適合 Poly-Trader 的架構概念：

- Stage 1：regime / bucket 判別
- Stage 2：within-bucket scorer

這比單純堆更複雜黑箱模型，更符合目前：
- bull 全體與 bull collapse pocket 最佳組合不同
- exact live bucket support 太薄
- deployment 需要 support-aware blocker/fallback

---

## 七、目前建議的最小核心模型組合

若只保留最值得投入的模型組合，建議是：

1. `rule_baseline`
2. `random_forest`
3. `xgboost`
4. `logistic_regression`

這四個分別對應：

- 規則對照
- 穩健 production 候選
- 高表達研究主力
- 乾淨 sanity baseline

---

## 八、對 leaderboard 的直接意義

目前 leaderboard 建議直接採用三層：

- **核心模型**：`rule_baseline`, `random_forest`, `xgboost`, `logistic_regression`
- **對照模型**：`lightgbm`, `catboost`, `ensemble`
- **研究模型**：`mlp`, `svm`

這樣做的好處：
- 使用者能一眼看懂目前該優先相信哪些模型
- heartbeat / issue / roadmap 不會把研究型模型和主線模型混成一團
- 方便之後把 heartbeat 結論回灌到 leaderboard 與文件
