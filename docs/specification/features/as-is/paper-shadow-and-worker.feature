@as_is @paper @shadow @worker
Feature: Paper Shadow evidence、run control與worker liveness
  為了在不送真單下驗證exact candidate與order decision流程
  作為owner
  我需要candidate-scoped shadow evidence與可信worker狀態

  # Sources: execution/control_plane.py, execution/live_runner.py,
  # server/routes/api.py, tests/test_execution_run_control.py,
  # tests/test_live_trading_runner.py,
  # tests/test_execution_truth_contract.py

  Scenario: user啟動saved strategy的paper-shadow run
    Given saved strategy存在且可建立exact immutable bundle
    When `/api/strategies/{name}/paper-shadow`被呼叫
    Then 系統freeze strategy binding
    And 建立或選擇paper execution profile
    And 執行一個safe worker tick
    And order submission保持dry-run

  Scenario: exact model缺失時worker不使用placeholder
    Given saved strategy指定exact fitted model
    But artifact不存在或schema不相容
    When worker啟動
    Then run fail closed
    And event說明exact-model blocker

  Scenario: shadow candidate可由HOLD轉成no-submit evidence proposal
    Given shadow_candidate_enabled
    And normal decision是HOLD
    And market row有效且timestamp存在
    When runner執行 `_maybe_force_shadow_candidate`
    Then action變為SHADOW_CANDIDATE
    And order_submission_enabled是false
    And live_order_submitted是false
    And 不呼叫ExecutionService

  Scenario: 同一feature timestamp只記錄一個shadow candidate
    Given 同strategy hash、symbol、venue與feature timestamp已有shadow candidate
    When runner再次處理同timestamp
    Then duplicate candidate被skip
    And reason是shadow_candidate_already_recorded

  @known_gap @safety
  Scenario: duplicate candidate檢查不是DB atomic invariant
    Given 兩個worker同時查詢相同feature timestamp
    And 兩者都在insert前看到count為0
    When 兩者記錄decision
    Then 現行check-then-write可能產生race
    And DB沒有顯示對該business key的unique constraint

  Scenario: 1440m outcome reconciliation只配對相同symbol與時間窗
    Given expired shadow candidate有symbol與proposal time
    When reconciliation查找label outcome
    Then SQL先依normalized symbol、1440m horizon與bounded time range縮小
    And Python再選nearest label
    And 超過允許tolerance不得配對

  Scenario: canonical overview保留100-candidate semantics
    Given reconciliation summary被建立
    When execution overview查詢
    Then 最多使用canonical 100 candidates
    And 不得為效能偷偷改成10而改變56/44或其他resolved/pending語義

  Scenario: pending candidate在label成熟後轉resolved
    Given candidate horizon已到且匹配label出現
    When 下一輪reconciliation執行
    Then candidate狀態由pending轉resolved
    And resolved evidence統計更新

  Scenario: generic shadow evidence不得替不同candidate放行
    Given resolved outcomes來自random-forest hybrid bundle
    And owner release要求logistic current_full bundle
    When promotion gate評估
    Then 這些outcomes只作diagnostic/reference
    And 不得解除owner candidate的exact runtime binding或support gate

  Scenario: persisted run status不是process liveness
    Given execution_runs row顯示RUNNING
    But 沒有process lease或worker process存活
    When worker status endpoint查詢
    Then 不得只靠persisted state回報live
    And 應標示stale/orphaned/not live

  Scenario: live process死亡會更新operator-visible status
    Given worker曾啟動且有process identity/lease
    When process退出或lease過期
    Then API status不再顯示healthy running
    And 保留last event/exit reason供診斷

  Scenario: stop與retry形成可追蹤run events
    Given operator停止或重試run
    When control plane處理action
    Then run state transition與event被持久化
    And 新run/retry不覆蓋舊run history
