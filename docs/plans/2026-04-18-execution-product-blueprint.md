# Poly-Trader Execution 產品化設計藍圖

_最後更新：2026-04-18_

## 一句話決策
Poly-Trader 應把 execution 從「工程診斷附屬區」升級成 **Bot 營運主工作區**：
- `/execution` = **營運 / 盈虧 / Bot 控制**
- `/execution/status` = **執行狀態 / 對帳 / recovery / proof**
- `Dashboard` 與 `Strategy Lab` 只保留 **摘要同步 + CTA**，不再承擔 execution 深診斷主責。

這個方向符合目前前端與測試暴露出的現況：
- `web/src/App.tsx` 現在只有 `/`、`/execution`、`/senses`、`/lab`，execution IA 還不完整。
- `web/src/pages/ExecutionConsole.tsx` 已經拿得到 `ROI / PF / avg_expected_win_rate` 與 run ledger preview 型別（`unrealized_pnl / capital_in_use / budget_gap / commitment_vs_budget_ratio`），但首屏仍把「Bot 市集」放太前面。
- `web/src/pages/Dashboard.tsx` 目前承擔了 execution diagnostics、metadata governance、reconciliation、artifact checklist、timeline 等重負。
- `web/src/pages/StrategyLab.tsx` 目前同步太多 execution 細節，已超出研究頁的心智模型。

---

## 1) 新 IA / Routes

### 1.1 建議首層導航
1. `/` → **市場總覽**
2. `/execution` → **Bot 營運**
3. `/execution/status` → **執行狀態**
4. `/lab` → **Strategy Lab**
5. `/senses` → **特徵設定**

### 1.2 Route 責任切分

| Route | 導航名稱 | 使用者問題 | 內容責任 | 不應承載 |
|---|---|---|---|---|
| `/` | 市場總覽 | 現在市場如何？可不可以部署？ | 市場摘要、readiness 摘要、兩個 CTA | proof chain、artifact checklist、大段對帳細節 |
| `/execution` | Bot 營運 | 我開了哪些 bot？各自賺多少？要不要停？ | Bot 列表、PnL、資金占用、狀態、操作 | metadata governance 長篇敘事、lifecycle 細節 |
| `/execution/status` | 執行狀態 | 為什麼 blocked？要怎麼 recover？ | runtime truth、guardrails、metadata smoke、reconciliation、timeline | 策略回測、bot 建立主流程 |
| `/lab` | Strategy Lab | 哪個策略值得用？ | 回測、DQ、leaderboard、策略建立來源 | execution 深診斷主頁 |
| `/senses` | 特徵設定 | 特徵成熟度如何？ | 特徵管理 | execution 主流程 |

### 1.3 Nav 順序建議
**Primary**：市場總覽 / Bot 營運 / Strategy Lab  
**Secondary**：執行狀態 / 特徵設定

理由：
- 對產品價值來說，`Bot 營運` 比 `特徵管理` 更接近核心回訪任務。
- `執行狀態` 很重要，但它是高價值診斷頁，不應搶走 `/execution` 的營運主入口角色。

### 1.4 Route Contract 建議
既有 `/api/status` 已有 `execution_surface_contract`，第一輪先沿用，但語意要改清楚：

```ts
execution_surface_contract = {
  canonical_execution_route: "/execution",
  canonical_surface_label: "Bot 營運",
  operations_surface: {
    route: "/execution",
    label: "Bot 營運",
    role: "operations"
  },
  diagnostics_surface: {
    route: "/execution/status",
    label: "執行狀態",
    role: "diagnostics"
  },
  operator_message: "Bot 操作請在 /execution；blocked 原因、recovery 與 lifecycle 對帳請看 /execution/status。"
}
```

### 1.5 App.tsx 目標路由
```tsx
<Route path="/" element={<Dashboard />} />
<Route path="/execution" element={<ExecutionConsole />} />
<Route path="/execution/status" element={<ExecutionStatus />} />
<Route path="/lab" element={<StrategyLab />} />
<Route path="/senses" element={<Senses />} />
<Route path="/backtest" element={<Navigate to="/lab" replace />} />
```

