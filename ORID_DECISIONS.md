# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-05-18 01:22:23 CST_

---

## 心跳 #1314-productization ORID

### O｜客觀事實
- Heartbeat runner status=`success`；`Raw=33499 / Features=24609 / Labels=66808`；`simulated_pyramid_win=56.65%`。
- Current-live blocker：`deployment_blocker=under_minimum_exact_live_structure_bucket`。
- Current bucket：`CAUTION|structure_quality_caution|q15`；exact support=`3/50`；gap=`47`；`support_route_verdict=exact_bucket_present_but_below_minimum`。
- Runtime：`allowed_layers_raw=1 → allowed_layers=0`；`runtime_closure_state=patch_inactive_or_blocked`。
- Recent drift：latest window `100`，wins/losses=`17/83`，win rate=`17.0%`，dominant regime=`bear 84.0%`，alerts=`label_imbalance, regime_shift`。
- High-conviction Top-K：`deployable_rows=0`，`risk_qualified_rows=6`，`runtime_blocked_candidate_rows=6`，仍是 paper/shadow-only。
- 本輪 patch：`/execution/status` 新增 `RecentCanonicalDriftCard`，由 `/api/status` fallback chain 取得 `recent_canonical_drift`，放在「部署診斷」與「帳戶快照」之間。
- 驗證：frontend decision contract `83 passed`；server recent drift/API status contract `3 passed`；web build 成功。local 8000/8001 health 未啟動，因此本輪不硬啟 dev runtime。

### R｜感受直覺
- 最大風險不是沒有新研究結果，而是 operator 在 canonical diagnostics page 看到部署 blocker，卻看不到 recent drift/root-cause，進而把 q15 3/50 當成單純樣本不足而忽略最近 100 筆 17% 勝率與 bear concentration。
- 另一個風險是 OOS-pass Top-K 候選被誤讀成可部署；目前 exact support gap 47 仍足以阻止 buy/add exposure。

### I｜意義洞察
1. **Blocker + drift 必須同屏**：current-live exact support shortage 與 recent canonical drift 是同一個產品決策鏈，不應散落在不同 surface。
2. **OOS pass ≠ deployment pass**：Top-K 候選可以進 shadow lane，但 exact support / venue proof / reconciliation proof 未過前不可升級。
3. **Docs overwrite 是 guardrail**：current-state docs 必須只說 latest truth，避免歷史 breaker / legacy support 文案污染 operator 判斷。

### D｜決策行動
- 決策：把 `/execution/status` 升級為 blocker-first + drift-aware canonical diagnostics，而不是只顯示阻塞與 venue/account 資訊。
- 已執行：修改 `web/src/pages/ExecutionStatus.tsx`；新增 frontend contract test；覆寫 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`；更新 heartbeat summary artifact 的 productization closure 欄位。
- 下一步 gate：若下輪 q15 exact support 未增加，優先做同 semantic identity evidence accumulation / q15 root-cause；若 backend 已啟動，補 browser QA 確認 `/execution/status` 實際畫面順序。
