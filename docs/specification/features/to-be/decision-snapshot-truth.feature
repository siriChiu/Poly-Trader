@to_be @owner_approved @snapshot @projection @no_live_order
Feature: API、畫面與文件只顯示同一張完整狀態單
  為了不把不同時間與版本的資料拼成假現在
  作為owner與operator
  我需要一張完整、有編號、不可修改且可追查來源的DecisionSnapshot

  # Decision: docs/adr/ADR-0004-decision-snapshot-truth.md
  # Q4 accepted 2026-08-11.

  Background:
    Given 系統把完整狀態單稱為DecisionSnapshot
    And 每張snapshot都有唯一snapshot ID、generation ID與valid until
    And API、UI與generated docs都是projection而不是release或order authority

  Scenario: 完整狀態單記錄所有重要版本
    Given snapshot builder開始建置candidate
    When 它收集model、bundle、release、market、risk與venue輸入
    Then candidate包含每個輸入的identity、as-of與來源
    And 包含strategy、feature、label、model與bundle版本
    And 包含warning、blocking reasons與typed status

  Scenario: 狀態單完整後才一次發布
    Given candidate snapshot仍在建置
    When 只有部分輸入完成
    Then active snapshot不變
    And API與UI看不到半張candidate
    When candidate通過schema、identity與freshness驗證
    Then 系統以atomic pointer一次切換active snapshot ID

  Scenario: 建置失敗不會把新舊資料混合
    Given 上一張active snapshot完整可讀
    And 新candidate因一個輸入失敗而無法完成
    When builder結束
    Then 不發布candidate
    And 上一張snapshot內容保持immutable
    And 不得只覆蓋成功的新欄位

  Scenario: 舊狀態單可以顯示但必須說明年齡
    Given 最新candidate建置失敗
    And 上一張active snapshot尚未過valid until
    When API回應current state
    Then 回傳上一張完整snapshot
    And 保留原snapshot ID、generated at與age
    And 明確顯示最新建置失敗warning

  Scenario: 過期狀態單不能冒充現在正常
    Given active snapshot已超過valid until
    When API、UI或ExecutionAuthorizer讀取它
    Then projection顯示STALE或UNKNOWN
    And risk-on authorization fail closed
    And 不得以舊JSON或config補值變成READY

  Scenario: 明確的zero與false不會被舊值覆蓋
    Given current snapshot的support是0且can execute是false
    And 舊artifact有非零support與true
    When projection建立
    Then current 0與false原樣保留
    And 不得用truthy fallback選舊值

  Scenario: 同一個API response只使用一個snapshot
    Given active snapshot ID是S2
    When current-state API組裝response
    Then 所有卡片、gate、evidence、risk與venue欄位都來自S2
    And response最上層包含S2與generation metadata

  Scenario: 同一個畫面不合併不同snapshot
    Given 主狀態response屬於S2
    And 次要圖表response屬於S1
    When UI準備render同一個current-state頁面
    Then UI不得把S1圖表當成S2現在狀態
    And 顯示refresh required或清楚的historical標籤

  Scenario: generated docs必須標明snapshot ID
    Given current-state Markdown由系統產生
    When 文件寫入狀態數字
    Then 文件包含snapshot ID、generated at與valid until
    And evergreen policy文件不複製這些時變數字

  Scenario: 不同generation的即時probe不能覆寫主狀態
    Given active snapshot是S2
    And 一個較新的probe沒有S2 generation identity
    When API準備overlay probe結果
    Then probe只能顯示為獨立觀測
    And 不得覆寫S2的market、venue或execution status

  Scenario: 讀取API不會順便改系統
    Given active snapshot已存在
    When current-state GET endpoint被呼叫
    Then endpoint只讀取並投影snapshot
    And 不得在request path訓練模型、回填feature、刷新probe或寫入policy state

  Scenario: 底層資料更新要等下一張完整狀態單才公開
    Given active snapshot是S2
    And release registry或market data出現新版本
    When S3尚未完整驗證與發布
    Then API與UI仍完整顯示S2並標明as-of
    And 不得把新版本單一欄位插入S2

  Scenario: 並行builder不會互相拼接
    Given 兩個builder同時建立不同generation candidate
    When 它們完成順序不同
    Then 每張candidate各自immutable
    And active pointer只指向一張通過驗證的完整snapshot
    And 任何response不得同時引用兩張candidate的欄位

  Scenario: order intent必須引用狀態單
    Given operator從active snapshot S2啟動Live Canary intent
    When intent進入ExecutionAuthorizer
    Then intent引用S2的snapshot ID與exact bundle identity
    And authorizer拒絕過期、非active或identity mismatch的snapshot

  Scenario: READY狀態不能取代最後一刻安全檢查
    Given active snapshot顯示Live Canary READY
    When order準備送到venue
    Then authorizer仍檢查fresh quote、kill switch、exposure、single-use permit與idempotency
    And 任一last-mile檢查失敗就不送單

  Scenario: 找不到完整狀態單時直接說不知道
    Given 沒有任何完整且可驗證的snapshot
    When current-state API被呼叫
    Then 回傳UNKNOWN或service unavailable類型狀態
    And 不得從config、DB與JSON臨時拼出ready answer
