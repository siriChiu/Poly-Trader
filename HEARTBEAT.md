# HEARTBEAT.md — Poly-Trader 心跳任務（5 分鐘循環）

> 角色定義見 [AI_AGENT_ROLE.md](AI_AGENT_ROLE.md)，系統架構見 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 🧬 核心使命：負熵驅動

Poly-Trader 不是靜態系統，而是持續引入外部能量、排出系統混亂、讓預測能力與日俱增的活系統。

**負熵三律：**
1. 封閉系統必然衰亡 → 必須定期引入新數據源、新視角、新方法
2. 每個感官都必須被實證淘汰或升級 → IC（訊息係數）是唯一裁判
3. 所有決策都要能追溯「它做了什麼功」→ 只問結果，不問意圖

**終極目標：做空(SELL/SHORT) 勝率 ≧ 90%**
（定義：`sell_win_rate = profitable_sells / total_sells`，label_sell_win=1 表示價格下跌=做空獲利）

---

## 📊 感官系統：Sensory ETF（20 個感官）

所有感官像 ETF 一樣由 **時間加權 IC (TW-IC)** 動態賦權，連續 D 級自動淘汰。

### Tier 分級標準
| 等級 | \|TW-IC\| | 權重 | 含義 |
|------|-----------|------|------|
| A+   | ≥ 0.15    | 3x   | 高價值核心信號 |
| A    | ≥ 0.10    | 2x   | 強信號 |
| B    | ≥ 0.05    | 1x   | 基線信號 (閾值) |
| C    | ≥ 0.02    | 0.5x | 邊緣信號 |
| D    | < 0.02    | 0x   | 淘汰/靜音 |

淘汰規則：連續 3 次心跳 D 級 → `disabled=True`

### 現有 20 個感官

| #  | 名稱 | 數據源 | 免費 | IC 預估 | SHORT 意義 |
|----|------|--------|------|---------|------------|
| 1  | 👁️ Eye (視覺) | return_24h / vol_72h | ✅ | 0.02-0.04 | 24h 回報/72h 波動 = 趨勢強度 |
| 2  | 👂 Ear (聽覺) | 24h 價格動量 | ✅ | -0.05 | 過熱反轉信號 |
| 3  | 👃 Nose (嗅覺) | RSI(14) | ✅ | -0.05 | 超買信號 → 看跌 |
| 4  | 👅 Tongue (味覺) | 20h 均值回歸偏移 | ✅ | -0.06 | 偏離均線 → 回落概率 |
| 5  | 💪 Body (觸覺) | 48h 波動率 z-score | ✅ | 0.05-0.06 | 高波動 = 延續信號 |
| 6  | 💓 Pulse (脈動) | 12h 成交量 z-score | ✅ | -0.08 | 量增反轉 |
| 7  | 🌀 Aura (磁場) | 價格 vs SMA144 偏離 | ✅ | -0.04 | 極端偏離 → 反轉 |
| 8  | 🧠 Mind (認知) | 144h 價格回報 | ✅ | -0.07 | 長期動量反轉 |
| 9  | 📈 VIX (恐慌指數) | Yahoo Finance | ✅ | -0.08 | VIX 高 = 市場恐懼 = SHORT 勝率高 |
| 10 | 💵 DXY (美元指數) | Yahoo Finance | ✅ | -0.11 | 美元強 = 風險資產弱 = SHORT |
| 11 | 📊 RSI-14 | 技術指標 | ✅ | 0.10 | 超買確認 |
| 12 | 📊 MACD-Hist | 技術指標 | ✅ | 0.15 | 動量反轉 |
| 13 | 📊 ATR% | 技術指標 | ✅ | 0.08 | 波動率通道 |
| 14 | 📊 VWAP Dev | 技術指標 | ✅ | 0.10 | 公平價值偏離 |
| 15 | 📊 BB %B | 技術指標 | ✅ | 0.06 | 波動率極端 |
| 16 | 🦞 Claw (清算) | CoinGlass API | 需 key | 0.10-0.20 | 多頭清算 = SHORT 勝率跳升 |
| 17 | 🦷 Fang (期權 PCR) | Deribit API | ✅ | 0.08-0.15 | PCR 高 = 機構買保護 |
| 18 | 🐟 Fin (ETF 流向) | CoinGlass ETF | 需 key | 0.05-0.12 | 淨流出 = SHORT 信號 |
| 19 | 🕸️ Web (巨鯨) | Binance 大額交易 | ✅ | 0.05-0.10 | 大額賣壓 = 出貨前兆 |
| 20 | 🐚 Scales (穩定幣 SSR) | CoinGecko | ✅ | 0.05-0.12 | SSR 高 = 買盤枯竭 |

