# HEARTBEAT.md — Poly-Trader Productization Charter

> 核心參考：`ISSUES.md`、`ROADMAP.md`、`issues.json`、`ARCHITECTURE.md`、`README.md`

---

## 0. 心跳唯一目的
**心跳唯一目的：把 Poly-Trader 往可運營、可驗證、可產品化的 P0/P1 主線推進。**

若本輪沒有帶來以下任一項，視為不合格：
- code / runtime / UI patch
- 可重跑驗證證據
- `ISSUES.md / ROADMAP.md / issues.json` 的 current-state overwrite sync
- commit + push 到 git remote（若失敗，必須明記 blocker）

---

## 1. P0/P1 優先原則（強制）
每次修改前，必須先對齊 `ISSUES.md` 中的 **P0 / P1 issue**。

### 允許做
- 直接修 P0 / P1 問題
- 為了完成 P0 / P1 所需的測試、文件、驗證、部署契約修正

### 不允許做
- 在 P0 / P1 尚未收斂時，做不對應 issue 的 side quest
- 只改漂亮、只改報告、只重跑數字
- 做完 patch 卻不回寫 issue / roadmap / heartbeat current state

**硬規則：每次修改都必須能指出它對應哪一個 P0 / P1 issue。**

---

## 2. 文件治理規則（強制）
以下文件每次心跳都必須採用 **覆蓋更新（overwrite）**，只保留 current state：
- `ISSUES.md`
- `ROADMAP.md`
- `issues.json`
- `HEARTBEAT.md`
- 其他 current-state 摘要文件

禁止：
- 追加長篇歷史流水帳
- 把失效 issue 留在 current-state 文件中
- 文件與實際 repo 狀態不一致

---

## 3. 每輪固定流程（不可省略）
```text
Read ISSUES / ROADMAP / HEARTBEAT
↓
鎖定本輪對應的 P0/P1 issue
↓
做最少且直接的 patch
↓
verify（pytest / build / API / runtime / browser）
↓
overwrite 更新 ISSUES / ROADMAP / issues.json / 必要 heartbeat 文件
↓
git add / commit
↓
git push origin
↓
若 push 或 verify 失敗，將 blocker 回寫 current-state 文件
```

如果缺少以下任一步，視為 heartbeat 未完成：
- issue alignment
- patch
- verify
- docs overwrite sync
- commit
- push / blocker 記錄

---

## 4. 驗證規則
每輪至少要留下與本輪改動直接對應的驗證證據：
- Python / API 改動 → `pytest`
- 前端 contract 改動 → frontend contract tests / build
- runtime surface 改動 → API payload / browser / artifact 檢查

**沒有驗證，不得 commit。沒有 commit，不得視為完成。**

---

## 5. Git / Remote 規則
- 預設目標：`origin`
- 驗證完成後，必須提交並推送到 git remote
- 若因 auth / remote reject / failing tests 無法 push：
  - 不可假裝完成
  - 必須在 `ISSUES.md` / `ROADMAP.md` / heartbeat summary 中明記 blocker

---

## 6. 當前固定主線
1. Strategy Lab / leaderboard / model surfaces 必須可信且可比較
2. execution / runtime / UI contract 必須一致
3. heartbeat 必須維持 current-state-only 治理，且每輪 commit + push

---

## 7. 本輪 next gate 寫法
下一輪 gate 只能寫：
- 1~3 個最重要的 P0/P1 目標
- 每項的驗證方式
- 若失敗如何升級為 blocker

禁止寫成模糊願望清單。
