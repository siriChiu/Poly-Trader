@as_is @decision @position
Feature: Current market signal、entry quality 與金字塔層數
  為了只做低頻高信心spot-long pyramiding
  作為decision engine
  我需要分辨市場條件、研究證據cap與technical cap

  # Sources: backtesting/strategy_lab.py, model/predictor.py,
  # execution/live_runner.py, tests/test_strategy_lab.py,
  # tests/test_api_feature_history_and_predictor.py,
  # tests/test_live_decision_quality_drilldown.py

  Scenario: regime gate BLOCK時不允許進場
    Given 4H bias/regime/structure判定為BLOCK
    When entry decision建立
    Then market allowed layers是0
    And signal保持HOLD或等價blocked state

  Scenario Outline: entry quality決定原始最大層數
    Given regime gate不是BLOCK
    And configured pyramid最多3層
    And entry quality是 <quality>
    When `_allowed_layers_for_signal`執行
    Then raw allowed layers是 <layers>

    Examples:
      | quality | layers |
      | 0.54    | 0      |
      | 0.60    | 1      |
      | 0.72    | 2      |
      | 0.85    | 3      |

  Scenario: 第一層進場需要所有entry checks通過
    Given 沒有open layer
    When runner建立decision
    Then regime不為BLOCK
    And current regime在allowed list
    And entry quality達minimum
    And rolling top-k gate通過
    And turning-point gate通過
    And bias50低於entry threshold
    And confidence達minimum
    And bias200達regime minimum
    Then 才能產生BUY_LAYER

  Scenario: 加層遵循20 30 50與逐層條件
    Given 已有一個或兩個open layers
    When 下一層被評估
    Then next layer index不得超過raw allowed layers
    And layer2/layer3有更嚴格bias threshold
    And reserve unlock規則必須通過
    And layer budget依strategy capital policy計算

  Scenario: exit先於new entry判斷
    Given 已有open layers
    When current price觸發stop loss、take-profit bias、ROI或turning-point exit
    Then decision產生SELL_ALL
    And 不再要求new-entry conditions

  Scenario: decision quality可縮小市場原始層數
    Given raw allowed layers大於0
    And historical decision quality/toxicity gate較弱
    When predictor套用DQ policy
    Then final allowed layers不大於raw allowed layers
    And position sizing可降到0

  Scenario: owner evidence warning可形成position cap
    Given owner release存在
    And evidence tier是limited或不足
    When release policy套用
    Then release record保持
    And final layers可受owner risk cap限制

  Scenario: technical blocker可令final layers為0
    Given runtime binding失敗或circuit breaker active
    When final capacity組裝
    Then final allowed layers是0
    And market raw layers不得被抹除

  @known_inconsistency
  Scenario: 同一allowed_layers欄位被多個overlay反覆改寫
    Given market regime計算出raw layers
    When DQ、support、runtime patch、breaker與personal release依序套用
    Then 多個步驟會mutate最終allowed_layers
    And deployment_blocker/reason可能被後來overlay覆蓋
    And caller不易分辨是哪一類capacity造成0

  @known_inconsistency
  Scenario: predictor與live runner各自重算entry公式
    Given 相同feature snapshot與strategy params
    When predictor與live runner分別建立decision
    Then 兩者都呼叫部分strategy_lab helpers
    But 各自仍有不同fallback、history與overlay
    And cross-path bit-for-bit parity不是單一domain service保證

  @known_gap @safety
  Scenario: latest feature timestamp沒有統一max-age authorization
    Given DB最新feature row已過期
    And runner以 `collect_market=false` 或collector未刷新讀取latest row
    When decision建立
    Then 現行runner可取得該row並計算signal
    And 沒有顯式統一quote/feature max-age gate
    And risk-on execution前必須新增fail-closed freshness authorization
