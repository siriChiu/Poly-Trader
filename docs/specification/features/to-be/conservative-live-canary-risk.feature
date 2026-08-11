@to_be @owner_approved @live_canary @risk @money @no_live_order
Feature: Live Canary採25 USDT或0.5%的保守上限
  為了用可承受的真實資金驗證完整order lifecycle
  作為strategy owner
  我需要極小額、單層、全域曝險與自動停手機制

  # Decision: docs/adr/ADR-0008-conservative-live-canary-risk.md
  # Supplemental Owner risk decision R1 accepted 2026-08-11.

  Background:
    Given Live Canary只允許一層
    And 每筆risk-on與全部canary曝險共用同一上限
    And risk-off、cancel與reconcile不受risk-on entry gate阻止

  Scenario: 使用25 USDT與帳戶0.5%取較小
    Given fresh account equity是4000 USDT
    When 系統計算Live Canary cap
    Then 0.5%是20 USDT
    And 最終order與total exposure cap是20 USDT

  Scenario: 固定25 USDT是另一個天花板
    Given fresh account equity是10000 USDT
    When 系統計算Live Canary cap
    Then 0.5%是50 USDT
    And 最終order與total exposure cap是25 USDT

  Scenario: Equity缺失或過期時不下單
    Given account equity不存在、過期、負數或無法確認account identity
    When ExecutionAuthorizer計算cap
    Then risk-on capacity是0
    And 不得使用舊equity或default正值

  Scenario: 明確zero equity保持zero
    Given current account equity明確是0
    And older snapshot有正equity
    When cap calculation執行
    Then final cap是0
    And 不得以truthy fallback採用舊值

  Scenario: 費用與保守滑價也計入上限
    Given final cap是25 USDT
    When authorizer準備risk-on order
    Then order notional加estimated fees與slippage buffer不得超過25 USDT
    And 不能只檢查未含成本的quote amount

  Scenario: Quantity rounding不能把金額推過上限
    Given venue要求quantity step rounding
    When order quantity normalization完成
    Then 系統重新計算normalized notional與fees
    And 若超過cap就向下round或拒絕
    And 不得向上round後照送

  Scenario: 安全cap低於交易所最低下單額就不交易
    Given final cap低於fresh instrument minimum order
    When order準備建立
    Then 狀態是BELOW_VENUE_MINIMUM
    And adapter不收到place-order call
    And 系統不得自行提高cap

  Scenario: Open order與現有position共同計入總曝險
    Given 已有Live Canary open order保留10 USDT
    And existing canary position notional是8 USDT
    And final total cap是25 USDT
    When current capacity計算
    Then remaining risk-on capacity最多是7 USDT再扣成本buffer

  Scenario: 單層限制禁止第二筆加倉
    Given 已有一層Live Canary position或pending risk-on order
    When 新risk-on intent要求加倉
    Then intent被拒絕
    And reason code是single_layer_limit或等價stable code

  Scenario: 市場上漲超過cap時只停止加倉
    Given position原始下單符合cap
    And 市場上漲令mark-to-market notional超過cap
    When risk policy評估
    Then 新的risk-on capacity是0
    But 系統不因超cap本身強迫賣出
    And operator仍可reduce或exit

  Scenario: 多symbol仍共用一個全域cap
    Given 未來允許多個symbol做Live Canary
    And symbol A已有canary exposure
    When symbol B要求risk-on
    Then A與B的open orders及positions合計受同一25 USDT或0.5%cap
    And 不得每個symbol各自取得完整全域cap

  Scenario: 單日虧損使用10 USDT與0.25%取較小
    Given UTC start-of-day equity是2000 USDT
    When 系統計算daily realized loss cap
    Then 0.25%是5 USDT
    And 最終daily loss cap是5 USDT

  Scenario: 達單日虧損上限後停止risk-on
    Given daily realized PnL含fees已虧到final daily cap
    When 新risk-on intent進入
    Then intent被拒絕
    And daily loss halt保持到下一個UTC日且ledger健康
    But cancel、reduce、exit與reconcile仍可執行

  Scenario: UTC新日不會掩蓋不健康ledger
    Given daily halt在前一日active
    And 新UTC日已開始
    But order或position reconciliation仍是UNKNOWN
    When risk state更新
    Then risk-on保持blocked
    And 不能只因日期改變就顯示READY

  Scenario: 第一次真實送單失敗顯示warning
    Given consecutive live failure count是0
    When 一筆non-dry Live Canary order進入確認的FAILED terminal state
    Then failure count變成1
    And 顯示warning與問題原因

  Scenario: 第二次連續真實送單失敗後停止
    Given consecutive live failure count是1
    When 下一筆non-dry Live Canary order再次確認失敗
    Then failure count變成2
    And failure halt active
    And 新的risk-on intent被拒絕

  Scenario: UNKNOWN outcome先停止retry並對帳
    Given venue request timeout且不知道是否已接受
    When worker處理該intent
    Then 不得立即重送相同risk-on order
    And 先查venue status與client order ID進行reconciliation
    And 確認terminal結果後才更新failure counter

  Scenario: 確認成功的venue ack可重置連續失敗
    Given consecutive live failure count是1
    When 下一筆合法order取得可驗證venue ack
    Then consecutive failure count重置為0
    But local submit acknowledgement或UNKNOWN不能重置

  Scenario: Paper與dry-run失敗不污染live counter
    Given Paper、Shadow或dry-run order失敗
    When live failure counter更新
    Then counter保持不變
    And 模擬錯誤另行顯示與修復

  Scenario: Owner可降低或暫停但不能無決策提高
    Given accepted policy是25 USDT/0.5%、10 USDT/0.25%與2 failures
    When Owner或operator要求更小cap或pause
    Then 系統允許並記錄較保守override
    When config或automation要求提高任一accepted limit
    Then 系統拒絕並要求新的Owner decision
