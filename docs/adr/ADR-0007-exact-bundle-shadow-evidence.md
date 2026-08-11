# ADR-0007：新Bundle只能用自己的Paper/Shadow成績證明自己

- Status: **ACCEPTED**
- Decision date: 2026-08-11
- Decided by: Owner（Kazuha）
- Decision source: 本次BDD owner Q&A，Q7回答「只能用這個完整新版本自己的成績，才不會拿別人的考卷替它加分」
- Scope: Paper/Shadow evidence identity與promotion recommendation
- Related: ADR-0005 autonomous improvement；ADR-0006 immutable DeploymentBundle

## 白話背景

目前可能存在一組全域shadow成果，例如某個舊Random Forest累積的預測與結果，被另一個Owner核准的Logistic bundle拿來解除gate。這就像拿別人的考卷替新考生加分：即使名稱、指標或模型類別相近，也不能證明完整新版本真的有相同行為。

## Decision

> **任何用來判斷、推薦或切換DeploymentBundle的Paper/Shadow成績，必須由該exact bundle自己產生。其他bundle的成績只能顯示為參考或診斷，不能合併、補足或解除promotion條件。**

## Exact evidence identity

每筆prediction、intent、simulated fill與outcome至少記錄：

- exact `bundle_id`與bundle content hash；
- model artifact hash；
- dataset/feature/label/target versions；
- `decision_snapshot_id`與generation ID；
- symbol、timeframe與market as-of；
- execution mode（paper/shadow）；
- strategy action、price/quote provenance與cost assumptions；
- prediction/intent/outcome stable IDs與時間；
- evaluator/comparator policy version。

從prediction到outcome必須可完整join。任何missing、unknown或identity mismatch的record不可用於promotion evidence。

## 新版本與證據邊界

- Bundle任何語義內容改變都產生新bundle ID。
- 新bundle的promotion evidence從自己的第一筆valid Paper/Shadow record開始。
- 舊bundle historical outcomes保持immutable並可作reference。
- 不把舊bundle的trade count、win rate、ROI、drawdown或support加入新bundle。
- 同一model class、同一feature profile或同一strategy name都不足以共用成績。
- 重新訓練後model bytes不同即為新bundle，即使hyperparameters相同。

## 同步比較

當新bundle B挑戰目前bundle A：

1. A與B在相同市場時間窗與as-of資料上同步產生各自prediction。
2. 每個outcome保留自己的bundle attribution。
3. Comparator各自聚合A與B，不先混成一個全域池。
4. Fees、slippage、latency、walk-forward與metric definitions相同。
5. 報告可並排比較A/B，但不轉移樣本。
6. 只有B自己的exact evidence能讓B得到`better candidate` recommendation。
7. Owner通知必須列出B自己的驗證期間、交易數、ROI、回撤、成本與不確定性。

## 舊資料與reference evidence

允許：

- 其他bundle outcomes作研究背景、ablation、regime診斷或prior information；
- UI顯示「類似bundle過去表現」且標為reference；
- 模型訓練使用經版本化的historical dataset。

不允許：

- 把reference rows計入B的promotion count；
- 用全域`deployable_count`解除B的gate；
- 對沒有bundle ID的legacy outcomes事後猜測歸屬；
- 以model class/profile相同冒充exact bundle；
- 用A的permit、release或live outcome授權B。

## 與Q3 Support Advisory的關係

Exact support/sample target依ADR-0003仍然只是信心警告。這不代表identity可以放寬：

- Support不足不阻止B進行Paper/Shadow與極小額canary（若其他條件與Owner release已滿足）。
- 但顯示B的support、ROI、trade count或shadow outcomes時，只能使用B自己的identity-matched records。
- 不能因support是advisory，就把其他bundle samples算到B名下。

## 資料品質與重複處理

- 同一bundle、snapshot與business key的prediction/intent/outcome需idempotent。
- Duplicate retries不能增加樣本數。
- Out-of-order outcome可晚到，但必須join原始intent identity。
- Snapshot generation mismatch、future information或時間倒置的record排除並標原因。
- 重新計算metrics要版本化，不改寫raw outcome truth。

## Recommendation與Owner切換

- 沒有足夠可信的B自身資料時，系統只能顯示「仍在觀察」，不能推薦切換。
- B被判定更好時，notification明確說明結論只來自B的exact evidence。
- Owner選擇切換後，Live Canary載入的必須是同一個B bundle ID。
- B若在推薦後又改任何內容，形成C；B的推薦不能自動套用C。

## Consequences

- 移除或降級全域shadow outcome對任意candidate的promotion權力。
- Worker、ledger、leaderboard與API都需要bundle-level attribution。
- 每次新bundle可能需要重新累積觀察時間，但比較結果可信且可稽核。
- UI清楚區分`exact evidence`與`reference evidence`。

## Executable specification

- `docs/specification/features/to-be/exact-bundle-shadow-evidence.feature`
- As-is characterization：`docs/specification/features/as-is/paper-shadow-and-worker.feature`
- Promotion characterization：`docs/specification/features/as-is/promotion-state-machine.feature`