> **注意**: Nest (Polymarket) 和 NQ (納斯達克) 也已導入代碼，但需要數據累積後才能計算 IC。

### Cross-features (交叉特徵)
- `feat_vix_x_eye`, `feat_vix_x_pulse`, `feat_vix_x_mind` — 恐慌與技術面的交互
- `feat_mind_x_pulse`, `feat_eye_x_ear`, `feat_nose_x_aura` — 感官交互
- `feat_eye_x_body`, `feat_ear_x_nose`, `feat_mind_x_aura` — 多維度確認
- `feat_mean_rev_proxy` = mind - aura — 均值回歸代理
- `feat_claw_x_pulse` — 清算 x 成交量 = 強制出清確認
- `feat_fang_x_vix` — 期權恐懼 x VIX = 宏觀恐懼確認
- `feat_fin_x_claw` — ETF 流出 x 清算 = 結構性賣壓
- `feat_web_x_fang` — 巨鯨賣壓 x 期權 PCR = 機構出貨確認
- `feat_nq_x_vix` — 納斯達克 x VIX = 科技股恐慌確認

---

## ⚡ 平行執行器

**`scripts/hb_parallel_runner.py`** — 多進程並行執行所有耗時腳本

```bash
# 完整心跳 (並行, ~3-6 分鐘)
cd /home/kazuha/Poly-Trader
source venv/bin/activate
python scripts/hb_parallel_runner.py --hb N

# 快速模式 (counts + global IC + regime IC, ~30s)
python scripts/hb_parallel_runner.py --hb N --fast

# 跳過重型步驟
python scripts/hb_parallel_runner.py --hb N --no-train --no-dw
```

並行執行 4 個任務:
1. 🔍 `full_ic.py` — 全域 IC 分析
2. 🏛️ `regime_aware_ic.py` — 分區間 IC
3. 📏 `dynamic_window_train.py` — 動態窗口掃描
4. 🔨 `model/train.py` — XGBoost 模型訓練
5. 🧪 `tests/comprehensive_test.py` — 完整測試套件

**預期加速**: 串行 ~1200-1800s → 並行 ~180-300s (3-5x)

---

## 🔄 心跳完整流程

每次心跳嚴格執行 **Step 0 〜 Step 8**，不可跳過。

### Step 0：閱讀 context（每次必讀）
- `AI_AGENT_ROLE.md` — 當前角色、紀律、邊界
- `ISSUES.md` — P0 / P1 / P2 問題清單
- `poly-trader-heartbeat` skill — 完整技術文檔

### Step 1：快速數據統計
- 運行 `python scripts/dev_heartbeat.py` 或平行 runner Step 0
- 記錄 Raw / Features / Labels 數量
- 檢查數據增長（如果 raw/features/labels 沒增加 → 資料收集有問題）

### Step 2：IC 分析（並行執行）
```bash
python scripts/hb_parallel_runner.py --hb N
```
- 全域 IC：|IC| < 0.05 → 感官需要替換
- Regime-aware IC：Bear / Bull / Chop 分開看
- Dynamic Window：N=100, 500, 1000, 2000, 5000 掃描
- Check: sell_win_rate — 如果 < 0.50 → EMERGENCY

### Step 3：模型訓練
- XGBoost global + per-regime models
- 記錄 Train / CV accuracy、gap
- Gap > 20pp → 過擬合，需要更正則化
- CV < 52% → 信號瓶頸，需要新數據源

