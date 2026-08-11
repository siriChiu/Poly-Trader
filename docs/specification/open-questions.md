# Poly-Trader BDD Open Questions

> 這是 owner decision queue。對話中**一次只問一題**，避免多題答案互相污染。每題確認後才寫入 `features/to-be/` 與 ADR；下列 recommendation 不是既定決策。

## Q1 — 「實戰」的產品承諾是哪一層？

### 為何必須決定

目前文件/UI把「實戰」同時用在 Execution Console、paper/shadow、manual trade與live canary。若不先定義，BDD無法判斷何時算產品完成。

### 選項

A. 人工查看訊號，自行在交易所操作；Poly-Trader不送單。
B. Paper/Shadow自動運行與ledger，永不送真單。
C. 極小額、單層、人工監督live canary。
D. 完整自動live execution與order lifecycle。

### Recommendation

產品roadmap以 **C為近期「實戰」驗收、D為後續階段**；A/B是現在可用的安全模式。無論選C/D，現在的execution safety invariants不變。

### Decision

`PENDING_OWNER`

---

## Q2 — Owner personal release 的生命週期？

### 選項

A. 永久有效，只有owner手動撤銷。
B. 有到期日，需定期重新核准。
C. 對strategy version永久；strategy identity/version變更即需新release。
D. runtime evidence變差可自動撤銷。

### Recommendation

選 **C**。owner對不可變strategy release ID核准；統計惡化產生warning/position cap，但只有hard risk或owner撤銷會改execution capacity。不要讓artifact overlay改寫release record。

### Decision

`PENDING_OWNER`

---

## Q3 — Exact support（例如50 rows）應屬哪種gate？

### 選項

A. 純evidence advisory。
B. Strategy release gate。
C. Deployment/canary sizing gate。
D. 每筆order execution hard gate。

### Recommendation

個人使用採 **A + C**：不阻止owner release，但控制canary tier/最大層數；不在每筆order重新計算。若owner接受evidence risk，可把C降為保守cap，但不能碰hard execution safety。

### Decision

`PENDING_OWNER`

---

## Q4 — 哪一個來源是 aggregate current truth？

### 選項

A. `config.yaml`。
B. canonical DB。
C. latest JSON artifacts。
D. request-time API。
E. 新增不可變 `DecisionSnapshot`，其他都是input/projection。

### Recommendation

選 **E**。config/DB/artifact都有不同角色；由single application service在同generation建立DecisionSnapshot，API/UI/docs只投影。

### Decision

`PENDING_OWNER`

---

## Q5 — Heartbeat 可以自動修什麼？

### 選項

A. 只觀測，完全不寫。
B. fast lane可做輕量、可逆、idempotent maintenance；slow lane做重建。
C. 任一lane可自動改code/docs/artifacts。
D. heartbeat只排程domain jobs，不做policy/doc projection。

### Recommendation

選 **B + D**：fast lane只刷新small snapshots/leases/freshness；model rebuild、leaderboard、backfill、docs publication進slow/explicit lane；code patch不由定時heartbeat自動做。

### Decision

`PENDING_OWNER`

---

## Q6 — Runtime binding 必須綁哪些identity？

### 候選欄位

- strategy release ID/version
- fitted model artifact SHA256
- model class/version/hyperparameters
- feature schema + feature definition version
- label definition + target + horizon
- training data snapshot/range/hash
- calibration artifact/version
- strategy parameters/top-k/regime policy
- execution policy version

### Recommendation

以上全綁，形成immutable deployment bundle；paper/shadow與live必須載入同一bundle，只有execution mode/capital cap可在允許的runtime override範圍內不同。

### Decision

`PENDING_OWNER`

---

## Q7 — Paper/Shadow evidence 是否必須與部署candidate完全同identity？

### 選項

A. 全域shadow outcomes可解除任何candidate gate。
B. model+feature profile相同即可。
C. exact immutable bundle相同才可promotion；其他只作diagnostic/reference。

### Recommendation

選 **C**。現有random-forest shadow evidence不能替owner-approved logistic bundle放行。

### Decision

`PENDING_OWNER`

---

## Q8 — Docs/AI指令可否影響execution決策？

### 選項

A. Docs可定義gate並由AI解讀。
B. Docs只描述policy；machine-readable policy/typed code執行gate。
C. AI可在owner instruction後直接改runtime gate。

### Recommendation

選 **B**。Docs可解釋、runbook可操作、AI可提出變更，但execution authorization只接受versioned machine policy與explicit release/permit records。

### Decision

`PENDING_OWNER`

---

## Q9 — Manual live trade 是否是正式旅程？

### 背景

`/api/trade`有manual buy入口，但不傳execution permit；ExecutionService對non-dry order要求permit，因此現況沒有成功manual live路徑。

### 選項

A. 移除manual live buy；只允許受管worker取得permit。
B. manual operator可透過UI明確二次確認後取得單次permit。
C. manual route只作paper/shadow，live永遠外部手動。

### Recommendation

若近期目標是tiny canary，選 **B**；permit需綁exact order、bundle、cap、TTL與single-use nonce。若產品只做自動worker則選A。

### Decision

`PENDING_OWNER`

---

## Q10 — Multi-symbol 是否在本次重構scope？

### 背景

部分程式支援symbol variants，但preprocessor 4H抓取hard-code BTC/USDT，training merge未by-symbol。

### 選項

A. 先明確只支援BTC/USDT，schema仍保留symbol。
B. 本次同時完成真正multi-symbol partition。
C. 移除symbol抽象直到未來需要。

### Recommendation

選 **A** 作第一階段，並以BDD保證任何非BTC請求明確拒絕，不得靜默使用BTC 4H或跨symbol label；之後再擴展B。

### Decision

`PENDING_OWNER`
