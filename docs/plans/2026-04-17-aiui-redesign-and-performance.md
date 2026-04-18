# Poly-Trader AIUI 重整與效能優化評估

_最後更新：2026-04-17 15:18 CST_

## 一句話結論
現在的問題不是功能不夠，而是 **資訊架構混雜、頁面責任過重、更新鏈太長**。正確方向是把 UI 從「工程總控台」重構成 **產品化多工作區**，並把前端載入/輪詢/圖表依賴做分層拆分。

---

## 現況診斷

### 1. 頁面責任過重
目前主要頁面：
- `Dashboard.tsx`：約 2000 行
- `StrategyLab.tsx`：約 2777 行
- `FeatureChart.tsx`：約 1078 行
- `CandlestickChart.tsx`：約 1073 行

這代表：
- Dashboard 同時承擔：live 狀態、execution diagnostics、metadata governance、chart、4H 讀盤
- Strategy Lab 同時承擔：策略編輯、回測工作區、排行榜、模型排行榜、runtime blocker sync、metadata smoke、技術摘要

### 2. 心智模型混在一起
目前混在同一層的其實是 4 種不同工作：
1. **研究 / 實驗**
2. **營運 / 實戰**
3. **診斷 / 治理 / proof chain**
4. **市場讀盤 / 觀察**

這會讓使用者感覺「太多、太亂、太雜」。

### 3. 更新速度慢的主因
目前已確認：
- 初始打包曾是單包約 `966 KB` JS
- 現在已先做第一步 code-splitting，build 後變成：
  - `StrategyLab` chunk ~ `79.9 KB`
  - `Dashboard` chunk ~ `101.6 KB`
  - `react-vendor` ~ `164 KB`
  - `chart-vendor` ~ `568.7 KB`
- 前端輪詢仍存在多個 polling endpoint：
  - `/api/senses` 30s
  - `/api/features/coverage` 60s
  - `/api/predict/confidence` 60s
  - `/api/model/stats` 60s
  - `/api/status` 60s
- `useApi.ts` 目前沒有 in-flight request dedupe，也沒有 page-level aggregated fetch

---

## 建議的 AIUI / 產品化資訊架構

## A. 首層導航只保留 4 個主工作區
### 1. 市場總覽（Market Overview）
用途：
- 今天市場狀態
- 4H regime
- 關鍵感測摘要
- 主要 blocker / readiness

不放：
- proof chain 大量細節
- 回測編輯器
- 多 bot 營運

### 2. 策略實驗室（Strategy Lab）
用途：
- 組策略
- 選 sleeve
- 回測
- leaderboard
- 模型比較

不放：
- execution governance 深層診斷
- metadata smoke 長篇治理資訊
- operator 對帳細節

### 3. 實戰交易（Execution Console）
用途：
- 選策略 / sleeve
- 選 venue / mode
- 配資金
- 開 bot
- 看 PnL / 狀態 / stop reason

這會是未來產品主頁之一。

### 4. 系統診斷（Diagnostics / Control Room）
用途：
- execution reconciliation
- guardrail context
- metadata smoke
- proof chain
- external monitor / stale governance

這些應該從 Dashboard 拆出去。

---

## B. 每頁只保留一種主要心智
### Dashboard / 市場總覽
核心問題：
- 「今天市場怎樣？」
- 「現在能不能部署？」
- 「主要 blocker 是什麼？」

### Strategy Lab
核心問題：
- 「哪個策略 / sleeve 最值得研究？」
- 「參數改了回測怎麼變？」

### Execution Console
核心問題：
- 「我現在開了哪些 bot？」
- 「各自賺多少虧多少？」
- 「要不要停？」

### Diagnostics
核心問題：
- 「這個執行/對帳/closure 為什麼被擋？」

---

## C. Strategy Lab 應怎麼重整
### 目前問題
Strategy Lab 現在像是 5 個產品疊在一頁：
- 策略編輯器
- runtime blocker sync
- 回測 workspace
- leaderboard
- 模型 leaderboard
- snapshot / 技術摘要

### 建議新布局
#### 上層：雙層頁籤
- `Workspace`
- `Leaderboard`
- `Models`
- `Diagnostics`（輕量版，只保留必要 blocker sync）

#### 左側：策略組裝區
只保留：
- strategy name
- sleeve modules
- 關鍵參數
- backtest range
- initial capital
- run/save

#### 中央：主工作區
只保留：
- 圖表
- KPI cards
- trade list
- regime / sleeve summary

#### 右側或次層抽屜：補充資訊
- benchmark
- 技術摘要
- 排行榜快照

### 關鍵 UI 原則
- **排行榜與工作區分頁，不要永遠同屏**
- **模型排行榜也獨立成 tab，不要擠在 Strategy 主 workspace 下方**
- **metadata smoke / lifecycle proof chain 不要留在實驗頁主路徑**

