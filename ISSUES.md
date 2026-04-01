# Poly-Trader Issues 追蹤

---

## ✅ 已修復

| ID | 問題 | 修復 | 驗證日期 |
|----|------|------|----------|
| #H01 | 回測使用 random 而非真實數據 | 讀 DB 五感數據 | 04-01 |
| #H02 | collector 持續寫入新數據 | 使用 v3/v4 數據收集 | 04-01 |
| #H03 | 前端 Vite 編譯/資料同步問題 | 修正環境變量 + proxy | 04-01 |
| UX6 | AdviceCard `undefined length` | 修改 Props 確保一性 | 04-01 |
| UX7 | 回測需要顯示 | BacktestSummary Null Safety | 04-01 |
| UX8 | 五感映射圖時間軸不一致 | 新增 MergedPoint 修復 | 04-01 |

---

## 🟡 觀察中

| ID | 問題 | 當前狀態 |
|----|------|----------|
| #M06 | 模型準確率 | 樣本數已大幅提升 (2107 paired) 可重新訓練 |
| ~#H20~ | ~~Ear/Nose 共線~~ | **已確認獨立 (r=-0.064)，251 樣本時的 r=0.998 是取樣偏差** |
| #M07 | 五感映射缺少統計意義 | Body IC 最高，Ear/Tongue 也顯著 |

---

## 🔴 高優先級

| ID | 問題 | 解法 | 狀態 |
|----|------|------|------|
| Eye IC | Eye IC = -0.01 (不再顯著) | 需要調查回填後的 Eye 計差異 | 🔴 新增 |

---

## 🟡 下次迭代

- **[Action 1]**: 用 2107 樣本重新訓練模型 — 過擬問題應大幅改善
- **[Action 2]**: Eye 反向特徵不再必要 — 回填數據中 Eye IC = -0.01 近乎 0
- **[Action 3]**: Body 現為最強信號 (IC=-0.079, p<0.001) — 增加權重
- **[Action 4]**: 更新 senses.py 權重: Body > Ear > Tongue > Nose > Eye

---

### 2026-04-01 修複記錄

| ID | 問題 | 修復 | 驗證日期 |
|----|------|------|----------|
| #H21 | api.py 匯入不存在的 WsManager → Windows subprocess spawn ImportError → 伺服器崩潰 | 移除 WsManager import，WS 路由統一由 ws.py 管理 | 04-01 |
| #H22 | 五感走勢圖/回測：特徵值 -1~1 但圖表和回測用 0~1 閾值 → 顯示錯誤+幾乎無交易 | SenseChart.tsx 加 normalizeSense() 映射到 0~1；api.py 回測加正規化+IC 權重 | 04-01 |
| Eye IC | Eye IC = -0.01 (不再顯著) | 回填後 Eye IC 近乎 0，反向特徵不再必要 | 04-01 |
| #M06 | 模型準確率 | 樣本數已大幅提升 (2160 paired) 可重新訓練 | 04-01 |

### 待擴充感官
| ID | 感官 | 數據源 | 說明 | 狀態 |
|----|------|--------|------|------|
| #NEW-1 | Sixth Sense (Mind) | CBOE Volatility Index (VIX) / Crypto Volatility | 市場波動感知 | 規劃中 |
| #NEW-2 | Intuition | BTC Dominance + Altcoin Index | 資金在 BTC vs 山寨的流向 | 規劃中 |
| #NEW-3 | Pulse | Funding Rate OI Divergence | 資金費率與持倉量的背離 | 規劃中 |
| #NEW-4 | Instinct | Fear & Greed Rate of Change | FNG 的變化速度（非絕對值） | 規劃中 |
| #NEW-5 | Aura | Liquidation Heatmap | 清算密集區 → 價格磁鐵效應 | 規劃中 |

**最後更新**: 2026-04-01 11:59 GMT+8
