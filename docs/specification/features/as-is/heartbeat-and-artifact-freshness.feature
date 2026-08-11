@as_is @heartbeat @artifacts
Feature: Heartbeat fast slow lanes、artifact freshness與publication
  為了在240秒內可靠觀測系統而不製造自我強化的重建迴圈
  作為scheduler
  我需要把觀測、maintenance、heavy rebuild與docs publish分開

  # Sources: scripts/hb_parallel_runner.py,
  # docs/ai-collaboration/HEARTBEAT.md,
  # tests/test_hb_parallel_runner.py,
  # tests/test_hb_parallel_runner_elapsed_contract.py

  Scenario: fast heartbeat遵守240秒hard budget
    Given heartbeat mode是fast
    When all fast probes完成
    Then elapsed budget不得超過240秒
    And slow/expensive tasks不得偷偷進入fast critical path

  Scenario: stale Top-K或leaderboard只形成freshness debt
    Given Top-K或leaderboard artifact已stale
    When fast lane執行
    Then 它記錄freshness debt或next action
    And 不自動重建昂貴Top-K/leaderboard

  Scenario: heavy model與leaderboard refresh屬slow或explicit lane
    Given model artifact需要retrain或leaderboard需full refresh
    When fast lane觀測到需求
    Then 只排程/報告
    And 真正refresh由slow lane或explicit operator action執行

  Scenario: artifact freshness需同時考慮TTL與semantic identity
    Given artifact的generated_at仍在TTL內
    But artifact strategy/model/scope與current subject不符
    When artifact被載入
    Then 不得視為current deployment evidence
    And 應標為reference-only或semantic mismatch

  Scenario: DB已提供fresh current support時artifact fallback不得覆蓋
    Given request-time DB計算得到fresh exact support
    And 舊artifact也包含support值
    When live overlay組裝
    Then fresh DB context優先
    And 舊artifact不得把owner release或current blocker改回舊世代

  Scenario: support warning不撤銷persisted owner release
    Given owner release已persisted
    And heartbeat看到support不足
    When heartbeat生成summary
    Then release status保持
    And warning與allowed_layers cap分開呈現

  Scenario: no-collect mode不呼叫full external collection
    Given heartbeat以no-collect/fast lane啟動
    When rounds執行
    Then 不得跑完整市場來源收集
    And 應使用現有DB/artifacts做觀測

  @known_inconsistency
  Scenario: no-collect仍可做feature或label maintenance write
    Given DB有可修復的feature/label gap
    When heartbeat fast/no-collect runner執行maintenance path
    Then 現行runner可修改canonical DB
    And 操作名稱沒有完整表達side effect

  Scenario: generated artifact失敗時不得輸出虛構PASS
    Given probe timeout、exception或payload schema invalid
    When heartbeat收集結果
    Then status是failed/unknown/stale
    And 不得生成看似成功的數值

  @known_inconsistency
  Scenario: 一個monolithic run同時負責probe與治理文件
    Given `run_rounds`執行
    When 它完成artifacts與gate projection
    Then 現行程式也可能重寫ISSUES、ROADMAP、ORID與PM status
    And 觀測結果與治理敘事在同一failure domain

  @known_gap
  Scenario: 沒有material delta時仍可能產生tracked churn
    Given runtime數字或timestamps變動但產品能力沒有改變
    When heartbeat publication執行
    Then root/current docs與artifacts仍可能被重寫
    And Git history不易分辨semantic change與runtime churn
