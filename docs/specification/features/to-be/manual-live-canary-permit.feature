@to_be @owner_approved @manual @permit @live_canary @no_live_order
Feature: Owner再次確認後取得只限一筆的Live Canary許可
  為了讓人工監督的極小額真實交易可控且不會重複送單
  作為strategy owner
  我需要先看完整preview，再明確確認exact order

  # Decision: docs/adr/ADR-0010-manual-live-canary-permit.md
  # Q9 accepted 2026-08-11.

  Background:
    Given Manual Live Canary使用與worker相同的ExecutionAuthorizer
    And preview本身不簽permit也不送單
    And permit短效、綁exact order且只能使用一次

  Scenario: Preview顯示完整模型與狀態單
    Given Owner準備一筆Live Canary
    When 系統建立OrderIntentPreview
    Then 畫面顯示exact bundle ID與model version
    And 顯示active DecisionSnapshot ID、時間與freshness
    And 顯示Owner release與binding status

  Scenario: Preview顯示完整金額與風險
    Given preview已取得fresh account與market state
    When UI顯示確認內容
    Then 顯示requested amount、fees、slippage與normalized quantity
    And 顯示R1 cap、existing exposure與remaining capacity
    And 顯示daily loss、failure count、single-layer與open order狀態

  Scenario: Preview顯示實際order semantics
    Given preview可建立
    When UI顯示order內容
    Then 顯示masked venue/account、symbol、side、order type與time in force
    And 顯示fresh quote、quote as-of與允許偏移
    And 不得只顯示「買入」而隱藏exact payload

  Scenario: 建立preview不會產生真實副作用
    Given Owner開啟或刷新preview
    When preview endpoint被呼叫
    Then 不建立可消耗permit
    And 不呼叫venue place order
    And 不把preview當成已核准order

  Scenario: 只有已驗證Owner能再次確認
    Given preview等待確認
    When 未驗證actor、過期session或CSRF失敗的request確認
    Then confirmation被拒絕
    And 不建立OrderIntent或permit

  Scenario: 再次確認後仍由Server重新檢查
    Given Owner明確確認preview
    When server處理confirmation
    Then 重新讀取active snapshot、quote、equity、exposure與ledger
    And 重新檢查kill switch、breaker、release、binding與venue
    And 重新計算R1 cap與normalized order

  Scenario: 全部相同且安全才簽發permit
    Given Owner確認preview
    And server重新檢查後所有hard safety通過
    When PermitService處理request
    Then 建立persistent exact OrderIntent
    And 簽發short-lived single-use permit
    And permit綁定Owner、intent、bundle、snapshot與policy versions

  Scenario: Permit綁定exact venue order欄位
    Given permit已簽發
    Then 它綁定venue、account、symbol與side
    And 綁定order type、time in force、normalized quantity與maximum notional
    And 綁定quote as-of、price/slippage bound、issued at與expires at
    And 包含single-use nonce與signature

  Scenario: 不能簽發blanket permit
    Given Owner核准bundle A
    When 系統建立Live Canary permit
    Then permit只適用一個OrderIntent
    And 不得授權A的任意未來order、symbol、金額或時間

  Scenario: Snapshot或bundle改變時要求重新確認
    Given Owner看到preview P1
    And active snapshot或bundle在確認前改變
    When Owner確認P1
    Then 原confirmation被拒絕
    And UI顯示內容已改變並建立新preview
    And 不得把P1自動套到新generation

  Scenario: Quote過期或價格偏移過大時要求重新確認
    Given Owner看到quote Q1
    And 確認時Q1已過期或current price超過允許偏移
    When server重新檢查
    Then 不簽permit或不消耗既有permit
    And UI顯示價格已改變需重新確認

  Scenario: Cap或風險狀態改變時不沿用確認
    Given Owner看到可用capacity
    And 確認前equity、exposure、daily loss、failure count或single-layer狀態改變
    When server重新計算
    Then 若order不再安全就拒絕
    And 不得靜默縮放或改order後直接送出

  Scenario: Owner release撤銷後舊preview失效
    Given preview建立時release是ACTIVE
    And Owner之後正式撤銷release
    When 舊preview被確認
    Then confirmation被拒絕
    And 不簽permit

  Scenario: Permit過期後不能使用
    Given permit已超過expires at
    When ExecutionAuthorizer收到該permit
    Then order被拒絕為permit_expired
    And adapter不收到place-order call

  Scenario: Permit payload不同時不能使用
    Given permit綁定BTC、BUY與maximum 20 USDT
    When caller改成其他symbol、side、quantity或更高notional
    Then signature/binding validation失敗
    And order不送到venue

  Scenario: Permit只能原子消耗一次
    Given 一張valid single-use permit
    When browser double-click或兩個request同時提交
    Then DB-level nonce consumption只允許一個成功
    And adapter最多收到一次place-order call

  Scenario: Browser retry使用同一OrderIntent
    Given client未收到第一次submit response
    When 它retry相同business key
    Then server回傳原OrderIntent current state
    And 不建立第二張permit或第二筆venue order

  Scenario: Permit通過後仍執行最後一刻檢查
    Given valid permit尚未消耗
    When ExecutionAuthorizer準備呼叫adapter
    Then 再次檢查kill switch、fresh quote、exposure、idempotency與venue state
    And 任一檢查失敗就拒絕且留下reason

  Scenario: Local submitted不顯示成已成交
    Given adapter已接受place-order request
    When UI顯示receipt
    Then 先顯示submitted或venue acknowledged
    And partial fill、fill、cancel、reject與unknown分開顯示
    And 只有reconciliation後才顯示terminal truth

  Scenario: Timeout或UNKNOWN不會盲目重送
    Given venue call timeout且結果UNKNOWN
    When worker處理該OrderIntent
    Then 不簽新permit重送相同order
    And 使用client order ID查venue並reconcile
    And UI顯示正在確認而不是成功或失敗

  Scenario: AI不能代替Owner再次確認
    Given AI已解釋preview並建議交易
    When 沒有Owner authenticated confirmation
    Then PermitService不簽permit
    And AI不能代按、代簽或重放nonce

  Scenario: Risk-off仍有正式但不同的安全旅程
    Given Live Canary有open order或position需要cancel、reduce或exit
    When Owner啟動risk-off action
    Then 系統驗證exact order/position identity與idempotency
    But 不要求risk-on entry eligibility
    And action與receipt完整audit
