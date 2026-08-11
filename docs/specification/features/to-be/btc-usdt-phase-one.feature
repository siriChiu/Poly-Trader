@to_be @owner_approved @symbol @btc @phase_one @no_live_order
Feature: 第一階段只允許BTC/USDT並明確拒絕其他幣
  為了避免ETH等request偷偷使用BTC資料或模型
  作為strategy owner
  我需要BTC/USDT端到端一致且保留未來symbol partition能力

  # Decision: docs/adr/ADR-0011-btc-usdt-phase-one.md
  # Q10 accepted 2026-08-11.

  Background:
    Given Phase 1唯一supported market是BTC/USDT spot
    And 所有data、bundle、snapshot、permit與ledger identity都包含canonical symbol
    And unsupported symbol在side effect前fail closed

  Scenario: 明確alias正規化為BTC/USDT
    Given request symbol是BTC-USDT或核准venue instrument alias
    When input boundary進行symbol normalization
    Then canonical symbol是BTC/USDT
    And market type是spot
    And 保留原venue instrument ID供adapter使用

  Scenario: 模糊或不同market type不會被猜成BTC spot
    Given request缺少quote asset或要求BTC futures
    When symbol normalization執行
    Then request被拒絕為unsupported或ambiguous market
    And 不得默認成BTC/USDT spot

  Scenario: 非BTC market data request明確拒絕
    Given request symbol是ETH/USDT
    When market data或4H fetch endpoint被呼叫
    Then 回傳UNSUPPORTED_SYMBOL_PHASE_1或等價typed error
    And 不發出BTC network fetch
    And 不寫入BTC或ETH market rows

  Scenario: 非BTC backfill不會使用BTC最新4H資料
    Given historical backfill request symbol是ETH/USDT
    When backfill job啟動
    Then job在任何fetch或DB write前拒絕
    And 不得使用BTC 4H snapshot填入ETH rows

  Scenario: BTC歷史backfill使用當時已知4H candles
    Given BTC/USDT historical row時間是T
    When 系統補建該row的4H features
    Then 只使用T當時已收盤或可知的BTC 4H candles
    And 不得使用現在最新4H candle

  Scenario: Feature與label join包含symbol key
    Given market facts、features與labels都屬BTC/USDT
    When training rows materialize
    Then join keys包含canonical symbol與event/as-of time
    And 不同symbol rows不能因timestamp相同而join

  Scenario: 非BTC training job明確拒絕
    Given training request symbol是ETH/USDT
    When automatic model-improvement scheduler處理request
    Then 不建立dataset snapshot或training run
    And 回傳Phase-1 unsupported reason

  Scenario: DeploymentBundle固定BTC/USDT spot
    Given Phase-1 candidate通過training與evaluation
    When DeploymentBundle建立
    Then manifest包含BTC/USDT與spot market type
    And symbol或market type改變會產生不同bundle identity

  Scenario: 非BTC bundle不能取得Phase-1 Owner release
    Given bundle subject是ETH/USDT
    When release workflow驗證Phase-1 scope
    Then release creation被拒絕或標為not applicable
    And 不得套用BTC bundle的永久release

  Scenario: DecisionSnapshot所有欄位屬同一BTC identity
    Given active Phase-1 snapshot正在建立
    When builder組裝market、model、signal、risk與venue資料
    Then 所有輸入都驗證為BTC/USDT spot
    And 任一symbol mismatch使candidate snapshot不發布

  Scenario: Manual preview只允許BTC/USDT
    Given Owner要求建立ETH/USDT Live Canary preview
    When preview endpoint驗證symbol
    Then request在permit或OrderIntent建立前拒絕
    And UI顯示第一階段只支援BTC/USDT

  Scenario: Permit不能從BTC改成其他symbol
    Given permit綁定BTC/USDT
    When caller把order payload改成ETH/USDT
    Then permit binding validation失敗
    And adapter不收到place-order call

  Scenario: Venue response symbol不一致時停止並對帳
    Given BTC/USDT OrderIntent已送到venue
    But venue response或reconciliation回傳不同instrument
    When order lifecycle處理response
    Then state標為symbol mismatch或UNKNOWN
    And 停止新的risk-on並要求reconciliation
    And 不得把response記到BTC position

  Scenario: UI不顯示其他幣為可交易選項
    Given Phase 1 symbol policy active
    When Owner查看Strategy Lab或Live Canary UI
    Then BTC/USDT是唯一可進正式pipeline的symbol
    And 其他symbol不顯示為可用live選項
    And 未來欄位可標示coming later而非假支援

  Scenario: Historical非BTC資料保留但不參與正式pipeline
    Given DB或artifact已有legacy ETH records
    When Phase-1 leaderboard、support或DecisionSnapshot建立
    Then legacy ETH records不被刪除
    But 不計入BTC metrics、support或promotion evidence
    And 清楚標為unsupported research/reference

  Scenario: 所有Paper與Shadow evidence也按BTC bundle歸屬
    Given BTC bundle產生Paper或Shadow outcomes
    When promotion metrics聚合
    Then records以BTC bundle與symbol partition
    And 任何非BTC或missing-symbol record只能作reference

  Scenario: R1是全部Live Canary的全域上限
    Given Phase 1只有BTC/USDT
    When risk capacity計算
    Then R1的25 USDT/0.5%涵蓋全部Live Canary exposure
    And 未來新增symbol時不得自動取得另一份相同cap

  Scenario: Schema保留未來multi-symbol能力
    Given Phase 1只允許BTC/USDT
    When system建立data、bundle、snapshot、intent與ledger records
    Then 每個record仍有explicit symbol與market partition fields
    And 不得因目前只有BTC而移除symbol identity

  Scenario: 開放第二個symbol需要新Owner決策
    Given 未來要加入ETH或其他symbol
    When 產品準備啟用multi-symbol
    Then 需要新的ADR與owner-approved BDD
    And 驗證per-symbol data/model/evidence/ledger與portfolio risk
    And 在完成前Phase-1 guard繼續明確拒絕
