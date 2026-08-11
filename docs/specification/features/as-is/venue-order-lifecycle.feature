@as_is @venue @orders @safety
Feature: Venue capability 與 order lifecycle
  為了讓本地accept不會被誤認為交易所成交
  作為execution operator
  我需要可驗證的preview、ack、fill、partial、cancel、reject與reconciliation

  # Sources: execution/exchanges/base.py, okx_adapter.py,
  # execution/execution_service.py, execution/control_plane.py,
  # tests/test_execution_service.py, tests/test_execution_metadata_smoke.py,
  # tests/test_paper_shadow_outcome_reconciliation.py

  Scenario: dry-run order可在沒有credentials時建立rehearsal lifecycle
    Given execution mode是paper或shadow
    And private venue credentials不存在
    When 合法order提交
    Then dry-run adapter回傳normalized order
    And TradeHistory與TradeLifecycleEvent記錄dry-run狀態
    And 沒有真實venue order ID被冒充

  Scenario: real adapter在credentials缺失時fail closed
    Given selected adapter是OKX non-dry
    But 必要credentials未配置
    When adapter初始化或order提交
    Then venue readiness是false
    And 不得退回dry-run卻標示live成功

  Scenario: venue metadata決定quantity與price normalization
    Given 市場規則包含qty step、price tick、minimum qty與minimum notional
    When order preview建立
    Then qty與price依規則正規化
    And 若正規化後低於minimum則拒絕

  Scenario: qty normalization不得把order放大超過原request
    Given requested qty不是step的整數倍
    When normalize_order_request執行
    Then 正規化qty不得高於requested qty

  Scenario: BUY market order使用venue規則驗證notional
    Given 買單使用quote或base quantity semantics
    When adapter建立order
    Then 系統依exchange規則計算minimum notional
    And 不足時fail closed

  Scenario: successful venue submit建立submitted與ack lifecycle
    Given adapter回傳accepted order identifier
    When ExecutionService持久化結果
    Then lifecycle含submitted/acknowledged或等價state
    And 保留client order ID與venue order ID

  Scenario: partial fill不得被當成filled
    Given venue回報partial filled quantity
    When reconciliation更新order
    Then lifecycle state是PARTIAL
    And remaining exposure仍可追蹤

  Scenario: cancel request與cancel acknowledgement分開記錄
    Given open order需要取消
    When cancel被送往venue
    Then 先記錄cancel requested
    And 只有venue確認後才記錄cancelled

  Scenario: adapter exception產生rejected/unknown而非成功
    Given venue call timeout或回傳無法確認
    When order lifecycle更新
    Then 不得標為filled
    And 應記錄reject或unknown/reconcile-required狀態

  Scenario: startup reconciliation修復stale local orders
    Given local DB存在submitted/partial但未終結orders
    When service啟動reconciliation
    Then 它查詢venue truth
    And 更新fills/cancels/rejects
    And 無法確認時維持fail-closed unknown

  @known_gap
  Scenario: metadata smoke artifact不是live venue proof
    Given `execution_metadata_smoke.json`顯示public metadata可用
    But credentials/connection/ack-fill-cancel proof不存在
    When API顯示venue readiness
    Then 不得推導live order lifecycle已ready

  @known_gap
  Scenario: current environment沒有完整real lifecycle evidence
    Given 目前real trade history與real lifecycle events為0
    And OKX credentials未配置
    When 判斷live readiness
    Then 只能證明paper/dry-run rehearsal
    And 不能宣稱venue live ready

  @known_gap @safety
  Scenario: position attribution不足時不得自動管理多bot部位
    Given 同一venue account可能有多個bot或manual position
    When runner計算SELL_ALL或exposure
    Then 只依自己decision ledger重建open layers可能不足以代表venue總position
    And to-be需要per-bot/per-bundle ledger與global exposure reconciliation