> 補充：若要最小改動，`/execution/:runId` 不需要先做獨立頁，第一版用 `?run=` 控制右側 drawer 即可。

---

## 2) `/execution` 首屏與區塊順序

### 設計原則
`/execution` 首屏應回答三件事：
1. **今天總共賺多少 / 用了多少資金**
2. **哪些 bot 正在跑、表現如何**
3. **哪一個 bot 需要我操作**

它不應再先回答「proof chain 是否完整」。那是 `/execution/status` 的工作。

### 2.1 Desktop 首屏順序

#### A. 頁首 Hero（固定頂部）
- Title：**Bot 營運**
- Subtitle：**集中管理正在運行的策略、資金占用與盈虧表現**
- 右側 CTA：
  - `新增 Bot`
  - `查看執行狀態`
  - `重新整理`
- status chips：
  - `PAPER / LIVE_CANARY / LIVE`
  - venue
  - automation on/off
  - account snapshot freshness

#### B. Portfolio KPI Strip（4~6 張大數字卡）
順序固定：
1. **總資產**
2. **總 PnL**（realized + unrealized）
3. **今日 PnL**
4. **資金使用中**（capital in use）
5. **可用資金**
6. **運行中 Bot**

> 這一排要直接吃目前已存在資料，優先使用：
> - `account.balance.total/free`
> - `executionOverview.summary.running_runs`
> - `runtime_binding_snapshot.shared_symbol_ledger_preview.capital_in_use`
> - `runtime_binding_snapshot.shared_symbol_ledger_preview.unrealized_pnl`

#### C. 我的 Bot（主區塊，首屏主角）
從現在的「Bot 市集」改成 **我的 Bot / Bot 清單**，直接以 table 或 exchange-style row list 呈現。

**欄位順序建議：**
1. Bot / Profile
2. 狀態
3. 策略快照
4. 分配資金
5. 資金使用中
6. 未實現 PnL
7. 累積 ROI
8. PF / 預期勝率
9. 最近事件
10. 操作

**資料對應：**
- `profile_cards[].strategy_binding.roi`
- `profile_cards[].strategy_binding.profit_factor`
- `profile_cards[].strategy_binding.avg_expected_win_rate`
- `runs[].runtime_binding_snapshot.shared_symbol_ledger_preview.unrealized_pnl`
- `runs[].runtime_binding_snapshot.shared_symbol_ledger_preview.capital_in_use`
- `runs[].runtime_binding_snapshot.shared_symbol_ledger_preview.commitment_vs_budget_ratio`

**關鍵決策：**
- 不再使用「卡片像 marketplace」的語氣；改成 **列表像交易所持倉 / bot table**。
- 卡片模式只保留在 mobile。
- 每列的主 CTA 只有：`啟動` / `暫停` / `停止` / `查看詳情`。

#### D. 選中 Bot 詳情（右側 rail 或下方 drawer）
只顯示當前選中 bot 的營運資訊：
- Bot 摘要
- 資金概況（budget / in use / gap）
- PnL（realized / unrealized / total）
- 部署狀態（running / paused / halted / blocked）
- 最近 3 筆 event
- 倉位 / 掛單摘要
- `前往執行狀態` CTA

#### E. 輕量營運輔助區（首屏下半部）
兩張小卡即可：
1. **部署狀態摘要**
   - live ready / blocked
   - 主 blocker
   - active sleeves 比例
2. **帳戶與風控摘要**
   - balance free / total
   - kill switch
   - daily halt
   - failure halt

#### F. 應急手動操作（降為次要）
現在的 `快速下單 / 模式` 不該是首屏核心卡。
改成：
- 區塊名稱：**應急手動操作**
- 預設收起或放在首屏下方
- 文案明講：**僅供人工介入，不是主營運流程**

