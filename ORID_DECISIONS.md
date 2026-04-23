# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-23 12:55:30 CST_

---

## 心跳 #20260423j ORID

### O｜客觀事實
- live runtime truth：`deployment_blocker=exact_live_lane_toxic_sub_bucket_current_bucket` / `current_live_structure_bucket=BLOCK|bull_q15_bias50_overextended_block|q15` / `support=199/50` / `gap=0` / `entry_quality=0.4266` / `allowed_layers=0`。
- recent canonical drift：`latest_window=100` / `win_rate=97.0%` / `dominant_regime=bull(91.0%)` / `avg_quality=+0.6707` / `avg_pnl=+0.0224`；`blocking_window=1000` / `win_rate=41.7%` / `dominant_regime=bull(80.4%)` / `avg_quality=+0.1189` / `avg_pnl=+0.0030`。
- operator-facing patch：`web/src/utils/runtimeCopy.ts`、`web/src/pages/ExecutionConsole.tsx`、`web/src/pages/ExecutionStatus.tsx`、`web/src/pages/StrategyLab.tsx`、`tests/test_frontend_decision_contract.py` 已更新。
- 驗證：`pytest tests/test_frontend_decision_contract.py tests/test_execution_surface_contract.py tests/test_strategy_lab.py -q` → `123 passed`；`cd web && npm run build` → pass；browser `/`、`/execution/status`、`/lab` 主 blocker 區塊無 raw machine-token regression。

### R｜感受直覺
- runtime truth 本身沒有變，但 operator-facing surface 還在主 blocker 卡片漏出 raw machine token，會把「已知 toxic q15 bucket」重新包裝成像內部 debug 工具，而不是產品化執行面。
- 這種問題如果不修，使用者看到的是正確資料配錯誤語言，等同 blocker truth 仍未真正落地。

### I｜意義洞察
1. **這輪 root cause 不是模型或資料，而是 payload-derived prose 繞過 shared humanizer。**
2. **同一個 blocker 必須在 Dashboard / Execution / Strategy Lab 用一致 operator copy 呈現，否則會形成 UI 層 split-brain。**
3. **修 shared humanizer + 路由摘要行，比逐頁手改文案更接近產品契約修復。**

### D｜決策行動
- **Patch**：補齊 toxic bucket / deployment guardrail / regime-gate / routing prose 的 humanizer；同步把 `/execution`、`/execution/status`、`/lab` 的 regime/gate/bucket 摘要改成中文 operator copy。
- **Verify**：用 pytest + frontend build + browser 三重驗證，確認主 blocker 卡片不再漏 `exact_live_lane_toxic_sub_bucket_current_bucket`、`toxic sub-bucket`、`regime gate`、`blocks trade`。
- **Next gate**：回到真正的 P0 —— toxic q15 bucket root cause 與 1000-row bull concentration pocket；如果下一輪 artifact 或 UI 再把 support closure 誤讀成 deployment closure，就把這條 lane 升級回 blocker-first governance regression。
