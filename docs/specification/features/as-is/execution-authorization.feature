@as_is @execution @safety
Feature: 每筆訂單的 Execution Authorization
  為了任何錯誤、stale或不一致狀態都不會產生真實新增曝險
  作為order boundary
  我需要fail-closed live config、canary、permit與risk controls

  # Sources: execution/execution_service.py, execution/config.py,
  # server/routes/api.py, tests/test_execution_service.py,
  # tests/test_server_startup.py, tests/test_execution_surface_contract.py

  Scenario: WAIT不建立order
    Given operator提交action `wait`
    When `/api/trade`處理request
    Then response成功
    And ExecutionService不被呼叫
    And DB沒有新增trade/order lifecycle

  Scenario: paper與shadow order永遠使用dry-run adapter
    Given execution mode是paper或shadow
    When buy/sell action提交
    Then selected adapter是dry-run
    And response標示dry_run true
    And 不需要private venue credentials

  Scenario: live order需要live config triple
    Given order將使用non-dry adapter
    When execution config被驗證
    Then mode必須是live
    And `enable_live_trading`必須true
    And `dry_run`必須false
    And 任一不成立都回fail-closed rejection

  Scenario: live order需要canary enabled
    Given live config triple通過
    But `live_canary.enabled`不是true
    When order提交
    Then order以LIVE_CANARY_DISABLED拒絕

  Scenario: explicit allowlist中的symbol才可進入canary
    Given live canary allowlist非空
    And requested symbol不在allowlist
    When order提交
    Then order以LIVE_SYMBOL_NOT_ALLOWED拒絕

  @known_inconsistency @safety
  Scenario: 空allowlist目前被視為不限制symbol
    Given live canary enabled
    And allowed_symbols是空list
    When `_enforce_live_canary_policy`執行
    Then 現行實作不會因symbol缺少allowlist而拒絕
    And 這與policy文案要求explicit allowlist矛盾

  Scenario: order quantity不得超過canary cap
    Given requested qty大於symbol-specific cap
    When live canary policy執行
    Then order以LIVE_QTY_CAP_EXCEEDED拒絕

  Scenario: non-dry order需要signed short-lived permit
    Given live config與canary通過
    When ExecutionService處理non-dry request
    Then request必須帶execution permit
    And permit claims必須符合run/profile/strategy hash/venue/symbol/side/order type/reduce-only/qty/notional
    And permit不得過期

  Scenario: permit nonce只能消費一次且跨process持久
    Given 一個valid permit已被成功消費
    When 另一個ExecutionService instance重放同permit
    Then durable permit store拒絕重放

  Scenario: unused permit可在另一個service instance消費
    Given permit已簽發但尚未消費
    When 另一個process使用同一DB提交符合claims的order
    Then permit可成功驗證並原子消費一次

  @known_gap
  Scenario: manual API live buy沒有成功permit journey
    Given `/api/trade`前段predictor gates全通過
    And selected adapter是non-dry
    When route呼叫ExecutionService
    Then 現行route沒有傳入execution permit
    And order在真正boundary仍被拒絕

  @known_gap
  Scenario: live runner沒有成功permit journey
    Given runner產生BUY_LAYER或SELL_ALL
    And submit_orders是true
    And selected adapter是non-dry
    When runner呼叫ExecutionService
    Then 現行runner沒有傳入execution permit
    And order被fail-closed拒絕

  Scenario: API buy在current-live gate blocked時不呼叫adapter
    Given predictor current-live payload的should_trade是false
    When operator提交buy
    Then API回409
    And ExecutionService/adapter不應收到request

  Scenario: malformed或unsupported action被拒絕
    Given action不在wait/buy/sell/paper/shadow允許集合
    When API處理request
    Then 回傳validation error
    And 沒有order side effect

  @known_gap @safety
  Scenario: risk-off sell仍被live canary與permit共同限制
    Given 已有live position需要reduce-only exit
    And kill switch active或qty大於tiny canary cap
    When SELL_ALL抵達ExecutionService
    Then 現行 `_enforce_live_canary_policy` 仍可能拒絕它
    And execution permit仍是必需
    And 系統尚未實作「阻止risk-on但保留受控risk-off」的完整緊急退出契約

  @known_gap @safety
  Scenario: daily loss與failure halt在side判斷前套用
    Given daily loss或failure count已觸發
    When reduce-only sell提交
    Then 現行risk limit可在side/reduce-only例外之前拒絕
    And to-be必須由owner定義emergency exit authorization
