# HEARTBEAT.md — Poly-Trader 心跳任務（5 分鐘循環）

> 心跳詳細流程。角色定義見 [AI_AGENT_ROLE.md](AI_AGENT_ROLE.md)，系統架構見 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 🔄 心跳完整流程

每次心跳必須嚴格執行以下 **Step 0 ~ Step 6**，不可跳過。

---

### Step 0: 閱讀 AI_AGENT_ROLE.md（每次必讀）
- 每次心跳必須完整閱讀 `Poly-Trader/AI_AGENT_ROLE.md`
- 先確認當前角色、紀律、邊界與 P0 問題清單
- 再確認系統架構與目標（準確度 > 90%）
- 此步驟不可跳過，即使只是例行心跳

### Step 1: 數據收集
- 運行 `ssh Kazuha@192.168.0.238 "cd C:\Users\Kazuha\repo\Poly-Trader && python scripts/dev_heartbeat.py"`
- 運行 collector 收集最新數據
- 記錄最新 raw / features / labels 數量、BTC 價格、衍生品數據

### Step 2: 感官表現分析
- 計算每個感官的 IC（Information Coefficient）對 labels
- 檢查特徵品質：std、range、unique_count
- 標記異常：IC < 0.05 → 🔴，std ≈ 0 → ⚠️

### Step 3: 多重會議激盪

#### Step 3.1: 六帽會議（每輪心跳皆執行）
針對數據、使用者介面、使用者操作起來的感受、使用者預期達到的目標、使用者設計這個程式的初衷討論。

| 帽子 | 職責 |
|------|------|
| ⚪ 白帽 | 客觀事實 — 數據、IC、測試結果 |
| 🔴 紅帽 | 直覺感受 — 系統給人什麼感覺 |
| ⚫ 黑帽 | 風險缺陷 — 什麼可能出錯 |
| 🟡 黃帽 | 正面價值 — 什麼在正常工作 |
| 🟢 綠帽 | 創意方案 — 有什麼新方法 |
| 🔵 藍帽 | 管控決策 — 下一步、優先級 |

#### Step 3.2: 迪士尼會議（有可行方案時執行）
針對數據、使用者介面、使用者操作起來的感受、使用者預期達到的目標、使用者設計這個程式的初衷討論。

| 角色 | 職責 |
|------|------|
| 🎵 夢想家 | 理想的會是什麼樣子？ |
| 🚫 批評家 | 方案有什麼漏洞？ |
| 🔧 現實家 | 實際上怎麼做？ |
| 🎯 裁判 | 最終決策：做不做？優先級？ |

#### Step 3.3: ORID 循環（整合會議 → 行動）
綜合六帽會議的輸出，形成具體行動規劃。

| 階段 | 內容 |
|------|------|
| **O** 客觀事實 | 綜合六帽白帽事實 + 迪士尼批評分析 + 收集到的數據與 IC 值 |
| **R** 感受直覺 | 六帽紅帽直覺 + 迪士尼夢想家願景 + 數據揭示的趨勢風險 |
| **I** 意義洞察 | 六帽黑帽風險分析 + 迪士尼現實家執行洞察 + 數據的因果推論 |
| **D** 決策行動 | 六帽藍帽優先級 + 迪士尼裁判最終決策 → 產出 P0-P5 行動項目，記錄在 ISSUES.md / PRD.md / ROADMAP.md / ARCHITECTURE.md |

### Step 4: ISSUES 狀態
- 列出當前所有未解決問題及優先級
- 評估影響範圍和緊急程度
- 若有新問題，立即補進 ISSUES.md

### Step 5: 修正與測試

#### Step 5.1: ISSUES 修正（完全自動執行，不問用戶意見）
- 直接修正問題，不要只討論
- 修改前先審閱（git diff）
- 修改後務必確認不破壞既有功能

#### Step 5.2: 功能測試（如果有修改代碼）
- 運行 `ssh Kazuha@192.168.0.238 "cd C:\Users\Kazuha\repo\Poly-Trader && python tests/comprehensive_test.py"`
- 若有修改資料流程或模型，再補跑對應的更窄測試

### Step 6: 回報摘要
輸出格式：
```text
📊 心跳摘要 [時間]
- Raw: ?? / Features: ?? / Labels: ??
- BTC: $??? | 衍生品: LSR=? GSR=? Taker=? OI=?
- 感官 IC: Eye=? / Ear=? / Nose=? / Tongue=? / Body=? / Pulse=? / Aura=? / Mind=?
- 會議結論：
  ⚪ 白帽：[簡述事實]
  🔴 黑帽：[主要風險]
  🟢 綠帽：[建議方案]
  🔵 藍帽：[決策與優先級]
  📋 ORID D：[具體行動項目]
- 本輪修改：[做了什麼]
- 測試結果：[pass/fail]
- ROADMAP：[更新了什麼]
```

---

## ⚠️ 重要原則
1. 每次心跳必須讀取 AI_AGENT_ROLE.md（Step 0），不可跳過
2. 每次心跳執行 Step 0-6 全流程
3. D（決策）必須轉化為具體行動
4. 不問用戶意見，發現問題直接修復
5. 修改代碼後必須 commit

---

## ⛔ 開發環境約束（嚴格遵守）

所有程式碼開發、修改、測試必須在本機 Windows 進行，嚴禁在 Raspberry Pi 上執行任何開發操作。

- 開發機器：`Kazuha@192.168.0.238`
- 工作目錄：`C:\Users\Kazuha\repo\Poly-Trader`
- 連線方式：`ssh Kazuha@192.168.0.238`
- Raspberry Pi 僅執行 OpenClaw Gateway，不進行任何程式碼修改

執行規則：
1. 所有檔案讀取：`ssh Kazuha@192.168.0.238 "type C:\Users\Kazuha\repo\Poly-Trader\<file>"`
2. 所有檔案寫入：透過 SSH 執行寫入指令
3. 所有 Python 執行：`ssh Kazuha@192.168.0.238 "cd C:\Users\Kazuha\repo\Poly-Trader && python <script>"`
4. 所有 Git 操作：`ssh Kazuha@192.168.0.238 "cd C:\Users\Kazuha\repo\Poly-Trader && git ..."`
5. 絕對禁止在 `~/.openclaw/workspace/Poly-Trader/` 建立或修改任何程式碼檔案
