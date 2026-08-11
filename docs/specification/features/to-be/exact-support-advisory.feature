@to_be @owner_approved @evidence @support @no_live_order
Feature: Exact support不足只顯示警告
  為了不讓固定sample count反覆阻塞owner-approved極小額canary
  作為strategy owner
  我需要把exact support當成信心資訊，而不是交易開關

  # Decision: docs/adr/ADR-0003-exact-support-advisory.md
  # Characterization: docs/specification/as-is-gating-lineage.md
  # Q3 accepted 2026-08-11.

  Background:
    Given Owner release依ADR-0002永久有效且只能手動撤銷
    And 近期實戰依ADR-0001固定為極小額單層Live Canary
    And hard execution safety與support sample count分離

  Scenario: support不足只產生warning
    Given exact support目標是50筆
    And current exact support少於50筆
    When evidence assessment建立
    Then support status是WARNING或等價advisory狀態
    And 顯示current rows、target rows、ratio與as-of
    But blocking必須是false

  Scenario: support不足不撤銷Owner release
    Given Owner release狀態是ACTIVE
    And exact support不足
    When release projection建立
    Then Owner release保持ACTIVE
    And 不得產生automatic revocation

  Scenario: support不足不阻止極小額單層Live Canary
    Given exact support不足
    And Live Canary的所有hard safety gates都通過
    And current market允許risk-on intent
    When ExecutionAuthorizer評估order
    Then support warning不得拒絕order
    And order仍受極小額cap、單層與single-use permit限制

  Scenario: support不足不把allowed layers改成zero
    Given market capacity允許第一層
    And exact support不足
    When final capacity組裝
    Then support evidence不得把capacity改成0
    And Live Canary capacity仍由ADR-0001固定最多一層

  Scenario: 每筆order不重新執行固定50筆hard gate
    Given current DecisionSnapshot已包含support advisory
    When 一筆risk-on order進入ExecutionAuthorizer
    Then authorizer只驗證snapshot identity與hard safety
    And 不重新把sample target計算成order blocker

  Scenario: support達標不自動增加風險
    Given exact support已達或超過目標
    When evidence assessment更新
    Then confidence狀態可改為better-supported
    But 不自動增加order cap或pyramid layers
    And 不自動啟用Full Auto Live

  Scenario: support達標不解除technical blocker
    Given exact support已達標
    But runtime bundle mismatch或venue unavailable
    When readiness建立
    Then support顯示better-supported
    And risk-on仍被technical blocker拒絕

  Scenario: support zero必須保留為zero
    Given current generation的exact support明確是0
    And older artifact記錄非零support
    When API或overview組裝projection
    Then current support保持0
    And 不得以truthy fallback採用舊正值

  Scenario: stale support只能顯示unknown或stale
    Given support artifact已超過TTL
    When UI顯示confidence
    Then support狀態是STALE或UNKNOWN
    And 不得顯示為current 0或current passed
    And stale狀態仍只是evidence unavailable而非order blocker

  Scenario: 不同candidate的support不可替代current candidate
    Given shadow evidence屬於bundle A
    And current Live Canary candidate是bundle B
    When support projection建立
    Then A的support只能作reference
    And B的exact support warning不得被A解除
    And B仍可在hard safety全通過時做極小額單層canary

  Scenario: moving bucket不會造成release或canary反覆關閉
    Given market regime改變導致exact support bucket改變
    When 新bucket sample count重新變少
    Then warning內容更新為新bucket
    But Owner release不變
    And hard-safety-ready的極小額單層canary不因sample count反覆開關

  Scenario: heartbeat不能把support warning升級為blocking issue
    Given support不足是advisory
    When heartbeat或PM文件發布current status
    Then 它可以建立研究warning或資料診斷next action
    But 不得宣稱補滿50筆是Live Canary唯一解鎖條件
    And 不得改寫runtime blocking狀態

  Scenario: 等待樣本不能冒充修復資料或模型問題
    Given 系統存在4H look-ahead、label mismatch、feature missingness或model bias
    When support rows隨時間增加
    Then 這些結構問題仍需獨立修復與重新驗證
    And support數量增加不得自動讓受污染evidence變成可信

  Scenario: UI用白話區分信心警告與安全阻塞
    Given support不足但hard safety全部通過
    When operator查看Live Canary狀態
    Then UI顯示「類似案例較少，信心較低」
    And UI另行顯示「可做極小額單層canary」
    And 不得把warning顯示成禁止交易的紅色hard blocker
