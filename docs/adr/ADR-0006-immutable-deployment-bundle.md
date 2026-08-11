# ADR-0006：Live Canary綁定完整不可變封裝

- Status: **ACCEPTED**
- Decision date: 2026-08-11
- Decided by: Owner（Kazuha）
- Decision source: 本次BDD owner Q&A，Q6回答「完整封裝；任何內容改變都算新版本，先在模擬中成長，再另外核准進Live Canary」
- Additional owner direction: 新模型同步驗證一段時間、確認更優後通知使用者，由使用者決定是否切換
- Scope: Runtime model/strategy binding與Live Canary switching
- Technical name: Immutable `DeploymentBundle`

## 白話背景

只記住「模型檔名」不夠。同一個模型若配到不同資料、指標算法、預測目標、參數或交易規則，實際行為可能完全不同。若Owner核准A，但runtime偷偷把其中一部分換成B，就無法知道真正驗證與下單的是哪一套。

## Decision

> **Live Canary核准、載入、顯示與送單都必須引用同一個完整、不可修改、有唯一編號的DeploymentBundle。任何會改變預測或交易行為的內容改變，都建立新bundle。**

新bundle先進Paper/Shadow與舊bundle同步驗證。系統確認它更好後通知Owner，但不自動替換Live Canary；Owner決定是否切換。

## Bundle必備內容

每個bundle manifest至少固定：

- strategy ID與strategy version；
- symbol/market scope與timeframe contract；
- fitted model artifact SHA256；
- model class/library version與hyperparameters；
- training recipe、random seed與code version；
- training dataset snapshot ID、range、as-of與hash；
- feature schema與feature definition version；
- label definition、target與prediction horizon；
- calibration artifact與version（如適用）；
- strategy parameters、regime、entry與layer policy；
- execution policy version；
- manifest schema version與bundle content hash。

Owner release是一筆引用bundle ID的獨立治理記錄，不放進bundle hash，避免循環identity。

## 任何改變都算新版本

下列任一變更都產生新bundle ID：

- 重新訓練後model bytes不同；
- dataset snapshot或training range改變；
- 指標算法、欄位或normalization改變；
- label、target或horizon改變；
- hyperparameters、calibration或strategy parameters改變；
- regime/entry/layer/execution policy語義改變；
- symbol/timeframe scope改變。

只改顯示文字、非語義metadata或artifact儲存位置，不改content hash；但runtime必須以hash驗證內容，不能只相信path。

## Runtime載入契約

1. Resolver只接受bundle ID，不接受零散model path與profile name拼裝。
2. Loader讀取manifest並驗證manifest/content hashes。
3. Model、feature schema、label、strategy與execution policy逐一核對。
4. 載入後產生binding attestation，記錄實際hash與expected hash。
5. 任一unknown、missing或mismatch時risk-on capacity=0。
6. DecisionSnapshot引用同一bundle ID與attestation generation。
7. OrderIntent與permit也引用同一bundle ID。

不得使用「找不到核准bundle就退回legacy model」或truthy fallback。

## 允許的runtime override

不建立新bundle也可做的安全操作：

- Paper、Shadow或已核准Live Canary execution mode切換；
- operator pause/kill switch；
- 把資金cap或allowed layers向下縮；
- credentials、network endpoint與secret rotation（不改venue/account/scope語義）；
- logging、tracing與UI presentation。

不得在runtime override：

- 換model或feature definition；
- 換symbol、target、horizon、strategy parameters；
- 提高超過Owner核准的cap/layers；
- 降低permit、idempotency、venue lifecycle或risk safety。

## 新舊模型同步驗證

新bundle B比目前Live Canary bundle A更新時：

1. A保持Live Canary不變。
2. B用自己的exact identity進Paper/Shadow。
3. A與B在相同時間、資料as-of、費用與評分規則下比較。
4. B必須累積一段清楚標示起訖時間與outcomes的同步證據。
5. 只有B通過versioned better comparator，系統才產生switch recommendation。
6. 通知顯示A/B版本、驗證期間、ROI、回撤、成本、交易數與差異。
7. Owner明確選擇後，建立B適用的release/switch decision並切live pointer。
8. 若Owner不切換，A繼續運作，B留在shadow觀察。

同步驗證的最低期間與樣本處理由Q7確認；Q3 exact support仍只作warning。

## 切換與回復

- 切換是atomic active-live-bundle pointer update，不原地修改A。
- 切換後新的DecisionSnapshot完整引用B。
- 切換中的open orders/positions按原bundle attribution管理，不可改標為B。
- Owner可明確切回仍有效且安全相容的舊bundle。
- ADR-0002規定舊release不會因新bundle出現而自動撤銷；是否撤銷由Owner決定。
- 新bundle不得繼承舊bundle的release。

## Consequences

- 模型自動成長與Live資金邊界清楚分離。
- UI必須顯示research/shadow/live bundle各自的ID，不再只顯示model名稱。
- Model registry、release registry、DecisionSnapshot、OrderIntent與ledger形成可追蹤identity chain。
- 路徑、config profile與「latest model」不再是release identity。
- 每次真正切換都能重現、比較與回復。

## Executable specification

- `docs/specification/features/to-be/immutable-deployment-bundle.feature`
- As-is binding characterization：`docs/specification/features/as-is/personal-release-and-runtime-binding.feature`
- Promotion characterization：`docs/specification/features/as-is/promotion-state-machine.feature`
