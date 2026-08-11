@as_is @promotion @gates
Feature: Strategy promotion與多維 readiness state
  為了避免單一 deployable boolean掩蓋原因
  作為owner與operator
  我需要分別看到evidence、release、binding、market與order狀態

  # Sources: model/runtime_closure.py, model/personal_release.py,
  # model/predictor.py, server/routes/api.py,
  # tests/test_runtime_closure_copy.py,
  # tests/test_personal_release_policy.py, tests/test_server_startup.py

  Scenario: research candidate只有evidence status
    Given candidate只有walk-forward/OOS metrics
    When promotion status建立
    Then 它可被標為research evidence ready
    But 不得被標為runtime bound或order authorized

  Scenario: owner release只改release dimension
    Given owner核准指定strategy identity
    When personal release policy套用
    Then release status是RELEASED_FOR_PERSONAL_USE
    And execution permit仍不存在
    And venue capability不因此改變

  Scenario: runtime binding failure只阻止deployment capacity
    Given owner release存在
    But runtime bundle identity不匹配
    When runtime closure組裝
    Then release status仍保留
    And runtime binding status是blocked
    And final allowed layers是0

  Scenario: market HOLD不撤銷策略release
    Given release與binding都成立
    But current entry conditions未通過
    When current signal建立
    Then market actionability是HOLD
    And release/bundle identity仍有效

  Scenario: venue unavailable不改寫model evidence
    Given strategy evidence與release成立
    But credentials或venue connection unavailable
    When execution overview建立
    Then evidence保持原狀
    And venue capability是blocked/unknown
    And order authorization是blocked

  Scenario: execution permit是per-order而非strategy永久旗標
    Given strategy、bundle、market與venue都ready
    When 一筆order被授權
    Then permit綁定該order scope與短TTL
    And 不能作為下一筆order的永久live ready旗標

  @known_inconsistency
  Scenario: 現行deployable欄位由多層重算
    Given 同一candidate通過owner release
    When predictor、Top-K overlay、runtime closure、API與heartbeat依序處理
    Then 各層可能再次設定deployable、deployment_blocker與allowed_layers
    And 最後值依composition order而非單一state machine決定

  Scenario: statistical advisory不得蓋過technical blocker
    Given exact support不足形成warning
    And runtime binding也失敗
    When promotion payload組裝
    Then primary execution blocker仍是technical binding failure
    And support warning保留在evidence dimension

  Scenario: technical blocker解除後不自動送單
    Given runtime binding或breaker blocker剛解除
    When next snapshot建立
    Then system只更新readiness
    And 仍需新的market signal與per-order authorization

  @known_gap
  Scenario: current payload缺少shared generation identity
    Given release來自config
    And binding來自runtime payload
    And support來自DB與artifact
    And venue readiness來自metadata smoke
    When API組成aggregate
    Then 各dimension可能有不同as-of
    And 現行aggregate沒有單一immutablegeneration ID保證一致
