# ISSUES.md — 問題追蹤

> 問題追蹤與狀態。架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，路線見 [ROADMAP.md](ROADMAP.md)。


> *
---

## ⛔ 開發環境約束（嚴格遵守）

**所有程式碼開發、修改、測試必須在本機 Windows 進行，嚴禁在 Raspberry Pi 上執行任何開發操作。**

- **開發機器**：`Kazuha@192.168.0.238`
- **工作目錄**：`C:\Users\Kazuha\repo\Poly-Trader`
- **連線方式**：`ssh Kazuha@192.168.0.238`
- **Raspberry Pi 僅執行 OpenClaw Gateway**，不進行任何程式碼修改

**執行規則**：
1. 所有檔案讀取：`ssh Kazuha@192.168.0.238 "type C:\Users\Kazuha\repo\Poly-Trader\<file>"`
2. 所有檔案寫入：透過 SSH 執行寫入指令
3. 所有 Python 執行：`ssh Kazuha@192.168.0.238 "cd C:\Users\Kazuha\repo\Poly-Trader && python <script>"`
4. 所有 Git 操作：`ssh Kazuha@192.168.0.238 "cd C:\Users\Kazuha\repo\Poly-Trader && git ..."`
5. 絕對禁止在 `~/.openclaw/workspace/Poly-Trader/` 建立或修改任何程式碼檔案

*最後更新：2026-04-02 18:05 GMT+8*
> **🔄 心跳 #101：Pulse 失效替換（vol_ratio_12_48，IC=+0.1087）；全 8 感官 IC OK；BTC=$66,476；CV=56.30%；6/6測試通過**

---

## 🔴 最高優先級 (P0)

*暫無 P0 — 系統穩定*

## 🟡 高優先級 (P1)

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H87 | 🟡 CV≈56% 距目標 90% 差距仍大 | 累積更多數據（現 11K/目標 50K+）+ 特徵創新 | 🟡 P1 |
| #H31 | 🟡 歷史 raw data polymarket_prob 幾乎全 NULL | Ear/Polymarket 歷史信號缺失 | 🟡 P1 |

## 🟢 低優先級

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H94 | 全量 IC 仍被舊數據稀釋 | 已改用近期N=5000，監控效果 | 🟢 P2 |
| #IC4 | 模型動態 IC 加權 | sample_weight 依 IC 動態調整 | 🟢 P3 |
| #H97 | rolling IC 穩定性追蹤 | 建立每次心跳 IC 歷史趨勢記錄 | 🟢 P3 |

## 🏆 已解決

| ID | 問題 | 解決方案 | 日期 |
|----|------|----------|------|
| **#H115** | 🔴 Pulse IC=0 完全失效（vol_spike12 失效） | 替換為 vol_ratio_12_48（IC=+0.1087）✅ | 04-02 16:05 |
| **#H114** | 🔴 Tongue/Aura 感官替換後穩定監控 | tongue→vr24/144; aura→fr_abs_norm | 04-02 15:44 |
| **#H113** | 🔴 Aura IC 驟降（-0.0171，失效） | 替換為 volume_trend_12（IC=-0.2522）✅ | 04-02 13:39 |
| **#H112** | 🔴 Tongue IC 驟降（-0.0016，失效） | 替換為 fr_acceleration（IC=+0.1162）✅ | 04-02 13:39 |
| **#H111** | ⚠️ Pulse IC 接近閾值（-0.0717） | 已升 P0 → 解決 #H115 | 04-02 16:05 |
| **#H110** | ⚠️ Tongue IC 弱（-0.0043 上輪）| 本輪自然回升至 +0.0880 ✅ | 04-02 13:29 |
| **#H109** | ⚠️ Aura IC 驟降（-0.0089 上輪）| 本輪自然回升至 +0.0791 ✅ | 04-02 13:29 |
| **#H108** | 🔴 Pulse IC 連續3輪 < 0.05（vol_roc48 無效） | 替換為 vol_spike12（IC=-0.0669, p=0.034）✅ | 04-02 13:25 |
| **#H107** | Eye IC 衰減至臨界（0.0497 < 0.05） | 本輪心跳自然回升 ✅ | 04-02 13:09 |
| **#H106** | ic_signs.json stale（全量N=15366稀釋） | 改用近期N=5000，全8感官IC>0.05 | 04-02 12:40 |
| **#H105** | Ear IC 弱(-0.029) | 替換為 mom_24(IC=-0.085@recent) | 04-02 12:35 |
| **#H104** | Eye IC 弱(-0.021) | 替換為 fr_cumsum_48(IC=-0.063@recent) | 04-02 12:35 |
| **#H102** | model/last_metrics.json stale | 同步修正 | 04-02 12:05 |
| **#H101** | Pulse/Aura IC 不顯著 | Pulse→vol_roc48; Aura→vol_ratio_short_long | 04-02 11:57 |
| **#H100** | label=-1 只有 2 筆 | UPDATE labels 修正門檻；CV 45%→56% | 04-02 11:19 |
| **#H99** | Nose IC≈0.005 | 替換為 RSI14 norm（IC=-0.082）| 04-02 11:13 |
| #H96 | ic_signs.json stale | N=4975 重算 + 重訓 | 04-02 10:38 |
| #H95 | Body IC 不顯著 | 替換為 price_ret_20P | 04-02 10:20 |
| #H76 | 模型過擬合 | 加強正則化 | 04-02 06:44 |
| #H67 | labeling 時間戳匹配失敗 | nearest-match | 04-02 05:11 |
| #H62 | 偽標籤污染 | 清除 4383 筆偽標籤 | 04-02 04:15 |
| #H43 | 8,760 筆 1969-era 污染數據 | 全部清除 | 04-02 00:06 |

