@as_is @governance @documentation
Feature: Documentation truth、AI decision input與歷史隔離
  為了避免舊數字與generated narrative控制未來工程判斷
  作為AI agent與owner
  我需要知道每份文件的type、authority、TTL與supersedes relation

  # Sources: AGENTS.md, docs/ai-collaboration/*,
  # scripts/doc_topology_check.py, scripts/hb_parallel_runner.py,
  # tests/test_doc_topology.py

  Scenario: root AGENTS提供repository discovery map
    Given agent進入repository
    When 讀取AGENTS.md
    Then 它被導向heartbeat、PM、issues、roadmap與ORID文件
    And 這些文件會成為後續agent decision input

  @known_gap
  Scenario: generated current docs沒有明確低於machine policy的authority
    Given ISSUES、ROADMAP、ORID或pm-status由heartbeat覆寫
    When 下一輪agent依AGENTS指示讀取
    Then 文字可能被當成binding current truth
    And 文件沒有統一machine-readable authority/TTL metadata阻止此行為

  @known_inconsistency
  Scenario: evergreen AI role包含固定model metric gate
    Given AI_AGENT_ROLE要求accuracy大於90%或IC threshold
    But 產品策略排序以ROI、低drawdown、DQ與PF為主
    When agent選擇下一項模型工作
    Then 兩份文件可能導向不同優化目標

  @known_inconsistency
  Scenario: personal release policy包含stale runtime數字
    Given policy文字聲稱latest support是某固定ratio
    And request-time runtime已有不同ratio
    When agent只讀policy
    Then 可能錯判current evidence與next action

  @known_inconsistency
  Scenario: strategy decision guide混入dated研究結論
    Given evergreen guide包含特定日期/model結果與舊owner名稱
    When 新資料世代進入
    Then 歷史結論仍可能被誤當永久策略規則

  Scenario: dated historical closure不得作current truth
    Given 文件名稱或frontmatter標明historical date
    When agent判斷現在runtime
    Then 必須查詢直接runtime source
    And historical文件只作decision context

  Scenario: docs topology checker驗證active Markdown位置
    Given repo新增active Markdown
    When doc_topology_check執行
    Then 文件必須位於允許的docs目錄或approved root
    And 違規路徑使check失敗

  @known_gap
  Scenario: 現行topology checker不驗semantic type與authority
    Given 一份runtime status被放進允許的policy或analysis目錄
    When doc_topology_check執行
    Then 它仍可能通過
    And checker不驗document_type、authority、TTL、generated_at或supersedes

  Scenario: credentials不得出現在docs/artifacts
    Given agent產生status、evidence或error report
    When 內容可能包含API key/secret/passphrase
    Then 值必須redact為 `[REDACTED]`
    And 不得commit credential

  Scenario: policy文件不得授權live action
    Given docs說明某strategy已personal released
    When ExecutionService處理non-dry order
    Then 它只接受versioned config/registry/snapshot/permit
    And 不解析Markdown來開啟live trading

  @known_gap
  Scenario: ORID decisions目前是overwrite projection而非immutable ADR
    Given heartbeat完成一輪
    When ORID_DECISIONS.md被重寫
    Then 先前decision的精確context/superseded chain可能只存在Git history
    And 無法像append-only ADR直接追蹤

  Scenario: 重構規格將as-is與to-be分開
    Given owner尚未回答open question
    When BDD文件更新
    Then as-is feature只描述現行行為
    And proposed behavior不得冒充已實作
    And owner決定後另建to-be feature與ADR