---

## D. Dashboard 應怎麼重整
### 現在最大的問題
Dashboard 塞了太多 operator 級區塊，已經不像 dashboard，而像 debugging wall。

### 建議新布局
#### 第一屏：只保留 4 卡
1. 市場 regime / 4H bias
2. live readiness / blocker
3. execution mode / venue / account summary
4. 今日信號摘要

#### 第二屏：市場與策略摘要
- 價格圖
- 感測雷達
- 近期 distribution pathology（精簡版）

#### 第三屏：深度區塊移出或折疊
以下都應移去 Diagnostics：
- execution route contract
- metadata smoke
- stale governance
- full artifact checklist
- venue lanes
- lifecycle timeline
- normalization replay

Dashboard 應該只顯示 **摘要與導引**，不是全量細節。

---

## 建議視覺方向（AIUI）
### 方向
最適合 Poly-Trader 的不是花俏 marketing 風，而是：
- **Linear 式資訊層級 + Kraken 式交易狀態卡 + Notion 式次要說明區**

### 原則
- 主畫面深色、低雜訊
- 一級卡片少而重
- 細節資訊放抽屜 / drilldown
- 同頁不要同時出現 5 種顏色語義與 10 個 badge 系統
- badge 分成固定 3 類：
  - 狀態（running / blocked / degraded）
  - 類型（sleeve / regime / venue）
  - 風險（low / medium / high）

---

## 更新速度慢：可行優化清單

## 已做的 quick win
### 1. Route-level code splitting
已完成：
- `App.tsx` 改為 `React.lazy()` 載入 Dashboard / Senses / StrategyLab
- 加入 `Suspense` fallback

### 2. Vite manualChunks
已完成：
- `react-vendor`
- `chart-vendor`

效果：
- 從單一巨大 JS 包，拆成多 chunk
- StrategyLab / Dashboard 不再一進站全部打進主包

---

## 下一步建議的效能優化
### P0. 把 chart-vendor 再拆細
現在最大塊仍是：
- `chart-vendor ~568.7 KB`

原因：
- `recharts`
- `lightweight-charts`
同時進同一 vendor chunk

建議：
- `recharts-vendor`
- `lightweight-vendor`
分開
- 甚至讓 `CandlestickChart` 再用 dynamic import

### P0. 降低頁面同時 polling 數量
目前一頁同時輪詢多個 endpoint。
建議：
- 用 `GET /api/dashboard/summary`
- 用 `GET /api/strategy-lab/summary`
聚合資料

好處：
- 減少多請求往返
- 減少多次 state 更新造成重渲染

### P1. `useApi` 加 in-flight dedupe
目前同 endpoint 若多處 refresh，可能重複 fetch。
建議：
- 用 global in-flight map
- 相同 endpoint 同時只發一次

### P1. 把巨型頁拆成 container + section component
目前大頁重渲染成本高。
建議：
- `StrategyLab.tsx` 拆成：
  - `StrategyEditorPanel`
  - `StrategyWorkspacePanel`
  - `StrategyLeaderboardPanel`
  - `ModelLeaderboardPanel`
  - `StrategyLabDiagnosticsPanel`
- `Dashboard.tsx` 拆成：
  - `MarketOverviewPanel`
  - `ReadinessPanel`
  - `AccountSummaryPanel`
  - `DiagnosticsPreviewPanel`

### P1. 對大圖表資料做 memo / input normalization
特別是：
- `FeatureChart.tsx`
- `CandlestickChart.tsx`

應避免每次上層小 state 變動就重算整份 chart data。

### P2. 對長作業結果做 server-side snapshot aggregation
不要每次前端刷新都重算大量衍生欄位，尤其是 leaderboard / strategy summaries。

---

## 建議的產品化實作順序
1. **先重整資訊架構**：把 Dashboard / Strategy Lab / Diagnostics 的責任拆乾淨
2. **再做 regime-aware sleeve routing**：因為 UI 分頁清楚後，routing 更容易表達
3. **再補 Execution Console**：多 bot + per-sleeve + per-regime
4. **最後做聚合 API 與 polling 最佳化**

---

## 最重要的設計原則
### 不要再把所有資訊都放在同一頁
要把 Poly-Trader 從「工程功能全集頁」變成「多工作區產品」。

### 不要再用更多 badge / 卡片解決資訊過多
資訊太多時，應該做的是：
- 分頁
- 抽屜
- drilldown
- summary first

### 不要靠降低 threshold 補交易頻率
正解仍然是：
- 多 sleeve
- regime routing
- uncertainty gate
- turnover allocator

這些要在新的 UI 架構下表達，而不是堆回舊頁面。