---

## 📊 當前系統健康 (2026-04-02 18:02 GMT+8)

### 數據管線
| 項目 | 數值 | 狀態 |
|------|------|------|
| Raw data | 11,129 筆 | ✅ 每 5 分鐘增長 |
| Features | 11,114 筆 | ✅ |
| Labels | 22,099 筆 (h=4 + h=24) | ✅ 三類均衡 |
| BTC 當前 | $66,476 | ✅ |
| FNG | 12.0（極度恐慌）| ⚠️ 市場悲觀 |
| Funding Rate | -2.61e-05（負/偏空）| ⚠️ |

### 感官 IC（N=5000，h=4）
| 感官 | 特徵 | IC | 狀態 |
|------|------|------|------|
| Eye | fr_cumsum_48 | -0.0533 | ✅ |
| Ear | mom_24 | -0.0733 | ✅ |
| Nose | RSI14_norm | -0.0734 | ✅ |
| Tongue | fr_acceleration | +0.0570 | ✅ |
| Body | vol_zscore_48 | +0.0720 | ✅ |
| Pulse | vol_ratio_12_48（新）| +0.1087 | ✅ **替換** |
| Aura | volume_trend_12 | +0.1067 | ✅ |
| Mind | ret_144 | -0.1457 | ✅ 強 |

### 模型性能
| 指標 | 值 |
|------|-----|
| Train Accuracy | 52.75% |
| TimeSeries CV | 56.30% ± 9.06% |
| n_features | 32（8 base + 24 lag）|

### 測試狀態
| 項目 | 狀態 |
|------|------|
| dev_heartbeat.py | ✅ 全 OK |
| comprehensive_test.py | ✅ 6/6 通過 |

---

## 📋 下一步優先行動

| 優先 | 行動 | Issue |
|------|------|-------|
| P1 | **累積數據**：每天+288筆，目標 50,000+ 筆 | #H87 |
| P1 | **監控新 Pulse**：vol_ratio_12_48 需 2-3 輪心跳驗證穩定 | #H115 |
| P2 | **研究組合特徵**：mind×eye 交叉項 IC 可能更高 | - |
| P3 | **IC 動態加權**：依近期 IC 調整 XGBoost sample_weight | #IC4 |

---
*此文件每次心跳完全覆蓋，保持簡潔。*


## Backtest Engine v3

- 加入交易成本模型：手續費 (0.1%%) + 滑點 (0.05%%)
- 加入 Buy ^& Hold 基準線 + Alpha 計算
- 修復 engine.py L116 重複 predict_proba bug
- metrics.py 新增 Sortino、最大連續虧損、平均持倉時間
- 新增 _build_results 輸出 buy_hold_curve / total_trading_cost


## 🟡 新增 P1

| ID | 問題 | 建議 | 狀態 |
|----|------|------|------|
| #H116 | 📈 價格 × 多感官走勢為空，疑似時間對齊 / 資料窗不足 / 回填缺口 | 改成 nearest-match 對齊 + 明確 empty-state + 補齊歷史窗 | 🟡 P1（進行中） |
| #H117 | 綜合推薦分數仍不精確，疑似模型校準 / 選型不穩 | 做 confidence calibration、regime-aware model selection、驗證不是感官本身造成偏差 | 🟡 P1 |
| #H118 | 🔬 回測引擎近期失效，需重新驗證交易曲線與指標輸出 | 重新跑 backtesting/engine.py、metrics.py、optimizer.py 的端到端驗證 | 🟡 P1（進行中） |

## 📋 近期補充說明

- `dashboard/app.py` 已補上價格 × 多感官 nearest-match 對齊與 empty-state 退化路徑；當資料窗不足時不再整張圖空白。
- `backtesting/engine.py` 與 `backtesting/metrics.py` 已補資料不足防呆，避免回測在空窗時直接炸掉。
- `server.senses` 與 `database.models` 已補上新舊感官欄位相容，但若圖表仍空，優先檢查「時間對齊」與「資料窗是否有重疊樣本」。
- 綜合推薦分數不精確，不應先假設感官失效；下一層應檢查模型校準、訓練樣本分佈、類別不平衡與 regime 切換。
- 回測引擎仍需用同一批資料重新驗證 buy/sell/abstain 與 `sell_win_rate` 是否正確輸出。
