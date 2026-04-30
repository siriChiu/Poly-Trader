# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-04-30 08:12:12 CST_

---

## 心跳 #1143 + 本輪產品化補丁 ORID

### O｜客觀事實

- full heartbeat #1143 完成：`Raw=32495 / Features=23913 / Labels=65598`，`simulated_pyramid_win=56.73%`，兩年歷史覆蓋確認 OK。
- current-live deployment blocker：`unsupported_exact_live_structure_bucket`。
- current live bucket：`CAUTION|structure_quality_caution|q15`；exact support `0/50`，gap `50`。
- route truth：`support_route_verdict=insufficient_support_everywhere` / `support_governance_route=exact_live_lane_proxy_available`。
- support progress：`semantic_rebaseline_under_minimum`，basis=`legacy_or_different_semantic_signature`，legacy reference=`53/50@20260419b`，只能作參考。
- recent canonical diagnostics：window `100`，win rate `24.0%`，dominant regime `chop(87.0%)`，alerts=`regime_shift`。
- venue/source truth：Binance 仍 metadata-only / public-only 且缺 live credential、order ack、fill lifecycle proof；OKX 停用；fin_netflow 仍 source_auth_blocked。
- 本輪產品化補丁：`web/src/utils/runtimeCopy.ts` 新增 `insufficient_support_everywhere` 與 `exact_live_lane_proxy_available` 的支持路徑 / 治理路徑 / runtime summary 繁中化；`tests/test_frontend_decision_contract.py` 補上 contract assertion。
- 驗證結果：`tests/test_frontend_decision_contract.py` 76 passed；`web npm run build` 成功；browser `/execution` DOM scan 確認 raw `insufficient_support_everywhere` / `exact_live_lane_proxy_available` 不再外洩，中文 `所有支持路徑仍不足` 與 `已有精準路徑近似樣本` 出現。

### R｜感受直覺

- 最大產品風險不是資料沒刷新，而是操作員看到 raw route token 或把治理/近似樣本誤讀成可部署。
- `0/50` exact support 與 `exact_live_lane_proxy_available` 必須同時呈現：前者是阻塞真相，後者只是治理參考，不可混成 deployment closure。
- High-conviction OOS rows 離線表現雖佳，但 current-live support / venue proof 未過前，產品上只能是影子驗證候選。

### I｜意義洞察

1. **support route label 是 production UX contract**：raw route token 一旦出現在 runtime summary，operator 會把控制平面字串誤讀成交易決策；必須集中在 `runtimeCopy.ts` humanize。
2. **governance route ≠ deployment route**：`exact_live_lane_proxy_available` 代表可供治理參考，不代表 q15 exact bucket support 已滿。
3. **fail-closed 必須同時覆蓋 UI 與 API**：UI disabled 不足夠；direct `/api/trade` 也要依 current-live blocker 409。
4. **docs overwrite 是閉環證據**：補丁後若 ISSUES/ROADMAP/ORID 沒同步，下一輪 heartbeat 仍可能回到舊敘事。

### D｜決策行動

- **Owner**：Execution / operator runtime copy lane。
- **Action**：保持 `unsupported_exact_live_structure_bucket` 為唯一 current-live deployment blocker；所有支持路徑 / 治理路徑 / runtime summary 都要 humanized，且不能用 proxy/legacy/reference rows 放行部署。
- **Patch**：
  - `web/src/utils/runtimeCopy.ts`：新增 `insufficient_support_everywhere`、`exact_live_lane_proxy_available` route/governance/runtime detail mappings。
  - `tests/test_frontend_decision_contract.py`：鎖定 `insufficient_support_everywhere → 所有支持路徑仍不足` contract。
  - `ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md`：覆蓋為最新 current-state truth。
- **Verify**：`python -m pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser `/execution` DOM raw-token scan。
- **Next gate**：下一輪先跑 full heartbeat/probe，再驗證 `/`、`/execution`、`/execution/status`、`/lab` 都不洩漏 raw route/governance token，且 high-conviction OOS candidates 在 exact support / venue proof 未過前仍 no-deploy。