### 2.2 Mobile 順序
1. Hero
2. KPI Strip（橫向滑動）
3. 我的 Bot（卡片列表）
4. 選中 Bot Drawer
5. 部署狀態摘要
6. 帳戶與風控摘要
7. 應急手動操作

### 2.3 `/execution` 元件結構
```tsx
<ExecutionPage>
  <ExecutionHero />
  <ExecutionPortfolioStrip />
  <MyBotsTable />
  <BotRunDetailDrawer />
  <ExecutionReadinessSummaryCard />
  <ExecutionAccountHealthCard />
  <ManualInterventionPanel />
</ExecutionPage>
```

### 2.4 必改文案
- `Bot 市集` → **我的 Bot**
- `執行中的 Bot / Runs` → **運行中**
- `快速下單 / 模式` → **應急手動操作**
- `Runtime gate` → **部署狀態**
- `帳戶 / 委託` → **帳戶與成交**
- `深度診斷` → **執行狀態**
- `策略挑選` → **從 Strategy Lab 選策略**

---

## 3) `/execution/status` 的角色與內容

### 3.1 頁面角色
`/execution/status` 是 **唯一的 execution diagnostics 主頁**。

它要回答：
- 為什麼 bot 被擋？
- 是否是 market / support / guardrail / metadata / reconciliation 問題？
- operator 下一步要做什麼？

它不應承擔：
- 建立 bot
- 批量看盈虧
- 策略挑選

### 3.2 首屏內容順序

#### A. Status Hero
- Title：**執行狀態**
- Subtitle：**blocked 原因、對帳狀態與 recovery 行動中心**
- 右側 CTA：
  - `回到 Bot 營運`
  - `重新整理`

#### B. Incident Summary Bar
4 張 summary 卡：
1. **Live Readiness**
2. **主 Blocker**
3. **Snapshot Freshness**
4. **Metadata Freshness**

#### C. Operator Action Center
單獨一張高優先卡：
- `現在要做什麼`
- `operator_action`
- `restart replay required` 與否
- `最近一次檢查時間`

#### D. Runtime Truth / Deployment Gate
整合目前 Dashboard 與 Strategy Lab 反覆出現的 runtime closure 資訊：
- runtime closure state / summary
- signal / confidence / allowed layers
- deployment blocker
- execution guardrail reason
- support alignment
- active sleeves / inactive sleeves
- recent distribution pathology（若存在）

#### E. Guardrail Context
- 最近拒單
- raw → adjusted → delta → rules
- 最近 order normalization replay

#### F. Account / Symbol Scope / Snapshot
- requested symbol → normalized symbol
- account degraded / freshness
- positions count / open orders count
- account recovery hint

#### G. Reconciliation / Lifecycle
- reconciliation summary
- trade history alignment
- open-order alignment
- lifecycle audit
- recovery state
- restart replay summary

#### H. Metadata Governance
- metadata smoke freshness
- governance state
- auto refresh
- background monitor
- external monitor
- install status / ticking state
- venue metadata cards

#### I. Venue-specific Closure Lanes
- 各 venue 分 lane 顯示 baseline / path / replay
- 明確標示 OKX-only，不再把 legacy venue 混成 closure narrative

#### J. Timeline / Artifact Checklist（預設折疊）
- lifecycle timeline
- per-order artifact checklist
- proof chain 最多先顯示最近 3 條

### 3.3 頁面區塊開合策略
預設展開：
- Incident Summary
- Operator Action Center
- Runtime Truth
- Reconciliation

預設折疊：
- Metadata Governance 詳細 lane
- Artifact Checklist
- Timeline
- Normalization Replay 詳細區

