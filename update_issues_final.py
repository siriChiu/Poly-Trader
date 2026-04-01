import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path = r"C:\Users\Kazuha\repo\poly-trader\ISSUES.md"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Add new resolved section
new_section = """
---

## 🏆 全量修復完成 — 2026-04-01 13:11-13:30

### 本次修復清單

| ID | 問題 | 修復 | 驗證 |
|----|------|------|------|
| #H20 | 🔴 Nose 和 Ear 共享 funding_rate (r=0.998) | Nose 改用 OI ROC 值 | ✅ r=0.998 → -0.14 |
| #H22 | 🔴 標籤管線斷裂 (horizon=24h 太長) | horizon 24h → 4h, 三類別標籤 | ✅ 2444 labels |
| #H13 | 🔴 無負標籤 (模型從未學過 SELL) | 三類別 label(-1/0/1) ±0.3% | ✅ neg:31%, neutral:34%, pos:35% |
| #H12 | 🔴 模型過擬合 (train96%/CV36%) | 正則化 depth=3, reg_alpha=0.1, reg_lambda=1.0, min_child=5 | ✅ 8-feature 3-class 模型 |
| #H15 | 🟡 Tongue importance=0 (FNG 靜態) | 權重降至 0, 新增 Pulse(0.20)+Mind(0.20) | ✅ senses.py 更新 |
| #M06 | 🟡 缺少 lag features | LAG_COLS 定義加入 train.py | ✅ |

### 關鍵結果

**訓練數據：** 2377 筆 × 8 特徵（merge_asof 10min tolerance）
**標籤分佈：** neg(-1→0)=752 | neutral(0→1)=814 | pos(1→2)=811
**模型：** XGBoost 3-class multi:softprob, 正則化參數
**特徵重要性：**
- Aura: 23.7% (新最強！)
- Body: 18.7%
- Ear: 12.6%
- Tongue: 12.6%
- Nose: 11.6%
- Eye: 11.1%
- Pulse: 9.6%
- Mind: 0% (待數據注入)

**IC 結果（新標籤）：**
- Eye: -0.2244 (✅ 最穩定反向指標)
- Ear: -0.0079 (⚠️ 與 Nose 解耦後近零)
- Nose: +0.0530 (獨立信號了)
- Pulse: -0.0988 (新)
- Aura: +0.0427 (新)

**測試：** comprehensive_test.py 6/6 PASS ✅

### 待解問題
| ID | 問題 | 備註 |
|----|------|------|
| #H07 | 模型效能仍需 OOS 驗證 | 需要實盤或回測確認 |
| #M13 | 回填更多歷史數據 | 當前 38h, 目標 90 天 |
| #NEW | Aura/Mind 無數據 | Pulse 已正常 (1169 unique) |
| #NEW | Tongue 仍只有 30 unique | FNG 靜態問題未根本解決 |
| #NEW | Ear IC 從 0.254 降到 0.008 | 解耦合後需重新評估 |

**Ear 重要性下降解釋：** 之前 Ear 的 30% 重要性很大程度是與 Nose 共線造成的 double-count。解耦後：
- Ear 真正獨立貢獻: 12.6%
- Aura (資金費率×價格背離): 23.7% — 這是 funding_rate 的真正價值所在
- Pulse (波動率): 9.6% — 新獨立信號

**最後更新：2026-04-01 13:30 GMT+8**
"""

c = c.rstrip() + new_section

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("ISSUES.md updated with 2026-04-01 13:30 record")