### Step 4：Sensory ETF 更新
```python
# IC 計算完後更新 ETF
from feature_engine.sensory_etf import get_etf
etf = get_etf()
etf.update_ic("feat_claw", ic_v...)
etf.save(hb=N)
print(etf.table(hb=N))
```
- 檢查哪些感官升級/降級/被淘汰
- 確保新感官在 probation 狀態下收集足夠數據

### Step 5：前端同步
- WebSocket 推送所有 20 個感官到 `server/routes/ws.py`
- Web 雷達圖更新 `SENSE_INFO` 包含新增感官
- API end points 返回完整 20 維數據

### Step 6：回測模型驗證
- 運行 `backtesting/engine.py` 或 `backtesting/engine_v2_backup.py`
- 檢查 sell_win_rate, profit factor, Sharpe
- 回測 vs 在線指標一致性檢查

### Step 7：ISSUES 更新
- 全寫 ISSUES.md（不是 append，是 overwrite）
- P0/P1/P2 優先級排序
- 包含：系統健康表、IC 表、測試狀態、下一步行動

### Step 8：Commit + 報告
```bash
cd /home/kazuha/Poly-Trader
git add -A && git commit -m "心跳 #N: 摘要"
```
更新 HEARTBEAT.md 底部的心跳歷史記錄。

---

## 🌐 前端畫面同步規範

### API endpoints
| 端點 | 用途 | 數據 |
|------|------|------|
| `/api/senses` | 最新感官分數 | 20 個感官的 score (0-100) |
| `/api/market` | 市場快照 | BTC, FNG, LSR, OI, VIX, DXY, NQ |
| `/api/ic` | IC 分析結果 | 全域+各區間 IC, 分級 |
| `/api/prediction` | 模型預測 | confidence, regime, model used |
| `/api/backtest` | 回測結果 | sell_win_rate, PnL, Sharpe |
| `/api/etf` | Sensory ETF 狀態 | 20 感官的 tier, weight, disabled |
| `ws://.../ws` | 實時推送 | 所有感官 + 預測結果 |

### 雷達圖更新 (RadarChart.tsx)
- `SENSE_KEYS` 從 8 個擴展到 20 個
- `SENSE_INFO` 包含 emoji, label, color, source, IC, tier
- 使用 Sensory ETF 的 weight 來影響點的大小
- 禁用 (disabled) 感官用灰色顯示

### 圖表需求
1. **價格 × 多感官 overlay** — 主圖 BTC 價格, 副圖 20 感官 score
2. **IC 條形圖** — 橫條顯示 20 感官的 IC, 顏色按 tier (A+=綠, A=黃, D=紅)
3. **勝率熱圖** — regime × time window
4. **ETF 權重圓環** — circle chart 顯示各感官的 ETF weight
5. **回測曲線** — equity curve + drawdown

---

## 🧪 回測模型整合

### 回測引擎
- `backtesting/engine.py` — 主回測引擎 (SHORT 策略)
- `backtesting/metrics.py` — 勝率, 利潤因子, 夏普, 最大回撤
- `backtesting/walkforward.py` — 滾動回測驗證

### 回測關鍵指標
| 指標 | 目標 | 當前 |
|------|------|------|
| sell_win_rate | ≥ 90% | ~50% |
| profit_factor | > 1.5 | 未知 |
| sharpe_ratio | > 1.0 | 未知 |
| max_drawdown | < 20% | 未知 |
| train_cv_gap | < 10pp | ~20pp |

### 回測必須驗證
1. 賣出勝率 ≠ 模型準確率 — 只看 profitable SHORT positions
2. 滑點 + 手續費納入計算
3. 回測 vs 在線預測結果一致性
4. 每個 regime 分開驗證 (bear/bull/chop)

---

## 📝 心跳歷史記錄

> 每次心跳在底部追加一行，保持最近 20 條。

