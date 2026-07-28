# Poly-Trader 產品重設：研究到安全實戰

日期：2026-07-11

## 1. 結論

本次問題不是單一畫面不好看，而是產品資訊架構與執行契約斷裂：

1. **所有內部狀態都直接暴露給使用者**：Dashboard、Strategy Lab、Execution Console 同時呈現大量 gate、artifact、研究說明與重複狀態，卻沒有一個清楚的主要任務。
2. **回測策略沒有明確的執行身分**：原本可以回測、儲存，也可以建立 execution run，但「使用者剛選的策略」沒有被精確凍結並傳入 paper/shadow run；profile 預設策略可能取代使用者選擇。
3. **Live gate 被誤當成整個產品的停止鍵**：exact bucket 漂移後可回到 `0/50`，UI 只顯示 blocked / 等待，沒有安全替代 lane、可靠 ETA、重新評估條件或可執行 CTA。
4. **能力存在但分散**：後端已有 paper/shadow、worker、24h outcome、venue dry-run、reduce-only 與 fail-closed guardrail，但使用者必須跨頁理解內部架構，才知道下一步能做什麼。

因此本輪把產品改成一條清楚主線：

> **選策略 → 回測 → 凍結 exact strategy/model bundle → Paper/Shadow worker → 24h outcome → 所有硬門檻通過後才進 bounded canary**

Live 安全沒有被放寬；被放寬的是「在 Live 尚未通過時，使用者仍可做安全而有產出的工作」。

---

## 2. 稽核證據

### 2.1 介面密度

- 前端等待／阻塞／部署／paper／shadow 等營運詞彙曾分散出現至少 271 次。
- 主要頁面 JSX 結構元素曾超過 1,000 個匹配。
- `StrategyLab.tsx` 超過 4,000 行，原先在同一工作區同時顯示：策略模組說明、模型選擇、資金模式、完整決策品質、Canary gate、資料同步三層明細、圖表、排行榜與研究解讀。
- 原主導覽同時提供儀表板、Bot 營運、執行狀態、特徵管理、策略實驗室；所有項目視覺權重相近，沒有使用者任務層級。

### 2.2 回測到執行的斷點

原有能力：

- 儲存與載入策略。
- 建立 execution profile run。
- paper/shadow worker 與 outcome reconciliation。
- strategy bundle freeze / parity guard。

原有斷點：

- run start 依賴 profile 的隱含推薦策略，不保證是使用者剛回測／選擇的策略。
- Strategy Lab 沒有直接、可驗證的「把此策略送入安全演練」操作。
- 同 profile 已有不同策略 run 時，可能造成使用者以為已切換，實際沿用舊 run 的認知風險。

### 2.3 永久等待

目前 runtime truth 可出現：

- exact support `0/50`。
- 沒有正向增量時，完成時間不可可靠估算。
- bucket／semantic identity 改變後，舊支持不可冒充當前 live support。

正確處理不是降低 50 筆門檻，也不是把 proxy rows 當 live 證據，而是：

- Live buy/add 持續 fail-closed。
- 自動選擇安全替代 lane。
- 顯示目前進度、ETA 狀態、下一次對帳、主動修復方向。
- Paper/Shadow、worker、24h outcome、venue dry-run、drift/rebaseline 可繼續產生證據。

---

## 3. 新資訊架構

### 主導覽

只保留三個使用者目標：

1. **總覽**：現在能做什麼、唯一阻塞點、唯一主要 CTA。
2. **策略**：選擇／回測策略，並直接啟動安全演練。
3. **營運**：查看與控制 active run、worker、outcome。

完整儀表板、執行診斷與特徵管理移到「進階」。功能沒有刪除，但不再搶主流程注意力。

### 總覽（Command Center）

首屏只回答：

- 現在是否安全？
- 現在應做什麼？
- 執行後會產生什麼？
- Live 為何未放行？

主畫面提供：

- 單一主要 CTA：啟動／推進最佳候選 Paper/Shadow。
- 三階段進度：回測候選 → Paper/Shadow → Bounded Canary。
- resolved / pending outcome 數量與下次可對帳時間。
- exact support 的目前值、最低值與差距。
- 沒有可靠 ETA 時，明確顯示已自動切換替代路線，而不是「請等待」。

### Strategy Lab

預設只顯示必要操作：

- 策略名稱。
- 策略類型／模型。
- 目前策略組合。
- 執行回測。
- 啟動目前策略 Paper/Shadow。
- ROI、最大回撤、PF、交易數。

