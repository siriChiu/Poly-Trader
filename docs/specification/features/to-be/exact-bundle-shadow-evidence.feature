@to_be @owner_approved @shadow @evidence @identity @no_live_order
Feature: 新Bundle只能用自己的Paper與Shadow成績證明自己
  為了不拿別的模型成績替新版本加分
  作為strategy owner
  我需要每個完整bundle獨立累積、比較與顯示自己的outcomes

  # Decision: docs/adr/ADR-0007-exact-bundle-shadow-evidence.md
  # Q7 accepted 2026-08-11.

  Background:
    Given 每個Paper或Shadow candidate都有exact DeploymentBundle ID
    And prediction、intent與outcome可以用stable IDs串起
    And 其他bundle evidence最多只能標為reference

  Scenario: 每筆Paper或Shadow預測記錄exact bundle
    Given bundle B產生一筆prediction
    When worker持久化prediction
    Then record包含bundle ID與content hash
    And 包含model、feature、label、target與DecisionSnapshot generation
    And 包含symbol、timeframe與market as-of

  Scenario: Outcome可追回原始prediction與intent
    Given bundle B的prediction產生simulated intent
    When outcome稍後完成
    Then outcome引用原prediction、intent與bundle B
    And 從prediction到outcome的identity chain可驗證

  Scenario: 全域shadow成績不能替bundle B加分
    Given 全域shadow pool有大量其他bundle outcomes
    But bundle B沒有自己的valid outcomes
    When promotion evidence聚合
    Then B的exact trade count是0
    And 全域outcomes只顯示為reference
    And 系統不得推薦B切換Live Canary

  Scenario: 相同model class不能共用成績
    Given bundle A與B都使用相同model class
    But model artifact hash或其他manifest內容不同
    When B的metrics計算
    Then A的outcomes不計入B
    And B保留自己的獨立metric series

  Scenario: 相同feature profile不能共用成績
    Given bundle A與B使用相同feature schema
    But dataset、label、target、parameters或model hash不同
    When B的promotion evidence建立
    Then A只能作reference
    And B不得因profile相同繼承A的win rate或ROI

  Scenario: 重新訓練後的model從自己的第一筆開始
    Given bundle B以新資料重新訓練並形成bundle C
    When shadow worker開始驗證C
    Then C建立新的exact evidence series
    And B的historical outcomes保持immutable
    But B的trade count不加入C

  Scenario: 沒有identity的legacy outcome不可猜測歸屬
    Given legacy shadow outcome缺少bundle ID或model hash
    When evidence migration執行
    Then record標為unattributed reference
    And 不得依path、時間接近或model name猜成bundle B

  Scenario: A與B同步比較仍各自保留成績
    Given A是目前Live Canary bundle
    And B是parallel Shadow candidate
    When 兩者在同一市場時間窗產生outcomes
    Then A與B各自聚合ROI、回撤、交易數與成本
    And comparator並排比較但不混合raw records

  Scenario: Comparator使用相同條件
    Given A與B有各自exact outcomes
    When 系統判斷B是否更好
    Then 兩者使用相同fees、slippage、latency與metric definitions
    And comparison記錄共同時間窗與policy version

  Scenario: 只有B自己的成績能產生switch recommendation
    Given B自己的exact outcomes通過better comparator
    When recommendation建立
    Then reason只引用B自己的驗證期間與metrics
    And 其他bundle只可列在reference appendix

  Scenario: Support不足仍是warning但不可借樣本
    Given B自己的exact support低於target
    And A與其他bundle有大量support rows
    When B的confidence顯示
    Then B顯示support warning
    And A的rows不加入B
    But support warning本身不作per-order hard gate

  Scenario: Duplicate retry不能增加bundle樣本數
    Given bundle B已有相同snapshot與business key的outcome
    When worker retry相同record
    Then idempotency只保留一筆promotion-eligible outcome
    And B的trade count不重複增加

  Scenario: Generation或時間不一致的record排除
    Given outcome的bundle identity相符
    But snapshot generation mismatch或時間順序不合理
    When evidence validation執行
    Then record不計入promotion metrics
    And 保存stable exclusion reason供診斷

  Scenario: Owner通知只呈現B自己的證明
    Given B被判定優於A
    When system通知Owner可以考慮切換
    Then 通知包含B自己的bundle ID、期間、交易數、ROI、回撤與成本
    And 清楚標示reference evidence未計入結論

  Scenario: B改變成C後需要新的證明
    Given B已取得better recommendation
    When 模型、資料、指標、target、parameters或交易規則任一改變形成C
    Then B的recommendation只適用B
    And C回到自己的Paper或Shadow驗證
    And Owner不得被告知C已經沿用B的成績通過
