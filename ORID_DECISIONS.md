# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-21 06:42:14 CST_

---

## 心跳 #20260421-0642 ORID

### O｜客觀事實
- current-live blocker 仍是 `under_minimum_exact_live_structure_bucket`；`current_live_structure_bucket=CAUTION|structure_quality_caution|q35` / `support=12/50` / `gap=38` / `support_route_verdict=exact_bucket_present_but_below_minimum`。
- recent canonical window 500 仍是 `distribution_pathology`：`win_rate=12.8%` / `dominant_regime=bull(83.8%)` / `avg_quality=-0.1547` / `avg_pnl=-0.0056` / `alerts=label_imbalance,regime_shift`。
- Browser QA 看到 `/execution/status` 先前會把 `fresh / healthy / public-only` 與 `blocked` 混在同一層，容易讓 operator 快速掃描時誤讀成「系統整體沒問題」。
- 本輪已修正 `/execution/status`：加入 `overall execution posture`、把 `healthy + no_runtime_order` 降成 `limited evidence`、把私有憑證缺失改成 `metadata-only snapshot / metadata-only`、並把 `fresh / healthy` 明確定義成 observability-only。
- 驗證已通過：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/execution/status`、browser console 無 JS errors。

### R｜感受直覺
- 如果 diagnostics page 把 `fresh / healthy` 與 `blocked` 放成同級訊號，operator 很容易在錯的情緒下做錯介入判斷。
- 這不是單純 copy polish；它會直接影響「現在可不可以動 Bot / 放不放行」的現場判斷品質。

### I｜意義洞察
1. **Execution diagnostics 的第一任務不是報綠燈，而是避免假綠燈。** `fresh` 只能代表 observability 正常，不能蓋掉 current-live blocker。
2. **`healthy` 但 `no_runtime_order` 不等於「已驗證無誤」。** 若沒有 runtime order 可核對，正確語義應是 `limited evidence`，不是完整 reconciliation closure。
3. **帳戶可見性必須說人話。** 在沒有私有憑證時，operator 需要看到的是 `metadata-only snapshot`，而不是模糊的 `review` 或只剩 technical detail。

### D｜決策行動
- **Owner**：execution diagnostics / blocker-visibility lane
- **Action**：把 `/execution/status` 固定為 blocker-first posture；保留 exact-support shortage 作為唯一 current-live blocker，並將 observability、reconciliation coverage、account visibility 明確降級成次級訊號。
- **Artifacts**：`web/src/pages/ExecutionStatus.tsx`、`tests/test_frontend_decision_contract.py`、`ARCHITECTURE.md`、`ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`
- **Verify**：`pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/execution/status`
- **If fail**：只要 `/execution/status` 再次讓 `fresh / healthy / venue` 文案與 current-live blocker 同級，或把 `no_runtime_order` 包裝成完整驗證，就把這條 lane 升級回 blocker-truth regression。
