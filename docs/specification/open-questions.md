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

**ACCEPTED — 2026-08-11**

Owner選擇 **C：極小額、單層、人工監督Live Canary**。

- 近期實戰Definition of Done：受監督Live Canary。
- Paper/Shadow：必要前置能力，不是最終milestone。
- Full Auto Live：後續獨立milestone。
- Q1不決定manual UI或受管worker的authorization入口；由Q9處理。
- Hard execution safety不因本決策降低。

ADR：[`../adr/ADR-0001-live-canary-product-scope.md`](../adr/ADR-0001-live-canary-product-scope.md)

To-be BDD：[`features/to-be/live-canary-product-scope.feature`](features/to-be/live-canary-product-scope.feature)

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

**ACCEPTED — 2026-08-11**

Owner選擇 **A：永久有效，只有Owner手動撤銷**。

- 本決策處理lifecycle，不決定完整identity欄位；identity由Q6確認。
- Release record不因support、evidence、breaker、binding、market或venue狀態自動撤銷。
- Technical/hard safety仍可令capacity=0並阻止risk-on。
- 不同identity不自動繼承舊release；原release也不因mismatch被撤銷。

ADR：[`../adr/ADR-0002-personal-release-lifecycle.md`](../adr/ADR-0002-personal-release-lifecycle.md)

To-be BDD：[`features/to-be/personal-release-lifecycle.feature`](features/to-be/personal-release-lifecycle.feature)

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

**ACCEPTED — 2026-08-11**

Owner選擇 **A：純Evidence Advisory**。

白話定義：資料不足只顯示「類似案例較少、信心較低」，仍可照常做ADR-0001的極小額、單層Live Canary。

- 不阻止Owner release。
- 不把allowed layers改成0。
- 不作每筆order hard gate。
- Support達標也不自動放大金額、增加層數或開啟Full Auto。
- Exact bundle、kill switch、breaker、permit、cap、venue與lifecycle safety仍全部強制。

ADR：[`../adr/ADR-0003-exact-support-advisory.md`](../adr/ADR-0003-exact-support-advisory.md)

To-be BDD：[`features/to-be/exact-support-advisory.feature`](features/to-be/exact-support-advisory.feature)

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

**ACCEPTED — 2026-08-11**

Owner選擇 **E：每次先產生一張完整狀態單，API、畫面與文件都只顯示同一張**。

白話定義：不同時間與版本的設定、DB、JSON和probe不能拼在一起。每張狀態單都有唯一編號、時間與完整來源；不完整就不發布，過期就明確顯示不知道。

- 技術名稱：immutable `DecisionSnapshot`。
- API/UI/generated docs只讀同一active snapshot ID。
- 明確的0與false不得被舊值覆蓋。
- Snapshot不是Owner release、order permit或venue truth的替代品。
- 每筆order仍需last-mile quote、kill switch、exposure、permit與idempotency檢查。

ADR：[`../adr/ADR-0004-decision-snapshot-truth.md`](../adr/ADR-0004-decision-snapshot-truth.md)

To-be BDD：[`features/to-be/decision-snapshot-truth.feature`](features/to-be/decision-snapshot-truth.feature)

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

**ACCEPTED — 2026-08-11**

Owner選擇允許**自動重建資料、重新訓練與比較模型、更新報告和狀態，讓模型自行成長**。

白話邊界：系統可自動訓練挑戰者；真正更好時可成為research/shadow新候選，但不能偷偷替換Live Canary模型。

- 「更好」優先看成本後ROI、最大回撤、profit factor與穩定性，不只看accuracy。
- 資料污染、look-ahead、label mismatch或不可重現時停止promotion。
- 新模型是新identity，不繼承舊Owner release。
- Heartbeat不自動修改source code、feature/label語義、交易規則或hard safety。
- Report與狀態單可自動更新，但必須同generation。

ADR：[`../adr/ADR-0005-autonomous-model-improvement.md`](../adr/ADR-0005-autonomous-model-improvement.md)

To-be BDD：[`features/to-be/autonomous-model-improvement.feature`](features/to-be/autonomous-model-improvement.feature)

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

**ACCEPTED — 2026-08-11**

Owner選擇**完整封裝**：任何模型、資料、指標、預測目標、參數或交易規則改變，都算新版本。

Owner另確認：新模型先和舊模型同步模擬一段時間；判定新模型更優後通知Owner，由Owner決定是否切換Live Canary。

- 技術名稱：immutable `DeploymentBundle`。
- Runtime必須驗證完整manifest與content hashes，不能只相信path或profile name。
- 安全override只能暫停或向下縮小cap，不能換模型、規則或放大風險。
- 新bundle不繼承舊release、permit或live pointer。
- Owner明確選擇後才atomic切換；舊訂單與持倉保留原bundle歸屬。

ADR：[`../adr/ADR-0006-immutable-deployment-bundle.md`](../adr/ADR-0006-immutable-deployment-bundle.md)

To-be BDD：[`features/to-be/immutable-deployment-bundle.feature`](features/to-be/immutable-deployment-bundle.feature)

---

## Q7 — Paper/Shadow evidence 是否必須與部署candidate完全同identity？

### 選項