### 3.4 `/execution/status` 元件結構
```tsx
<ExecutionStatusPage>
  <ExecutionStatusHero />
  <ExecutionIncidentSummary />
  <ExecutionOperatorActionCard />
  <ExecutionRuntimeTruthPanel />
  <ExecutionGuardrailContextPanel />
  <ExecutionAccountScopePanel />
  <ExecutionReconciliationPanel />
  <ExecutionMetadataGovernancePanel />
  <ExecutionVenueLanePanel />
  <ExecutionArtifactChecklistAccordion />
  <ExecutionLifecycleTimelineAccordion />
</ExecutionStatusPage>
```

---

## 4) Strategy Lab 與 Dashboard 如何降級 execution 診斷

## 4.1 Dashboard：從「execution debugging wall」降為「營運摘要入口」

### 保留
只保留 1 條 `Execution Summary Ribbon` + 1 張 `Execution CTA Card`：
- live ready / blocked
- 主 blocker
- account freshness
- metadata freshness
- CTA：`前往 Bot 營運`
- CTA：`前往執行狀態`

### 拿掉 / 移出
以下全部移去 `/execution/status`：
- execution route contract
- Metadata smoke 全量治理內容
- stale governance
- external monitor install/ticking
- Guardrail context 完整細節
- 倉位明細 / open orders 明細
- reconciliation 詳細結構
- artifact checklist
- venue lanes
- lifecycle timeline
- normalization replay

### Dashboard 內應保留的 execution 語義
只剩：
- `現在可不可以部署`
- `主要原因是什麼`
- `去哪裡操作 / 去哪裡看原因`

**建議區塊：**
```tsx
<ExecutionSummaryRibbon />
<ExecutionNextStepCard />
```

## 4.2 Strategy Lab：從「同步整包 execution runtime」降為「研究時的 live 約束提示」

### 保留
保留 1 條 compact ribbon / card：
- live blocker
- active sleeves ratio
- q15/support status
- metadata freshness
- readiness scope
- CTA：`前往 Bot 營運`
- CTA：`前往執行狀態`

### 拿掉 / 移出
以下全部不要留在 Strategy Lab 主區：
- lifecycle timeline
- artifact checklist
- venue lanes
- replay verdict 長文
- metadata governance 詳細 lane
- 對帳細表

### Strategy Lab 正確語氣
它只需要告訴研究者：
- 這個策略現在 **是否受 live blocker 約束**
- 目前 active sleeves 與 regime 是什麼
- 若要真的上線，請去 `/execution` 或 `/execution/status`

**建議區塊名稱：**
- `Live 部署同步`

而不是：
- `Execution runtime blocker sync`

---

## 5) 命名 / 文案重寫

## 5.1 導航命名
| 現況 | 建議 |
|---|---|
| 儀表板 | 市場總覽 |
| 實戰交易 | Bot 營運 |
| 策略實驗室 | Strategy Lab |
| 特徵管理 | 特徵設定 |

## 5.2 `/execution` 文案
| 現況 | 建議 |
|---|---|
| Execution Console / 實戰交易 | Bot 營運 |
| 像交易所一樣看 Bot、資金、狀態 | 集中管理 Bot、資金占用與盈虧表現 |
| Bot 市集 | 我的 Bot |
| 執行中的 Bot / Runs | 運行中 |
| Runtime gate | 部署狀態 |
| 帳戶 / 委託 | 帳戶與成交 |
| 快速下單 / 模式 | 應急手動操作 |
| 深度診斷 | 執行狀態 |
| 策略挑選 | 從 Strategy Lab 選策略 |
| 啟動 / 恢復 | 啟動 |
| Pause | 暫停 |
| Stop | 停止 |
| Resume | 恢復 |

## 5.3 `/execution/status` 文案
| 工程語氣 | 產品語氣 |
|---|---|
| execution reconciliation / recovery | 對帳與恢復 |
| guardrail context | 拒單與規則原因 |
| metadata smoke | 場館規格驗證 |
| lifecycle / replay audit | 訂單生命週期與 replay |
| venue-specific closure lanes | 各交易所對帳路徑 |
| artifact checklist / per-order closure | 每筆訂單證據清單 |
| runtime truth | 部署判定 |

