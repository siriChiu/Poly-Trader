# ROADMAP.md — Current Plan Only

_最後更新：2026-04-30 08:12:12 CST_

只保留目前計畫；每輪 heartbeat / productization run 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成

- **full heartbeat #1143 已完成 collect + diagnostics refresh**
  - `Raw=32495 / Features=23913 / Labels=65598`
  - 歷史覆蓋：`2y_backfill_ok=True`，raw/features/labels 均覆蓋 2024-04 起算的兩年視窗。
  - `simulated_pyramid_win=56.73%`
- **current-live blocker truth 已收斂到 exact-support shortage**
  - `deployment_blocker=unsupported_exact_live_structure_bucket`
  - `current_live_structure_bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `gap=50`
  - `support_route_verdict=insufficient_support_everywhere` / `support_governance_route=exact_live_lane_proxy_available`
- **Execution Console / `/api/trade` 操作入口已 fail-closed**
  - 同步中或部署阻塞期間：買入 / 加倉 / 啟用自動模式 disabled；減碼 / 賣出風險降低、切手動、診斷、refresh 保留。
  - direct `POST /api/trade` buy/add exposure 依 current-live blocker 回 409；risk-off sides 保留。
- **operator-facing route/governance copy 本輪補強完成**
  - `runtimeCopy.ts` 已新增 `insufficient_support_everywhere`、`exact_live_lane_proxy_available` 的支持路徑 / 治理路徑 / runtime summary 繁中化。
  - browser `/execution` 驗證：raw `insufficient_support_everywhere` 與 `exact_live_lane_proxy_available` 不再出現在畫面文字；顯示 `所有支持路徑仍不足`、`已有精準路徑近似樣本`。
- **high-conviction Top-K OOS gate 已可視化但維持 no-deploy**
  - `data/high_conviction_topk_oos_matrix.json` 有 risk-qualified candidates；`deployable_rows=0`，current-live support gate 未過前仍 fail-closed。

---

## 主目標

### 目標 A：維持 current-live exact-support blocker 作為唯一 deployment blocker
**目前真相**
- `deployment_blocker=unsupported_exact_live_structure_bucket`
- `bucket=CAUTION|structure_quality_caution|q15` / `support=0/50` / `gap=50`
- `support_route_verdict=insufficient_support_everywhere` / `support_governance_route=exact_live_lane_proxy_available`

**成功標準**
- `/`、`/execution`、`/execution/status`、`/lab`、probe、drilldown、docs 都一致顯示 current-live exact-support shortage。
- UI / API 不得把 breaker 舊敘事、venue metadata OK、proxy/reference rows、或 Top-K ROI winner 誤當 deployment closure。

### 目標 B：讓 Execution surfaces 成為 production-grade operator cockpit
**目前真相**
- Execution Console 已 fail-closed；本輪 route/governance raw token humanization 已補強。
- Venue readiness 仍 metadata-only / public-only；Binance 缺 live credential/order/fill proof，OKX 停用。

**成功標準**
- 操作員先看到部署阻塞與可/不可操作範圍，再看到 venue metadata 與治理背景。
- Runtime summary、support route、governance route、support progress、venue proof state 全部使用繁中 humanized copy，不外洩 raw internal token。
- 買入 / 加倉 / 啟用自動模式在 no-deploy 時 disabled + API 409；減碼 / risk-off 保留。

### 目標 C：把 high-conviction Top-K OOS 從研究指標推向可拒單部署 gate
**目前真相**
- Matrix 已產出 `rows=24` / `risk_qualified_rows=6` / `deployable_rows=0` / `runtime_blocked_candidates=6`。
- nearest candidate 離線表現佳，但 live support / venue proof 未過。

**成功標準**
- `/api/models/leaderboard.high_conviction_topk` 與 Strategy Lab 持續揭露：OOS ROI、win rate、profit factor、max drawdown、worst fold、trade count、support route、deployable verdict、gate failures。
- 即使離線 pass，只要 current-live support / venue proof 未過，就只能標 `runtime_blocked_oos_pass` / 模擬觀察 / 影子驗證。

### 目標 D：維持 source / venue blockers 與 docs automation 一致
**目前真相**
- `blocked_sparse_features=8`；fin_netflow auth missing；venue live proof 缺口仍有效。
- docs overwrite sync 已是 heartbeat contract；本輪手動補丁後也已覆蓋 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`。

**成功標準**
- current-state docs 只保留最新 truth，並與 live artifacts、probe、API、UI 同輪對齊。
- 若 source/venue blockers 仍未解，不得讓 UI copy 或 leaderboard 暗示 live-ready。

---

## 下一輪 gate

1. **Exact-support blocker gate**
   - 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、browser `/execution`、browser `/execution/status`、browser `/lab`。
   - 升級 blocker：q15 rows/gap/support route 從 top-level surfaces 消失，或 current-live blocker 被其他敘事覆蓋。
2. **Operator copy / runtime token hygiene gate**
   - 驗證：`python -m pytest tests/test_frontend_decision_contract.py -q`、`cd web && npm run build`、browser DOM text scan。
   - 升級 blocker：`insufficient_support_everywhere`、`exact_live_lane_proxy_available`、`runtime/calibration`、`none`、或 venue raw status 在 operator-facing surfaces 外洩。
3. **High-conviction OOS no-deploy gate**
   - 驗證：`python -m pytest tests/test_model_leaderboard.py tests/test_frontend_decision_contract.py -k high_conviction -q`、browser `/lab`。
   - 升級 blocker：ROI winner 未通過 support / venue proof 就被標 deployable。
4. **Venue/source proof gate**
   - 驗證：`data/execution_metadata_smoke.json`、`/api/features/coverage`、browser `/execution/status`。
   - 升級 blocker：metadata OK 被誤寫成 live trading proof，或 source auth/history blocker 從 UI/docs 消失。

---

## 成功標準

- current-live blocker 清楚且唯一：**unsupported_exact_live_structure_bucket**。
- q15 current-live truth 維持：**0/50 + insufficient_support_everywhere + exact_live_lane_proxy_available**。
- Execution surfaces fail-closed 且中文 humanized；raw route/governance tokens 不外洩。
- high-conviction OOS candidates 在 live support / venue proof 未過前仍 no-deploy。
- heartbeat/productization run 每輪完成：facts → decision → patch → verify → docs overwrite sync → next gate。