A. 全域shadow outcomes可解除任何candidate gate。
B. model+feature profile相同即可。
C. exact immutable bundle相同才可promotion；其他只作diagnostic/reference。

### Recommendation

選 **C**。現有random-forest shadow evidence不能替owner-approved logistic bundle放行。

### Decision

**ACCEPTED — 2026-08-11**

Owner選擇 **C：只能使用這個完整新版本自己的成績，其他模型只能參考**。

白話定義：每個bundle都是獨立考生，不能拿別人的考卷替它加分。

- Prediction、intent、outcome都必須帶exact bundle與snapshot identity。
- 相同model class或feature profile仍不能共用promotion成績。
- Bundle任何內容改變後，新版本從自己的valid evidence開始。
- 舊成績保留為reference，不刪除但不計入新版本。
- 缺少identity的legacy outcomes不可事後猜測歸屬。
- Q3 support仍只作warning，但support rows也不能跨bundle借用。

ADR：[`../adr/ADR-0007-exact-bundle-shadow-evidence.md`](../adr/ADR-0007-exact-bundle-shadow-evidence.md)

To-be BDD：[`features/to-be/exact-bundle-shadow-evidence.feature`](features/to-be/exact-bundle-shadow-evidence.feature)

---

## R1 — Live Canary保守風險上限（補充Owner決策）

### Decision

**ACCEPTED — 2026-08-11**

Owner選擇保守方案：

- 每筆risk-on與全部Live Canary曝險：`min(25 USDT, account equity × 0.5%)`。
- UTC單日實現虧損：`min(10 USDT, start-of-day equity × 0.25%)`後停止新增風險。
- 連續2次真實送單失敗後停止新的risk-on。
- 低於交易所minimum order時不交易，不自行提高金額。
- Cancel、reduce、exit與reconcile仍可執行。

ADR：[`../adr/ADR-0008-conservative-live-canary-risk.md`](../adr/ADR-0008-conservative-live-canary-risk.md)

To-be BDD：[`features/to-be/conservative-live-canary-risk.feature`](features/to-be/conservative-live-canary-risk.feature)

---

## Q8 — Docs/AI指令可否影響execution決策？

### 選項

A. Docs可定義gate並由AI解讀。
B. Docs只描述policy；machine-readable policy/typed code執行gate。
C. AI可在owner instruction後直接改runtime gate。

### Recommendation

選 **B**。Docs可解釋、runbook可操作、AI可提出變更，但execution authorization只接受versioned machine policy與explicit release/permit records。

### Decision

**ACCEPTED — 2026-08-11**

Owner選擇 **B：文件與AI只能解釋、提醒和提出修改；真正下單只相信正式設定、核准紀錄與單次許可**。

- Markdown、AI summary、一般聊天與`ready=true`都不是execution authority。
- Chat決策必須轉成authenticated formal record，才會影響live state。
- AI可提出code/policy變更，但需tests、review、version與deployment流程。
- Risk-on仍需exact bundle、fresh snapshot、hard safety與signed single-use permit。
- AI/Docs與machine state衝突時，execution fail closed並修正projection，不改machine state迎合文字。
- Kill switch的啟動/解除也是正式machine action，不靠一句文字。

ADR：[`../adr/ADR-0009-docs-ai-non-authoritative.md`](../adr/ADR-0009-docs-ai-non-authoritative.md)

To-be BDD：[`features/to-be/docs-ai-non-authoritative.feature`](features/to-be/docs-ai-non-authoritative.feature)

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

**ACCEPTED — 2026-08-11**

Owner選擇 **B：畫面顯示完整模型、金額與風險，再次確認後取得只限這一筆的一次性許可**。

- Preview顯示exact bundle、snapshot、venue/account、symbol、side、金額、費用、cap與風險。
- Preview不簽permit、不送單。
- Owner確認後Server重新檢查全部hard safety；狀態變更就要求重新確認。
- Permit綁exact order、bundle、snapshot、cap、quote、TTL與single-use nonce。
- Double-click/retry最多呼叫venue一次。
- Ack不等於fill；UI追蹤partial/fill/cancel/reject/unknown與reconciliation。
- AI不能代替Owner確認或簽permit。

ADR：[`../adr/ADR-0010-manual-live-canary-permit.md`](../adr/ADR-0010-manual-live-canary-permit.md)

To-be BDD：[`features/to-be/manual-live-canary-permit.feature`](features/to-be/manual-live-canary-permit.feature)

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

**ACCEPTED — 2026-08-11**

Owner選擇 **A：第一階段只允許BTC/USDT；其他幣明確拒絕，保留未來擴充能力**。

- Canonical Phase-1 market是BTC/USDT spot。
- 非BTC request在fetch、training、snapshot、preview、permit或venue side effect前拒絕。
- 不得fallback到BTC、混用BTC 4H或跨symbol join。
- Data、bundle、snapshot、intent與ledger仍保留explicit symbol partition。
- Historical非BTC資料可保留作reference，但不進正式pipeline。
- 未來新增symbol需新ADR/BDD與portfolio risk決策。

ADR：[`../adr/ADR-0011-btc-usdt-phase-one.md`](../adr/ADR-0011-btc-usdt-phase-one.md)

To-be BDD：[`features/to-be/btc-usdt-phase-one.feature`](features/to-be/btc-usdt-phase-one.feature)
