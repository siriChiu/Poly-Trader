@as_is @research @evidence
Feature: 模型證據、leaderboard 與策略研究
  為了優先選擇高 ROI、低回撤、低頻高信心策略
  作為策略 owner
  我需要研究證據與 execution authorization 分離

  # Sources: backtesting/model_leaderboard.py, backtesting/strategy_lab.py,
  # tests/test_strategy_lab.py, tests/test_model_leaderboard.py,
  # tests/test_model_leaderboard_api_cache.py

  Scenario: canonical model target 是 simulated pyramid decision quality
    Given model leaderboard 有 simulated_pyramid_win target
    When model candidates 被評估
    Then simulated_pyramid_win 是 canonical 主 target
    And label_spot_long_win 只作 path-aware 比較診斷

  Scenario: strategy leaderboard 依產品決策排序
    Given 兩個 saved strategies都有可比較 backtest results
    When Strategy Lab建立 leaderboard
    Then 優先比較 ROI
    And ROI相近時偏好較低 max drawdown
    And 再比較 average decision quality score
    And 再比較 profit factor
    And win rate只作reference而非唯一主排序

  Scenario: 模型證據包含walk-forward與overfit資訊
    Given candidate model已完成rolling/walk-forward evaluation
    When leaderboard row序列化
    Then 輸出 train與test metrics
    And 輸出fold coverage與generalization gap
    And overfit candidate不得被選為非overfit最佳模型

  Scenario: 不可比較placeholder不應冒充leaderboard證據
    Given 某模型因dependency或training failure無法產生完整metrics
    When API回傳leaderboard
    Then 該row被標記placeholder或non-comparable
    And 不應取得deployable ranking

  Scenario: user-saved策略都出現在Strategy Lab leaderboard
    Given owner儲存一個非system-generated strategy
    When `/api/strategies/leaderboard` 被查詢
    Then 該strategy出現在leaderboard
    And 可重新載入與編輯

  Scenario: system-generated策略不可由一般編輯流程覆寫
    Given strategy被標為system-generated/internal
    When 一般使用者請求修改或刪除
    Then 系統保持immutable/protected
    And 它仍可作比較基準

  Scenario: saved strategy儲存在repo外operator store
    Given owner儲存策略
    When strategy_lab.save_strategy執行
    Then JSON寫入 `~/.hermes/poly-trader/strategies`
    And strategy identity不只由Git commit決定

  @known_inconsistency
  Scenario: model leaderboard 有多層cache與history truth
    Given memory cache、disk cache與DB history的generation不同
    When leaderboard API組裝response
    Then 現行程式會選擇其中一份可用payload
    And 可能再套request-time live overlay
    And response沒有保證所有欄位來自同一generation

  @known_inconsistency @generated_state
  Scenario: GET leaderboard可觸發background model refresh
    Given leaderboard cache缺失或stale
    When client執行GET `/api/models/leaderboard`
    Then API可啟動daemon thread重跑models
    And 一個表面read-only request可能消耗大量CPU並更新cache/artifacts

  Scenario: fresh cache可避免同步heavy refresh
    Given cache仍在freshness window
    When 一般GET leaderboard
    Then API回傳cache
    And 不需要在request critical path重新訓練全部模型

  Scenario: strategy evidence不能直接授權order
    Given candidate有高ROI、低drawdown與良好profit factor
    When evidence被標為release-ready或owner-approved
    Then 它仍不得產生execution permit
    And runtime binding、market actionability、venue readiness與order safety仍獨立判斷

  @known_gap
  Scenario: evidence row缺少完整不可變dataset lineage
    Given 同名model與feature profile在不同資料世代重新評估
    When 只比較leaderboard row fields
    Then 現行row可能缺少training data snapshot hash與label definition version
    And 無法只靠model名/profile證明是同一候選
