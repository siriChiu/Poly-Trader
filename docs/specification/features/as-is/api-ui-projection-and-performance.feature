@as_is @api @ui @performance
Feature: API aggregate、Strategy Lab與Execution UI projection
  為了讓使用者看到一致且可解釋的狀態
  作為frontend與API
  我需要只投影domain truth而不偷偷重算授權

  # Sources: server/routes/api.py, execution/console_overview.py,
  # web/src/pages/StrategyLab.tsx, Execution.tsx, Dashboard.tsx,
  # tests/test_execution_console_overview.py,
  # tests/test_server_startup.py, tests/test_frontend_decision_contract.py,
  # tests/test_model_leaderboard_api_cache.py, tests/test_strategy_lab.py

  Scenario: status endpoint回傳可解釋current-live state
    Given backend可讀取latest data與predictor
    When client查詢 `/api/status`
    Then response包含signal、confidence、entry quality、allowed layers與blocker
    And 包含personal release/runtime binding projection
    And 錯誤或缺資料時fail closed而非捏造trade signal

  Scenario: execution overview一次建立canonical runner evidence
    Given overview需要run profiles、runs與100-candidate reconciliation
    When endpoint處理單一request
    Then 不得在route fallback再次重建同一live-runner overview
    And response維持canonical 100-candidate semantics

  Scenario: execution overview需穩定低於probe timeout
    Given canonical dataset規模
    When overview連續查詢
    Then 每次回HTTP 200
    And latency低於10秒consistency probe timeout
    And 效能修正不得縮短evidence window改變語義

  Scenario: Strategy Lab顯示所有saved strategies與可排序leaderboard
    Given user與system strategies存在
    When Strategy Lab載入
    Then user-saved strategy可選取、回填與編輯
    And system-generated strategy顯示protected
    And leaderboard可依多維績效排序

  Scenario: Strategy Lab區分研究競爭力與execution readiness
    Given strategy有ROI/DD/PF證據
    But runtime binding或venue readiness未通過
    When UI呈現row/detail
    Then 研究績效仍可比較
    And live execution不得顯示ready

  Scenario: Dashboard顯示raw 4H values與freshness
    Given latest 4H feature snapshot可用
    When Dashboard呈現
    Then 顯示raw 4H values
    And 顯示資料as-of/freshness
    And 不只顯示抽象pass/fail badge

  Scenario: execution rejected response帶structured reason
    Given buy被current-live、canary或permit gate拒絕
    When API回傳error
    Then response含stable reason code與operator message
    And frontend不必解析Markdown文字猜原因

  @known_inconsistency
  Scenario: API組裝層重算domain policy
    Given predictor已產生release/binding/blocker payload
    When status或leaderboard API組裝response
    Then 現行route/console helpers仍可推導新的readiness、fallback與copy
    And 同一gate可能在不同endpoint顯示不同primary blocker

  @known_bug @generation @fallback
  Scenario: fresh-by-wall-clock probe 可覆蓋不同identity的request-time prediction
    Given request-time predictor已使用current feature timestamp與loaded model
    And live_predict_probe在wall-clock TTL內
    But probe沒有與current feature timestamp、model SHA及config revision綁定
    When confidence API套用probe與q15 q35 overlays
    Then 現行payload可能混合不同generation的欄位
    And to-be identity mismatch必須回inconsistent或unavailable而不是靜默overlay

  @known_inconsistency
  Scenario: GET endpoint可能有heavy side effect
    Given leaderboard cache stale
    When frontend只讀GET leaderboard
    Then backend可啟動background evaluation
    And read-only UI flow可能消耗CPU或改cache/artifacts

  Scenario: browser UI不得在API失敗時顯示false success
    Given backend API timeout或回傳error
    When frontend fallback執行
    Then 頁面顯示unknown/error/stale
    And 不得顯示live ready或已啟動worker

  Scenario: raw Vite dev UI不能冒充authenticated backend shell
    Given frontend在raw Vite port運行
    But backend session token只由backend-served shell注入
    When 執行browser QA
    Then 應使用backend-served dashboard URL驗證authenticated routes

  @known_gap
  Scenario: UI copy contract過度綁定implementation tokens
    Given tests斷言多個humanized literal與欄位名稱
    When backend domain model需要簡化
    Then 現有tests可能因copy變更失敗
    And to-be應保留reason code/meaning contract而非每個舊文字token
