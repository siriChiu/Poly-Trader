@to_be @owner_approved @live_canary @no_live_order
Feature: 近期實戰完成定義為受監督 Live Canary
  為了在保留hard execution safety下完成第一個真實交易里程碑
  作為策略owner與operator
  我需要一條極小額、單層、人工監督且可完整reconcile的live canary journey

  # Decision: docs/adr/ADR-0001-live-canary-product-scope.md
  # Characterization: docs/specification/features/as-is/execution-authorization.feature
  # Q1 accepted 2026-08-11; authorization entry point remains pending Q9.

  Background:
    Given 本階段產品目標是Live Canary
    And Full Auto Live是後續獨立milestone
    And CI與BDD verification不得送真單

  Scenario: Paper與Shadow是必要前置但不是最終完成條件
    Given exact candidate已完成Paper與Shadow rehearsal
    When owner檢查本階段Definition of Done
    Then Paper與Shadow evidence可滿足前置條件
    But 只有它們不能把Live Canary milestone標成complete

  Scenario: Live Canary最多部署單一pyramid layer
    Given owner-approved strategy原本支援20%到30%到50%多層金字塔
    When strategy進入本階段Live Canary
    Then risk-on capacity最多是第一層
    And 第二層與第三層自動加倉維持disabled

  Scenario: Live Canary必須使用明確極小額cap
    Given operator準備Live Canary order
    When execution policy建立authorization
    Then symbol必須存在explicit allowlist
    And symbol必須有明確base quantity或notional cap
    And 空allowlist不得被解讀成允許所有symbol
    And requested order不得超過cap

  Scenario: Live Canary必須綁定exact released bundle
    Given owner release存在
    When runtime準備產生risk-on intent
    Then loaded strategy與model必須對應同一immutable release/bundle
    And 必須驗證model artifact SHA、feature schema、label/target/horizon與execution policy identity
    And config中的verified boolean不能自行證明binding

  Scenario: 每筆risk-on order需要current decision envelope與single-use permit
    Given exact bundle與market actionability都通過
    When risk-on order進入ExecutionAuthorizer
    Then order必須帶短效single-use permit
    And permit綁定order scope、bundle identity、decision generation、quote timestamp、venue、cap與nonce
    And permit缺失、過期、重放或claims mismatch時fail closed

  Scenario: 人工監督是必要條件
    Given 系統提出一筆Live Canary intent
    When operator尚未執行明確arm或approve動作
    Then permit不得簽發
    And adapter不得收到non-dry place-order call
    And 最終採manual UI或受管worker approval入口由Q9決定

  Scenario: stale或inconsistent current truth阻止risk-on
    Given strategy evidence、release與bundle看似ready
    But quote、decision generation、venue proof或risk state任一stale unknown或identity mismatch
    When Live Canary authorization評估
    Then risk-on order被fail closed
    And response包含stable reason code、observed_at與release condition

  Scenario: support不足不撤銷owner release
    Given owner已核准immutable strategy release
    And exact support仍不足
    When Live Canary readiness被評估
    Then owner release record保持accepted
    And support仍以evidence warning或owner核准的capacity policy呈現
    But support不能代替exact bundle、permit、venue或order safety

  Scenario: risk-on blocked時保留安全的risk-off path
    Given Live Canary position已存在
    And 新risk-on因kill switch、breaker或cap被blocked
    When operator要求reduce或exit
    Then 系統使用獨立risk-off authorization contract
    And 不應被risk-on layer cap錯誤阻止
    And venue/account無法安全退出時回reconcile-required而非虛構成功

  Scenario: local submit acknowledgement不等於成交
    Given adapter接受Live Canary order
    When 系統回報operator狀態
    Then 先顯示submitted或acknowledged
    And partial fill、fill、cancel、reject與unknown分別持久化
    And 只有venue reconciliation後才能顯示terminal truth

  Scenario: duplicate intent不會產生第二筆venue order
    Given 同一bundle、decision generation與action已有OrderIntent
    When 另一個worker或retry同時提交相同business key
    Then DB-level unique/idempotency invariant只允許一筆intent
    And adapter最多收到一次place-order call

  Scenario: 完成Live Canary不會自動完成Full Auto Live
    Given 一筆受監督Live Canary已完成submit與lifecycle reconciliation
    When product milestone更新
    Then Live Canary可標成complete
    But unattended risk-on、multi-layer pyramiding與Full Auto Live仍是not approved

  Scenario: Live Canary真正執行需要owner明確arm
    Given 所有preflight與BDD acceptance已通過
    But owner尚未明確arm真實canary run
    When 系統執行自動驗證或CI
    Then 只能執行dry-run、paper、shadow與no-submit probes
    And 不得因本feature是owner-approved就自動送真單
