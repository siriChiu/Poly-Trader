# Poly-Trader Live Trading Productization Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 把 Poly-Trader 從研究 / 回測平台推進到可受控上線的多交易所 execution foundation。

**Architecture:** 用 `ExecutionService + ExchangeAdapter + AccountSyncService` 抽出實盤層，讓 Binance 成為第一個 production venue、OKX 成為第二個 venue，同時保留 paper / live_canary / live 模式切換。

**Tech Stack:** Python, FastAPI, SQLAlchemy, ccxt, React, SQLite。

---

## 當前已完成的第一段
- 建立多交易所 adapter 骨架：Binance / OKX
- 建立 `ExecutionService` 與 `AccountSyncService`
- 將 `/api/trade` 與 heartbeat runtime 接到新的 execution layer
- 將 config 擴充為 `execution.mode / execution.venue / execution.venues.*`

## 下一段建議
1. 加入最小 notional / precision 實際檢查與拒單理由
2. 加入日內損失上限、kill switch、連續錯誤停機
3. 建立 `GET /api/execution/status` 與前端 venue/account 卡片
4. 做 Binance canary live 驗證，再接 OKX live canary
