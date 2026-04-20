# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-20 12:46:40 CST_

---

## 心跳 #fast ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=31214 / Features=22632 / Labels=62947`；`simulated_pyramid_win=57.17%`。
- current-live blocker 仍是 `deployment_blocker=circuit_breaker_active` / `streak=15` / `recent_window_wins=3/50` / `additional_recent_window_wins_needed=12`。
- q15 current-live bucket truth：`CAUTION|base_caution_regime_or_bias|q15` / `support=11/50` / `gap=39` / `support_route_verdict=exact_bucket_present_but_below_minimum`。
- recent pathological slice 仍是 `window=250 / win_rate=1.6% / dominant_regime=bull(95.6%) / alerts=label_imbalance,regime_concentration,regime_shift`。
- Venue metadata smoke 成功只代表 metadata contract OK，不代表 live-ready；目前 Binance 仍是 public-only，OKX 仍是 disabled + public-only。
- 本輪 patch 已把 Dashboard / Strategy Lab / Execution Status 的 venue / account wording 對齊：public-only / disabled venue 不再顯示成泛化 `OK`，public-only 帳戶卡不再顯示無語義 `—`。

### R｜感受直覺
- 這輪最危險的產品問題不是 breaker 本身，而是 operator 可能把 `metadata OK` 誤讀成 `venue OK`，再把 `— USDT` 誤讀成資料壞掉而不是缺 private creds。
- 如果 UI 連 blocker 與 venue/account readiness 語義都不分層，execution product surface 會比模型本身更早誤導使用者。

### I｜意義洞察
1. **metadata smoke success ≠ venue ready**：public-only / disabled lane 必須顯式講清楚，否則 operator 會把 read-only lane 當成可執行 lane。
2. **public-only account snapshot 也要有語義**：當 private creds 缺失時，`—` 不是中性資訊，而是 UI contract 缺口；必須明講「private balance unavailable until exchange credentials are configured」。
3. **shared component 比散落頁面更能守住 product truth**：把 Execution Status 改成共用 `VenueReadinessSummary`，可避免 `/` `/lab` `/execution/status` 再次各說各話。

### D｜決策行動
- **Owner**：execution operator-facing UI / venue-readiness contract
- **Action**：
  1. 擴充 `VenueReadinessSummary`，把 public-only / disabled / configured 與 metadata contract 分層顯示。
  2. 讓 `ExecutionStatus.tsx` 改用共享 `VenueReadinessSummary`，移除頁內重複 venue card 邏輯。
  3. 把 Dashboard / Execution Status 的資金卡在 public-only 模式下改成顯式 unavailable copy。
- **Verify**：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/` `/execution/status` `/lab`。
- **If fail**：只要 public-only / disabled venue 再次被渲染成泛化 OK，或 public-only 帳戶卡回退成 `—`，就把它升級回 operator-facing venue-readiness blocker，因為這會直接污染 live deployment judgment。
