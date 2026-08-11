@to_be @owner_approved @heartbeat @training @self_improvement @no_live_order
Feature: 模型可以自動重建資料、訓練、比較與成長
  為了讓模型持續吸收新資料並改善成本後報酬與回撤
  作為strategy owner
  我需要一條安全、可重現且不會偷偷替換實盤模型的自動成長流程

  # Decision: docs/adr/ADR-0005-autonomous-model-improvement.md
  # Q5 accepted 2026-08-11.

  Background:
    Given Heartbeat只安排工作而不自行修改code或交易規則
    And 每個dataset、training run、model與comparison都有immutable identity
    And Live Canary bundle必須另有適用的Owner release

  Scenario: Heartbeat可以安排資料重建
    Given market facts或feature data需要更新
    When Heartbeat檢查freshness
    Then 它安排idempotent data rebuild job
    And job有lease、timeout與resource cap
    But Heartbeat fast loop不直接執行整個heavy rebuild

  Scenario: 資料重建產生不可修改的dataset snapshot
    Given data rebuild job成功
    When 新資料通過schema與時間順序檢查
    Then 系統建立新的dataset snapshot ID
    And 記錄symbol、range、as-of、source與definition versions
    And 不得原地改寫舊dataset snapshot

  Scenario: 4H歷史特徵必須符合當時可知資訊
    Given training dataset包含歷史1min rows與4H features
    When dataset validation執行
    Then 每個歷史row只能看到該時間點已收盤或已知的4H資料
    And 不得把目前最新4H candle灌入過去缺口

  Scenario: 資料污染時停止自動訓練
    Given dataset有look-ahead、label mismatch、symbol混用或不可解釋missingness
    When validation失敗
    Then training job不啟動
    And 現任champion保持不變
    And 報告與狀態單顯示data validation failure

  Scenario: 自動訓練建立獨立challenger
    Given valid dataset snapshot已發布
    When training job依版本化recipe執行
    Then 每個challenger有model artifact hash、hyperparameters與random seed
    And 記錄feature schema、label、target、horizon與dataset ID
    And 不覆寫現任champion artifact

  Scenario: champion與challenger在相同條件下比較
    Given champion與challenger都可在同一dataset重現
    When comparison job執行
    Then 兩者使用相同walk-forward splits、fees、slippage與as-of
    And 比較結果記錄comparator policy version

  Scenario: 不只用accuracy判斷更好
    Given challenger的CV accuracy較高
    But 成本後ROI較差或最大回撤超過容忍範圍
    When comparator評估challenger
    Then challenger不得被判定為更好
    And accuracy只顯示為diagnostic metric

  Scenario: 成本後報酬與回撤優先
    Given challenger在相同OOS條件下成本後ROI較高
    And 最大回撤沒有超過核准容忍範圍
    And profit factor、trade count與時間切片穩定性通過versioned comparator
    When comparison完成
    Then challenger可標記為better candidate
    And comparison保存每個metric與reason code

  Scenario: 沒有更好的模型就保留champion
    Given 所有challenger都未通過better criteria
    When training cycle完成
    Then 現任champion pointer保持不變
    And 每個失敗challenger仍保留experiment record
    And 報告說明沒有可靠改善

  Scenario: 更好的模型可自動成為research或shadow champion
    Given challenger通過better criteria
    When promotion job執行
    Then registry可把它標為research champion或shadow candidate
    And Paper/Shadow worker可使用該exact identity
    And leaderboard與generated report更新

  Scenario: 更好的模型不會偷偷替換Live Canary
    Given 新的shadow candidate比現任模型更好
    But 它沒有適用於該identity的Owner release
    When live bundle resolver執行
    Then 現有Live Canary bundle不變
    And 新candidate顯示awaiting owner release或not applicable
    And adapter不得因automatic training收到新identity的live order

  Scenario: 舊release不會自動套用到新模型
    Given Owner release適用bundle A
    And automatic training產生bundle B
    When B成為better candidate
    Then A的release保持ACTIVE
    But B不繼承A的release
    And B進Live Canary前需要相符的release與binding

  Scenario: Exact support不足只顯示信心警告
    Given challenger通過資料完整性與better comparator
    But exact support低於sample target
    When candidate status發布
    Then 顯示support warning
    And warning不單獨阻止research或shadow competition
    And 不把support變成per-order hard gate

  Scenario: Paper與Shadow outcomes保留candidate identity
    Given 新candidate進入Paper或Shadow
    When worker記錄prediction、intent與outcome
    Then 每筆record包含exact bundle與DecisionSnapshot generation
    And 其他candidate的outcomes不會無標示地合併

  Scenario: 更新報告與狀態單使用同一generation
    Given training cycle、comparison與promotion結果完成
    When publication job執行
    Then leaderboard、generated report與candidate fields引用同一generation
    And 下一張DecisionSnapshot引用該generation
    And publication不會把新舊結果拼在一起

  Scenario: Publication失敗不會部分切換
    Given new champion candidate已在registry建立
    But report或DecisionSnapshot publication失敗
    When job結束
    Then active public pointer保持上一個完整generation
    And 新candidate保留為未發布狀態供retry

  Scenario: API讀取不會觸發training
    Given current-state頁面被頻繁刷新
    When GET endpoint被呼叫
    Then 它只讀active DecisionSnapshot
    And 不得在request內重建資料、訓練模型或改leaderboard

  Scenario: 同一時間只跑一個相同training cycle
    Given 某dataset與recipe的training job已有active lease
    When 另一個Heartbeat tick要求相同job
    Then scheduler合併或拒絕duplicate request
    And 不得產生兩個互相競爭的champion pointer update

  Scenario: Training失敗不影響現有運行
    Given training process因resource、timeout或model error失敗
    When failure被記錄
    Then 現任research、shadow與live pointers都保持不變
    And failure report包含run ID與可重試原因

  Scenario: Heartbeat不能自動修改code與交易規則
    Given 模型自動成長流程正在運行
    When 它發現feature、label或execution policy需要改進
    Then 它只能建立建議、issue或experiment proposal
    And 不得自動patch source code、policy thresholds或hard safety

  Scenario: 所有自動決策都可稽核與回復
    Given 多輪automatic training已完成
    When owner查看任一champion切換
    Then 可以看到dataset、recipe、metrics、comparator、actor與timestamp
    And 可以把research或shadow pointer切回上一個已知良好identity
    And historical records保持immutable
