@as_is @model_health @circuit_breaker
Feature: 模型結果熔斷與實際交易風控的分離
  為了在模型近期結果惡化時停止新增曝險
  作為risk policy
  我需要清楚區分model outcome breaker與realized execution risk

  # Sources: model/predictor.py, execution/execution_service.py,
  # tests/test_api_feature_history_and_predictor.py,
  # tests/test_hb_predict_probe.py, tests/test_execution_service.py

  Scenario: recent canonical outcomes達門檻時model breaker清除
    Given recent canonical 1440m simulated-pyramid outcomes有足夠樣本
    And recent wins達到configured minimum
    When evaluate_circuit_breaker執行
    Then active是false
    And reason說明recent window已通過

  Scenario: recent canonical outcomes不足時model breaker保持active
    Given recent canonical outcomes少於minimum samples或wins不足
    When evaluate_circuit_breaker執行
    Then active是true
    And predictor不得產生risk-on signal

  Scenario: breaker使用strict recent window而不是任意歷史support
    Given 全歷史evidence很多
    But strict current window未達recent wins門檻
    When breaker被評估
    Then reference-only歷史rows不得解除breaker

  Scenario: breaker active時predictor回傳可解釋狀態
    Given circuit breaker active
    When predict執行
    Then signal是CIRCUIT_BREAKER或等價fail-closed狀態
    And should_trade是false
    And allowed_layers是0
    And current price與diagnostic fields仍可呈現

  Scenario: owner release不因model breaker被刪除
    Given owner已核准immutable strategy identity
    And model breaker變成active
    When runtime release overlay組裝
    Then release record仍存在
    But technical capacity是0

  Scenario: breaker audit不得授權order
    Given `circuit_breaker_audit.json`顯示active或clear
    When API或heartbeat讀取artifact
    Then 該artifact只證明某generation的model outcome評估
    And 不等於ExecutionService的daily loss、failure halt或kill switch狀態

  Scenario: actual execution daily loss會阻止live order
    Given persisted execution metadata顯示當日loss超過limit
    When non-dry order抵達ExecutionService
    Then order被risk limit拒絕
    And rejection寫入lifecycle/metadata

  Scenario: consecutive execution failures會觸發runtime halt
    Given ExecutionService累積failure count達上限
    When 下一筆order被提交
    Then 系統拒絕order
    And 必須由明確reset/restart/recovery流程解除

  @known_inconsistency
  Scenario: model breaker與execution breaker共用熔斷語彙
    Given UI或docs只顯示 `circuit_breaker_active`
    When operator判讀狀態
    Then 現行copy可能沒有清楚指出它來自labels還是realized orders
    And AI可能把model evidence與資金風控視為同一gate
