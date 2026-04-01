# Poly-Trader Issues 追蹤

---

## ✅ 已修復

| ID | 問題 | 修復 | 驗證 |
|----|------|------|------|
| #H04 | 五感分數映射為同一個區間 0~1 | 改為各自獨立 min/max 範圍 | ✅ 五感獨立映射 |
| #H05 | 模型返回固定值使用 XGBoost | 無實際影響 | ✅ 仍使用 |
| #M09 | Tongue FNG 卡死 | 已回填資料有多個 FNG 值 | ✅ 30 unique |
| #H20 | Ear/Nose 特徵洩漏（共用 funding_rate） | ⏳ 待執行 - Nose 改用 OI ROC | 🟡 待執行 |

---

## 🟡 觀察中

| ID | 問題 | 建議解法 |
|----|------|----------|
| #H20 | Ear/Nose 共線 (r≈0.998) | Nose 改用 OI ROC |
| #M06 | 模型準確率 ~50% | 增加 lag features |
| #M07 | 五感映射缺少統計意義 | 基於 IC 動態調整 |
| #009 | 缺少 SHAP 可解釋性 | 安裝 shap 庫 |

---

## 🔴 高優先級

| ID | 問題 | 解法 | 狀態 |
|----|------|------|------|
| #H01 | 回測使用 random 而非真實數據 | **已改 api.py: 讀 DB 五感數據** | ✅ 04-01 |
| #H02 | collector 持續寫入新數據 | **使用 v3/v4 數據收集** | ✅ 04-01 |
| #H03 | 前端 Vite 編譯/資料同步問題 | **修正環境變量 + proxy** | ✅ 04-01 |
| UX6 | AdviceCard `undefined length` | **修改 Props 確保唯一性** | ✅ 04-01 |
| UX7 | 回測需要顯示 | **BacktestSummary Null Safety** | ✅ 04-01 |
| UX8 | 五感映射圖時間軸不一致 | **新增 MergedPoint 修復** | ✅ 04-01 |
| #018 | 90 天回填歷史數據 | **已回填 90 天數據** | ✅ 2498 rows |

---

## 🟢 下次迭代

- **[Action 1]**: Nose 改用 OI-based 數據源（消 #H20）
- **[Action 2]**: 增加 lag features（1h, 4h, 24h）
- **[Action 3]**: 重新訓練模型並評估
- **[Action 4]**: 修正 comprehensive_test 的 body_roc 測試（採樣最近 100 筆而非最先 100 筆）

---

**最後更新**: 2026-04-01 11:44 GMT+8