## 5.4 Dashboard / Strategy Lab 文案
| 現況 | 建議 |
|---|---|
| Execution 狀態面板 | 執行摘要 |
| Execution runtime blocker sync | Live 部署同步 |
| 前往 Execution Console → | 前往 Bot 營運 → |
| 前往 Dashboard 檢查 execution runtime → | 前往執行狀態 → |

---

## 6) 視覺語言（色彩 / 層級 / 卡片 / 表格）

### 6.1 風格定位
方向不是 data-science console，而是 **暗色高級交易所 + SaaS 控制台**：
- 參考感受：Pionex 的 bot 管理、Kraken 的交易資訊層級、Coinbase 的卡片乾淨度。
- 關鍵字：**深色、克制、數字先行、操作明確、風險語義單一化**。

### 6.2 色彩系統
- `bg/base`: `#0B1020`
- `bg/surface`: `#12192B`
- `bg/elevated`: `#182235`
- `line/subtle`: `rgba(255,255,255,0.08)`
- `primary`: `#7C5CFF`
- `info`: `#2BB8FF`
- `success`: `#16C784`
- `warning`: `#F5A524`
- `danger`: `#FF5C7A`
- `text/primary`: `#F5F7FB`
- `text/secondary`: `#AAB4C5`
- `text/tertiary`: `#6E7891`

### 6.3 層級規則
#### Level 1：Hero / 主 KPI
- 大數字 28~32px
- 強對比
- 只用 4~6 張卡

#### Level 2：核心清單 / 表格
- 我的 Bot table 為第一視覺主角
- Row height 64~72px
- hover 有輕微亮面與紫色邊光

#### Level 3：摘要卡
- readiness / account / manual intervention
- 內容 2~4 行，不講長文

#### Level 4：診斷細節
- accordion / drawer / secondary page
- 不進首屏主視覺

### 6.4 卡片規則
**主卡（Primary Card）**
- radius 20~24
- padding 20~24
- 僅用於 Hero / KPI / 主 table 容器

**次卡（Secondary Card）**
- radius 16~20
- padding 16
- 用於摘要區、選中 Bot 詳情

**內嵌卡（Inset Cell）**
- radius 12~14
- padding 10~12
- 用於 table 內小指標塊、drawer mini metrics

### 6.5 Badge 規則
只保留 4 類：
- `Running / Healthy` → 綠
- `Paused / Warning` → 黃
- `Blocked / Halted / Failed` → 紅
- `Info / Neutral` → 藍

不要再出現同頁 8 種 tone function 與多種相近 badge。

### 6.6 表格規則
`/execution` 的主 UI 應從卡片群改成交易所式 table：
- Sticky header
- 第一欄 Bot 名稱固定
- 數字欄右對齊
- PnL 用綠 / 紅 + monospace semibold
- 最近事件用次要字色，不搶主數字
- 行尾 action 採 3 個 icon button + 1 個文字 CTA

### 6.7 數字語言
- PnL、ROI、PF、Expected Win Rate 都用一致格式
- 數字 > 說明文字
- 正負顏色只用 success / danger
- `—` 表示無資料，不能用 `0` 假裝有值

---

## 7) 最小可交付 MVP（可直接開發）

## 7.1 MVP 目標
先完成 **Route split + 營運優先 UI + 診斷獨立頁**，不用等新後端大改就能落地。

## 7.2 MVP 範圍

### A. 新頁面與路由
- 新增 `web/src/pages/ExecutionStatus.tsx`
- `App.tsx` 新增 `/execution/status`
- Navbar 加入 `執行狀態`

### B. `/execution` 重構
用既有資料優先完成：
- Hero + KPI Strip
- 我的 Bot table/list
- 選中 Bot drawer
- 部署狀態摘要卡
- 帳戶與風控摘要卡
- 應急手動操作區降到下半部

### C. `/execution/status` 首版
直接吃現有 `/api/status`，先把現在 Dashboard 內以下模組搬過去：
- Runtime truth
- Guardrail context
- Metadata smoke
- Execution reconciliation
- Lifecycle timeline
- Venue lanes
- Artifact checklist

