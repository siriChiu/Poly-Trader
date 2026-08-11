@to_be @owner_approved @release @governance @no_live_order
Feature: Owner Personal Release永久有效且只可手動撤銷
  為了讓owner治理決策不被rolling evidence或generated artifacts覆寫
  作為strategy owner
  我需要永久、可稽核、selector-scoped且只能由我撤銷的personal release

  # Decision: docs/adr/ADR-0002-personal-release-lifecycle.md
  # Characterization: docs/specification/features/as-is/personal-release-and-runtime-binding.feature
  # Q2 accepted 2026-08-11; full identity fields remain pending Q6.

  Background:
    Given owner personal release record已建立
    And release record有stable decision ID與subject selector
    And release本身不是execution permit

  Scenario: release沒有自動到期日
    Given release狀態是ACTIVE
    When 時間經過且沒有owner revocation
    Then release保持ACTIVE
    And 系統不得因固定TTL或定期review未完成而自動revoked

  Scenario: support不足不撤銷release
    Given release狀態是ACTIVE
    And current exact support低於evidence target
    When evidence assessment更新
    Then release保持ACTIVE
    And support不足只進入evidence warning或獨立capacity policy

  Scenario: evidence惡化不自動撤銷release
    Given release狀態是ACTIVE
    And rolling ROI、win rate或model-health evidence惡化
    When 新evidence snapshot發布
    Then release保持ACTIVE
    And 系統可要求owner review或阻止risk-on
    But 不得建立自動revocation record

  Scenario: circuit breaker不改寫release record
    Given release狀態是ACTIVE
    And model-health circuit breaker active
    When current decision snapshot建立
    Then release status仍是ACTIVE
    And technical capacity是0
    And risk-on order authorization是blocked

  Scenario: runtime binding mismatch不撤銷release
    Given release狀態是ACTIVE
    But runtime載入不同bundle identity
    When binding attestation執行
    Then release record保持ACTIVE
    And runtime binding status是mismatch
    And final risk-on capacity是0

  Scenario: 不同identity不會繼承永久release
    Given original release subject是strategy identity A
    And runtime candidate是identity B
    When release registry查詢B
    Then 結果是NOT_APPLICABLE或需要新的release
    And 原本A的release仍保持ACTIVE
    And B不得因A是永久release而被視為owner approved

  Scenario: heartbeat與generated artifact無權撤銷
    Given release狀態是ACTIVE
    When heartbeat、PM agent、probe或JSON artifact產生blocked狀態
    Then projection可顯示technical blocker
    But release registry不得被該producer改寫成REVOKED

  Scenario: 只有已驗證Owner能建立revocation
    Given release狀態是ACTIVE
    When 非Owner actor或自動job要求撤銷
    Then registry拒絕request
    And release保持ACTIVE

  Scenario: owner手動撤銷建立append-only record
    Given release狀態是ACTIVE
    When 已驗證Owner明確撤銷該decision ID
    Then registry寫入append-only revocation record
    And record包含actor、reason、revoked_at與generation ID
    And 原release record仍保留供audit

  Scenario: revocation立即阻止新的risk-on authorization
    Given release已被Owner撤銷
    When 新的Live Canary risk-on intent要求permit
    Then ExecutionAuthorizer拒絕intent
    And reason code是owner_release_revoked或等價stable code
    And adapter不得收到non-dry place-order call

  Scenario: revocation不應阻止安全risk-off
    Given release已被Owner撤銷
    And 該release仍有open position或open order需要降低風險
    When operator要求reduce、cancel或reconcile
    Then 系統使用risk-off authorization contract
    And 不得因release revoked而強迫保留曝險

  Scenario: stale config或cache不能復活revoked release
    Given registry有較新的revocation generation
    And config或artifact仍顯示舊ACTIVE狀態
    When API建立release projection
    Then authoritative status是REVOKED
    And stale source被標為generation mismatch
    And 系統不得以truthy fallback選擇ACTIVE

  Scenario: 重新核准需要新的owner decision record
    Given 原release已被Owner撤銷
    When Owner決定再次核准相同或新identity
    Then 建立新的release decision ID
    And 舊revocation與舊release保持immutable
    And 新decision不會改寫historical audit trail
