@to_be @owner_approved @bundle @binding @switching @no_live_order
Feature: Live Canary只載入Owner核准的完整不可變封裝
  為了避免核准一套卻載入另一套模型、資料或交易設定
  作為strategy owner
  我需要完整DeploymentBundle identity與由我決定的新舊模型切換

  # Decision: docs/adr/ADR-0006-immutable-deployment-bundle.md
  # Q6 accepted 2026-08-11.

  Background:
    Given 每個DeploymentBundle都有immutable manifest與content hash
    And Owner release引用bundle ID而不是零散path或profile name
    And 新模型先在Paper或Shadow成長

  Scenario: Bundle固定完整預測與交易內容
    Given 系統建立bundle manifest
    When manifest完成
    Then 它包含strategy與symbol scope
    And 包含model hash、class、library version與hyperparameters
    And 包含dataset snapshot、feature schema、label、target與horizon
    And 包含calibration、strategy parameters、regime、layer與execution policy version

  Scenario: Bundle ID由內容決定
    Given 兩份manifest的所有語義內容完全相同
    When 系統計算content hash
    Then 它們得到相同bundle content identity
    But 任一語義內容不同時得到不同identity

  Scenario: 模型重新訓練後建立新bundle
    Given training pipeline以新資料重新訓練模型
    And model artifact bytes與舊版不同
    When candidate註冊
    Then 建立新bundle ID
    And 不得原地覆寫舊bundle manifest

  Scenario: 指標或預測目標改變時建立新bundle
    Given model artifact path未改變
    But feature definition、label、target或horizon任一改變
    When runtime bundle建立
    Then content identity改變
    And 舊Owner release不自動套用到新bundle

  Scenario: 交易參數或規則改變時建立新bundle
    Given model bytes與features未改變
    But entry、regime、pyramid或execution policy語義改變
    When bundle建立
    Then 建立新bundle ID
    And Live Canary不能沿用舊binding attestation

  Scenario: Runtime只用bundle ID載入完整內容
    Given Owner release引用bundle A
    When runtime resolver啟動
    Then 它從A的manifest載入model、schema、target、strategy與policy
    And 不得從不同profile或latest path補入其他版本

  Scenario: Artifact path相同不代表內容相同
    Given expected model hash屬於bundle A
    And artifact path仍相同但檔案內容已被替換
    When loader驗證artifact
    Then binding attestation是mismatch
    And risk-on capacity是0

  Scenario: 找不到核准bundle時不退回legacy model
    Given release引用bundle A
    But A的model或manifest不存在
    When runtime resolver執行
    Then 狀態是UNKNOWN或MISSING
    And 不得退回legacy、default或latest model
    And adapter不會收到risk-on order

  Scenario: Binding attestation核對每個重要identity
    Given bundle A所有artifact都可讀
    When loader完成
    Then attestation記錄expected與actual model hash
    And 記錄feature、label、dataset、strategy與policy versions
    And 只有全部相同才是MATCHED

  Scenario: 安全地向下縮小資金不建立新bundle
    Given Owner已核准bundle A的極小額單層Live Canary上限
    When operator把cap調得更小或暫停交易
    Then bundle identity仍是A
    And runtime override記錄actor、時間與較保守值

  Scenario: Runtime不能把風險向上調超過核准範圍
    Given bundle A核准極小額單層
    When config或caller要求更高cap或更多layers
    Then ExecutionAuthorizer拒絕override
    And bundle A不被視為核准更高風險

  Scenario: 新bundle可與舊live bundle同步模擬
    Given bundle A是目前Live Canary bundle
    And automatic training產生bundle B
    When B開始Paper或Shadow驗證
    Then A繼續Live Canary且identity不變
    And B的prediction、intent與outcome全部標記B

  Scenario: 新舊bundle使用相同條件比較
    Given A與B在同一段時間同步驗證
    When comparison job評估它們
    Then 使用相同market as-of、fees、slippage與metric definitions
    And 報告分別顯示A與B的ROI、回撤、交易數與成本

  Scenario: 新bundle更好時只通知Owner
    Given bundle B通過versioned better comparator
    And 同步驗證期間與outcomes可稽核
    When promotion recommendation產生
    Then 系統通知Owner可以考慮由A切換到B
    And 通知包含版本、期間、報酬、回撤、成本與差異
    But active Live Canary bundle仍是A

  Scenario: 沒有Owner決定就不切換Live Canary
    Given bundle B比A更好
    But Owner尚未選擇切換
    When heartbeat或promotion job執行
    Then active live pointer保持A
    And B繼續shadow或等待決定
    And B不得繼承A的permit或release

  Scenario: Owner選擇後才切換新bundle
    Given Owner查看A與B的同步驗證報告
    And Owner明確選擇切換到B
    When release與switch decision完成
    Then 建立適用B的Owner decision record
    And active live pointer以atomic update切到B
    And 下一張DecisionSnapshot完整引用B

  Scenario: Owner拒絕或延後切換時舊bundle保持運行
    Given 系統推薦B
    When Owner選擇不切換或稍後再看
    Then A繼續作Live Canary bundle
    And B留在Paper/Shadow累積獨立證據
    And 系統不得反覆把recommendation冒充blocking alert

  Scenario: 切換不會改寫既有訂單與持倉歸屬
    Given A已有open order或position
    And Owner切換active live bundle到B
    When order lifecycle與position ledger更新
    Then 原本A的order與position仍歸屬A
    And B只負責切換後的新intent

  Scenario: Owner可以明確切回已知良好bundle
    Given active live bundle B發生問題
    And 舊bundle A仍有有效release且通過current hard safety
    When Owner明確要求rollback
    Then active live pointer以atomic update切回A
    And 建立新的DecisionSnapshot與audit record
    And 不修改A或B的historical manifests