### D. Dashboard 降級
改成：
- `ExecutionSummaryRibbon`
- `ExecutionNextStepCard`
- 兩個 CTA（Bot 營運 / 執行狀態）

### E. Strategy Lab 降級
改成：
- `LiveDeploymentRibbon`
- 保留 blocker / active sleeves / support status / metadata freshness / CTA
- 移除長篇 lifecycle / metadata / venue lane 區塊

## 7.3 首批前端元件
```tsx
web/src/components/execution/
  ExecutionHero.tsx
  ExecutionPortfolioStrip.tsx
  MyBotsTable.tsx
  BotRunDetailDrawer.tsx
  ExecutionReadinessSummaryCard.tsx
  ExecutionAccountHealthCard.tsx
  ManualInterventionPanel.tsx
  ExecutionSummaryRibbon.tsx
  LiveDeploymentRibbon.tsx
  ExecutionIncidentSummary.tsx
  ExecutionOperatorActionCard.tsx
```

## 7.4 API 使用策略（第一版）
**不用等新 API 才能先做 UI**，優先利用現有：
- `/api/status`
- `/api/execution/overview`
- `/api/execution/runs`

### `/execution` 第一版資料優先順序
1. `execution/overview` → bot 列表 / strategy binding / allocation
2. `execution/runs` → 狀態 / 事件 / action contract
3. `status` → account / guardrail / readiness summary

### 首批一定要前景化的欄位
- `strategy_binding.roi`
- `strategy_binding.profit_factor`
- `strategy_binding.avg_expected_win_rate`
- `runtime_binding_snapshot.shared_symbol_ledger_preview.unrealized_pnl`
- `runtime_binding_snapshot.shared_symbol_ledger_preview.capital_in_use`
- `runtime_binding_snapshot.shared_symbol_ledger_preview.total_known_commitment`
- `runtime_binding_snapshot.shared_symbol_ledger_preview.commitment_vs_budget_ratio`

## 7.5 這一版先不做
- marketplace / bot discovery
- 跨 bot 自動再平衡
- 獨立 `/execution/:runId` 頁
- 高級績效報表
- 自訂 table column manager
- 多層複雜 alert center

## 7.6 驗收標準
1. 使用者進 `/execution` 第一眼先看到 **PnL / 資金 / 我的 Bot**，不是 marketplace。
2. 使用者可以一鍵從 `/execution` 進 `/execution/status`。
3. Dashboard 與 Strategy Lab 不再承載 execution 全量診斷內容。
4. `/execution/status` 可以完整承接 blocked / recovery / metadata / reconciliation 問題。
5. 文案從工程語氣改成產品語氣，且以繁中為主。

---

## 8) 實作順序建議

### Phase 1 — Route 與資訊架構重排
- 新增 `/execution/status`
- 改 nav label
- 建立 Dashboard / Strategy Lab 摘要 ribbon

### Phase 2 — `/execution` 首屏重構
- 拆掉「Bot 市集」心智
- 改成我的 Bot table
- 前景化 ROI / PF / expected win / unrealized pnl / capital in use

### Phase 3 — `/execution/status` 搬遷
- 把 Dashboard diagnostics 區塊移入新頁
- 以 accordion + table 重做層級

### Phase 4 — 視覺 polish
- 統一 badge tone
- 統一卡片層級
- 統一數字格式與表格密度

---

## 9) 需要同步注意的工程影響
- `tests/test_frontend_decision_contract.py` 目前強綁大量現有字串與區塊名稱；若依本藍圖實作，**測試需要一起改**。
- 現有 `execution_surface_contract` 雖已具備 operations / diagnostics 雛形，但文案與 route 仍偏舊語義，落地時要一起調整。
- 第一版不必先追加大量新 API，先靠現有 `status + overview + runs` 就能把產品層級做對。