### Heartbeat #246 — 2026-04-05 17:25-17:30
- **DB**: Raw=9180, Features=9142, Labels=8921, sell_win=49.9%（持平）
- **全域 IC**: 4/15（VIX -0.071, RSI14 -0.055, MACD -0.051, BB%B -0.058）→ 與 #245 完全一致
- **TW-IC**: 9/10 核心（Tongue +0.530, Body +0.510, ATR +0.443）
- **Regime IC**: Bear 3/8, Bull 2/8, Chop 0/8（持續 8+ 輪）
- **DW N=200**: 7/8 通過，CV=97.0%（200 樣本，過擬警告）
- **Global model**: Train=63.9%, CV=51.4%, gap=12.5pp
- **市場**: BTC=$66,994 (+0.14%), FNG=12（極度恐懼）, FR=0.00000210（-67%）
- **平行心跳**: 6/6 PASS, 200.9s
- **Tests**: 6/6 PASS, Backtest PASS
- **🔴 數據管線**: 175 分鐘未更新（持續惡化：#244=160→#245=160→#246=175）
- **🔴 連敗**: 156 持續

### Heartbeat #245 — 2026-04-05 17:15-17:20
- **DB**: Raw=9180, Features=9142, Labels=8921（持平）
- **全域 IC**: 4/15, TW-IC 9/10, DW N=200: 7/8
- **CV**: 51.4%（持平）
- **連敗**: 156
- **數據管線**: 160 分鐘未更新

### Heartbeat #223 — 2026-04-05 10:23-10:45
- **DB**: Raw=9180, Features=9142, Labels=8921, sell_win=50.8%
- **TW-IC**: Tongue +0.53, Body +0.51, Pulse -0.30, Mind -0.20 → 7/8 核心通過
- **CV**: 52.3% (gap 12.5pp) — 正則化增強後改善
- **P1 新增**: NQ (納斯達克) 納入 macro_data.py
- **P1 新增**: 10 個新感官加入代碼 (Claw, Fang, Fin, Web, Scales, Nest + TI)
- **Feature count**: 10 → 20 (含交叉特徵 14 個)
- **前端**: 需要更新 RadarChart 到 20 鍵
- **Cron issue**: 串行心跳超時 (22min > 10min limit) → 改用 hb_parallel_runner.py

---

## 紀律

1. **每次都讀** AI_AGENT_ROLE.md → 不可跳過
2. **全流程執行** Step 0-8 → 不做半套
3. **D 必須轉化為行動** → 不寫在文件裡就不算做了
4. **不問用戶，發現問題直接修** → 你是閉迴路 AI
5. **每次修改都 commit** → git 歷史要清
6. **負熵思維** → 每次心跳都要問：「今天比昨天更有序嗎？」
7. **Sensory ETF** → 用 IC 說話，不憑感覺
8. **平行執行** → 串行超時就用 parallel runner

---

## 通往 90% 勝率的策略路線

> 每一輪心跳都必須對照這份路線圖，檢查進度與偏離。

### Phase A：資料品質（地基）
- [ ] 確保 raw → features → labels 三層管線無 future leakage
- [ ] 每個 feature 都有 IC 實證，IC < 0.05 的感官必須替換
- [ ] 歷史資料能回放、能重算、版本化
- [ ] 標籤定義與交易行為完全對齊（sell_win 是核心標籤）

### Phase B：模型校準（核心引擎）
- [ ] Sensory ETF 動態權重 fusion 取代固定權重
- [ ] 信心校準（Platt / isotonic / temperature scaling）
- [ ] 市場狀態感知模型選擇（不同 regime 用不同模型）
- [ ] 放棄交易機制：低信心不交易

### Phase C：回測可驗證（檢驗）
- [ ] 回測結果可重跑、可比對、可追溯
- [ ] 賣出勝率、利潤因子、夏普比率全部在 dashboard 顯示
- [ ] 回測與上線指標完全一致，不偷換

### Phase D：儀表板可用（可視化）
- [ ] 雷達圖顯示 20 個感官
- [ ] IC 條形圖、ETF 權重圓環
- [ ] 價格 × 多感官 overlay 圖清晰可辨
- [ ] 空圖要顯示具體原因，不是留白
- [ ] 3 秒內看懂，暗色主題，中文界面

### Phase E：負熵永動機（持續進化）
- [x] 20 個感官代碼已寫入 (Heartbeat #223)
- [ ] 等新數據累積 24-48h 後驗算 IC
- [ ] 根據 IC 淘汰 C/D 級感官
- [ ] 繼續引入新數據源：Twitter/X、新聞、巨觀日曆
