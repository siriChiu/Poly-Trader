# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-25 14:52:00 CST_

---

## 心跳 #20260425_1441 ORID

### O｜客觀事實
- full heartbeat 已完成 collect + diagnostics refresh：`Raw=32239 / Features=23657 / Labels=65041`；歷史覆蓋 `2y_backfill_ok=True`；`simulated_pyramid_win=56.89%`。
- parallel runner 5/5 通過：`full_ic / regime_ic / dynamic_window / tests / train`；comprehensive test 6/6；train `CV=64.00% ± 7.36%`。
- 即時部署阻塞仍是 canonical circuit breaker：`deployment_blocker=circuit_breaker_active` / `streak=9` / recent 50 `2/50` 勝 / 還差 `13` 勝；q15 current-live support 已達 `82/50`，但 support closure 不等於 deployment closure。
- recent canonical primary window 惡化：最近 100 筆 `win_rate=19.0%`、`dominant_regime=bull(99.0%)`、`avg_quality=-0.0506`、`avg_pnl=-0.0038`，alerts=`label_imbalance, regime_concentration, regime_shift`。
- leaderboard governance 仍 single-role alignment，但 model leaderboard payload 仍 `payload_stale=true` / `payload_source=latest_persisted_snapshot` / `payload_age≈43.2m`。
- 本輪產品化 patch：Strategy Lab 模型排行榜現在在 `modelMeta.stale=true` 時顯示 stale-while-revalidate lifecycle（背景重算/等待重試、cache age、refresh reason、next retry、cooldown）與 `重新整理模型排行榜`，避免 stale rows 被誤讀成 fresh production truth。

### R｜感受直覺
- 最大風險不是 q15 support 不足，而是 operator 把已達 support、stale leaderboard 或 venue metadata OK 誤讀成可以部署；因此 UI 必須 breaker-first、freshness-first。
- leaderboard stale 狀態若只藏在 API payload，Strategy Lab 仍會看起來像「有排行榜就正常」；這是產品化 deception，需要在 UI 明確揭露。

### I｜意義洞察
1. **Circuit breaker 仍是唯一 current-live deployment gate**：q15 `82/50` 只代表 current bucket support ready，無法替代 recent 50 release math。
2. **Recent pathology 是根因監控，不是當前 live 放行依據**：current live regime 為 chop/CAUTION，但 blocker pocket 最近 100 幾乎全 bull，需保留 drift evidence 而非泛化。
3. **Stale leaderboard 必須產品化顯示**：stale-while-revalidate 是正確的 API 策略，但 UI 不顯示 lifecycle 時仍會造成 operator 誤讀。

### D｜決策行動
- **Owner**：Strategy Lab / leaderboard product surface。
- **Action**：保留 async/stale-while-revalidate，不改成同步重算；把 stale lifecycle、快取年齡、重試時間與手動刷新動作直接呈現在 `/lab`。
- **Artifacts**：`web/src/pages/StrategyLab.tsx`、`tests/test_frontend_decision_contract.py`、`ISSUES.md`、`ROADMAP.md`、`issues.json`。
- **Verify**：`python -m pytest tests/test_frontend_decision_contract.py -q`、`python -m pytest tests/test_model_leaderboard.py tests/test_strategy_lab.py -q`、`npm run build`、browser `/lab` DOM 檢查 stale lifecycle card。
- **If fail**：若 `/lab` 再次只顯示 stale rows 而沒有 lifecycle / refresh action，升級為 P1 leaderboard freshness product blocker；若 breaker release math 被 leaderboard/support UI 蓋掉，升級回 P0 current-live blocker truth regression。
