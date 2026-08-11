@to_be @owner_approved @docs @ai @authority @no_live_order
Feature: 文件與AI不能直接授權真實下單
  為了避免過期文字或AI誤解影響資金
  作為strategy owner
  我需要execution只相信正式機器規則、核准紀錄與單次permit

  # Decision: docs/adr/ADR-0009-docs-ai-non-authoritative.md
  # Q8 accepted 2026-08-11.

  Background:
    Given 文件與AI內容都是non-authoritative explanation或proposal
    And Owner decision registry保存正式核准與撤銷
    And ExecutionAuthorizer是每筆risk-on order的唯一授權邊界

  Scenario: 文件寫READY不能放行order
    Given evergreen或generated Markdown寫著READY或approved
    But machine policy或DecisionSnapshot顯示BLOCKED
    When risk-on intent進入ExecutionAuthorizer
    Then intent被拒絕
    And 文件文字不得覆蓋machine blocker

  Scenario: AI回答可以交易不能成為permit
    Given AI summary說「現在可以交易」
    But 沒有signed single-use permit
    When caller提交non-dry order
    Then ExecutionAuthorizer拒絕order
    And adapter不收到place-order call

  Scenario: 一般聊天同意不會直接切runtime gate
    Given Owner在聊天中表達產品決策
    When runtime收到新risk-on intent
    Then 聊天文字本身不改live bundle、cap或release registry
    And 必須先完成authenticated formal decision workflow

  Scenario: 正式Owner action建立可驗證record
    Given Owner在受信任UI或等價workflow確認release、revocation或bundle switch
    When system接受action
    Then 建立stable decision ID與actor identity
    And 記錄target bundle或policy、reason、timestamp與generation
    And audit record是append-only

  Scenario: AI可以提出修改但不能直接套用
    Given AI發現policy、code或gate需要改善
    When AI產生change proposal
    Then proposal包含原因、風險與BDD
    But 正在運作的machine policy保持不變

  Scenario: Machine policy變更要通過正式工程流程
    Given Owner接受AI的policy change proposal
    When 變更準備發布
    Then machine policy有新version
    And tests、review與deployment verification通過
    And 新DecisionSnapshot引用新policy version

  Scenario: Generated report不能反向改寫release
    Given report根據舊snapshot顯示release revoked或blocked
    But release registry的較新正式record是ACTIVE
    When projection重新建立
    Then release authority仍是registry record
    And report被標為stale而不是改寫registry

  Scenario: 舊文件不能復活revoked release
    Given Owner已正式撤銷release
    And 舊PRD、report或AI memory仍寫ACTIVE
    When risk-on authorization執行
    Then release status是REVOKED
    And 舊文字不得復活release

  Scenario: Read API不呼叫AI決定gate
    Given current-state GET endpoint被呼叫
    When response建立
    Then 它只投影active DecisionSnapshot與machine records
    And 不得解析Markdown或呼叫LLM產生authorization
    And read path沒有policy side effect

  Scenario: UI分開顯示建議與正式狀態
    Given AI建議切換bundle B
    But Owner尚未正式選擇
    When UI顯示current state
    Then AI區顯示「建議」
    And Owner release/live bundle區仍顯示原正式狀態
    And 按鈕不能因建議文字自動變成已核准

  Scenario: Machine state blocked時衝突fail closed
    Given AI或文件說READY
    And machine state說BLOCKED
    When UI與ExecutionAuthorizer處理衝突
    Then UI顯示source conflict與as-of
    And ExecutionAuthorizer保持BLOCKED
    And 建立修正projection或文件的工作

  Scenario: AI不能自行提高保守風險上限
    Given R1上限已正式核准
    When AI、Heartbeat或generated config建議更高cap
    Then runtime拒絕較高值
    And 要求新的Owner decision與versioned policy

  Scenario: AI不能簽發或重放permit
    Given AI知道bundle、order與cap資料
    When 它嘗試建立或重用permit
    Then permit service拒絕未授權actor或duplicate nonce
    And AI文字不能充當signature

  Scenario: Kill switch建議與正式啟動分離
    Given AI偵測到高風險並建議立即停止
    When 沒有authenticated kill-switch action
    Then AI recommendation清楚顯示但不偽造machine state
    When 受權actor正式啟動kill switch
    Then machine state立即阻止risk-on並留下audit record

  Scenario: 解除Kill switch不能只靠一句文字
    Given kill switch已正式啟動
    When 文件、AI或聊天說問題已修復
    Then kill switch仍保持active
    And 只有符合權限與驗證流程的正式action可以解除

  Scenario: AI輸出標示來源與非權威性
    Given AI產生current-state摘要或模型切換建議
    When 內容呈現在UI或generated report
    Then 內容包含generated at與source snapshot ID
    And 標示為建議或說明而非execution authority