策略模組說明、完整模型／決策品質／Canary 指標、Raw／Features／Labels 明細改成 progressive disclosure，預設收合。

---

## 4. 回測策略到安全實戰鏈路

新增 API：

```http
POST /api/strategies/{name}/paper-shadow
```

行為：

1. 只接受存在且非 system-generated 的已儲存策略。
2. 解析 exact strategy name、model、primary sleeve、definition 與 metadata。
3. 建立 exact `strategy_binding`，凍結 strategy/model bundle。
4. 強制使用 `paper_shadow` mode。
5. 建立或檢查 execution run。
6. 立即執行一次 paper/shadow worker poll。
7. 建立／更新 24h outcome reconciliation。
8. 回傳明確安全欄位：
   - `order_submission_enabled=false`
   - `risk_on_order_enabled=false`
   - `live_order_submitted=false`

### 衝突處理

- 相同 profile、相同策略的 running run：保持冪等，回傳既有 run。
- 相同 profile、不同策略的 running／paused run：回傳 `strategy_run_conflict`，不靜默沿用舊策略。
- 找不到策略或策略為 system-generated：fail-closed。
- `force_paper_shadow` 只可跳過原本阻塞 paper/shadow 的 profile start gate，不能影響 Live gate。

---

## 5. 主動解阻契約

`/api/execution/overview` 新增 `user_action_state`：

```text
state
progress_current
progress_target
freshness
blocking_reason
next_action
cta
deadline
alternative_lane
operator_fix
safety
```

核心語意：

- `deadline.status` 可明確表示「無正增量、無可靠 ETA」，不虛構完成日期。
- `alternative_lane.required=true` 時，產品不再只呈現 blocked；自動轉向 paper/shadow、venue dry-run、24h outcome 或 drift/rebaseline 評估。
- `operator_fix` 說明何時必須重新設計 map/signal 或重建證據窗口。
- `safety` 在非 bounded-canary 狀態固定維持 no-order / no-risk-on。

此契約讓 Dashboard、Strategy Lab、Execution Console 不必各自推導一套互相矛盾的說明。

---

## 6. 安全不變量

以下規則沒有被取消：

- Live buy/add 必須等所有 hard gates 通過。
- Exact current-bucket support 不可由 broad／legacy／proxy rows 取代。
- Paper/Shadow 不可標成 live clearance。
- Bundle parity 失敗時 worker fail-closed。
- Live canary 必須有 explicit symbol allowlist、symbol cap、venue lifecycle proof、kill switch 與 adapter guardrail。
- 即使 canary-ready，也只能先做 bounded minimum canary，不是 full deploy。

---

## 7. 主要修改檔案

- `web/src/pages/CommandCenter.tsx`
- `web/src/App.tsx`
- `web/src/pages/StrategyLab.tsx`
- `execution/control_plane.py`
- `execution/console_overview.py`
- `server/routes/api.py`
- `tests/test_execution_run_control.py`
- `tests/test_execution_console_overview.py`
- `tests/test_product_redesign_contract.py`

---

## 8. 驗證結果

已完成：

- 相關後端與產品契約測試：20 passed。
- 前端 TypeScript + Vite production build：成功。
- `git diff --check`：成功。
- Browser QA：總覽成功顯示單一 CTA、三階段流程、`0/50` 阻塞、替代 lane 與工作入口。
- Browser action smoke：在既有 shadow run 上執行下一次安全 worker tick，畫面回報本輪處理 1 次；沒有 JavaScript error。
- Strategy Lab Browser QA：Paper/Shadow CTA 存在；在未選已儲存策略時保持 disabled。

---

## 9. 尚存風險與後續

1. `StrategyLab.tsx` 內部仍然過大；本輪已降低預設可見密度，但下一輪應拆成 Editor、Backtest Result、Leaderboard、Activation 四個獨立元件。
2. 圖表 vendor chunk 仍超過 500 kB；不阻塞正確性，但可再做按頁／按圖 lazy loading。
3. Exact support `0/50` 仍是真實 Live blocker；本輪沒有降低門檻或偽造證據。
4. 場館 credentials／ack／fill／reconciliation proof 未完成前，bounded live canary 仍應維持關閉。
5. 主動替代 lane 已產品化；若 heartbeat 連續無正增量，工程流程仍需實際執行 map/signal redesign、fresh-window replay 或 drift-aware rebaseline，而不是只更新文字。
