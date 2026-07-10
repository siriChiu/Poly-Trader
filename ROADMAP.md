# ROADMAP.md — Current Plan Only

_最後更新：2026-07-10 04:18:11 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 當前結論（2026-07-10）

- **最新 runtime truth 取代 2026-06-06 舊 artifact**：`data/live_predict_probe.json` / Top-K 仍記錄舊分桶 `BLOCK|bias200_below_min|q00 = 131/50`，但目前 `/api/status.execution.live_runtime_truth` 的當前分桶已漂移到 `CAUTION|base_caution_regime_or_bias|q85 = 0/50`。
- **根因不是單純 UI bug**：舊 `current_live_support_gate` 把產品 readiness 綁死在「當前 exact bucket ≥50 rows」。市場 regime / entry-quality bucket 一漂移，support 會直接歸零，形成「等一年也可能重置」的產品化死循環。
- **安全邊界維持不變**：live buy/add、加倉、自動風險進攻下單仍 fail-closed；proxy / broad / semantic support 不可包裝成 live deployment proof。
- **產品化方向改為多證據 readiness**：strict exact support 只作 live-canary prerequisite；當 exact support 不足時，產品不應只顯示「等待 50 筆」，而要自動轉入 paper/shadow observation、cost-aware edge、venue dry-run、24h outcome evidence 與 reduce-only safe lanes。

---

## 已完成 / 本輪落地

- **Roadmap 已同步最新研究結論與 runtime root cause**
  - 現行阻塞：`deployment_blocker=unsupported_exact_live_structure_bucket`。
  - 當前分桶：`CAUTION|base_caution_regime_or_bias|q85`。
  - exact support：`0/50`，gap `50`。
  - 舊 `BLOCK|bias200_below_min|q00 = 131/50` 僅作歷史 artifact / stale reference，不可覆蓋 runtime truth。
- **Execution readiness contract 開始改造**
  - 新增 `current_lane_actionability_gate` 作為 operator-facing 主 gate。
  - 保留 `current_live_support_gate` legacy key 相容，但改為 `legacy exact subgate` 語意。
  - `current_lane_actionability_gate.sub_gates[]` 拆成：
    1. `strict_exact_support_subgate`：live-canary 前置條件，不足時 live buy/add blocked。
    2. `shadow_evidence_subgate`：paper/shadow observation 是否可用。
    3. `cost_aware_edge_subgate`：forecast edge 是否大於 fee + spread + slippage + volatility/drawdown buffer；未有 forecast/cost inputs 時 fail-closed。
  - blocking order 從單點 `current_live_support_gate` 轉為 `current_lane_actionability_gate`，避免 UI 只剩「等 50 筆」。
- **Execution Console UI contract 開始顯示新語意**
  - readiness cards 會顯示 `當前 lane 可行動 gate`。
  - 子 gate 顯示 `strict exact / shadow evidence / cost-aware edge`，讓 operator 看到 live blocker 與 paper/shadow lane 是不同層級。
- **Cost-aware inputs plumbing 已接上第一版 production default**
  - `execution/config.py` 新增 `DEFAULT_COST_AWARE_EDGE_CONFIG` 與 `resolve_cost_aware_edge_config()`，支援 root / trading legacy / `execution.cost_aware_edge` override。
  - `config.yaml.execution.cost_aware_edge` 預設為 `fee 5 + spread 3 + slippage 2 + volatility buffer 5 + drawdown buffer 0 = required_edge_bps 15`。
  - `/api/status.cost_aware_edge`、`execution.cost_aware_edge`、`execution_surface_contract.cost_aware_edge`、`execution.live_runtime_truth.cost_aware_edge` 都會 expose 同一份 machine-readable cost contract。
  - `cost_aware_edge_subgate` 現在即使缺 forecast，也會顯示 `required_edge_bps=15` 與完整 `cost_components_bps`；缺 forecast 仍 fail-closed。
- **Cost-aware OOS 反事實回測已完成，結論是 15bps gate 對 Top-K 非約束**
  - 新增 `scripts/cost_aware_gate_backtest.py`，輸出 `data/cost_aware_gate_backtest.json`。
  - 方法：沿用 Top-K walk-forward 前 4 folds；每個 fold 只用訓練期 score→PnL 校準 `forecast_edge_bps`，再比較 baseline Top-K vs Top-K + `forecast_edge_bps > 15bps`。
  - 結果：12/12 Top-K rows 全部 `no_effect_non_binding`；所有高信念候選的最低 forecast edge 都高於 15bps，filter retention = 100%，`net_roi_delta=0`。
  - 解讀：不是乾等，因為 paper/shadow Top-K 在扣 15bps 後仍有正 OOS net ROI；但也不能宣稱 cost-aware gate 本身改善 PnL，因為它目前沒有過濾任何 Top-K trade。
  - 門檻掃描：提高到約 250bps 才開始有約束；最佳 binding row (`xgboost top_2pct`) 從 58 筆降到 55 筆，回撤改善 `-0.0171`、單筆 net +4.87bps，但總 net ROI 少 `-0.008`，屬風險品質 tradeoff，不是總收益改善。
- **API fail-closed smoke 已補 proof**
  - in-process route smoke 驗證：`wait` 回 200 no-order、live `buy` 回 409 `current_live_deployment_blocker` 且沒有呼叫 `ExecutionService.submit_order`、`shadow_buy` 只進 paper/dry-run，`live_order_submitted=false`。

---

## 主目標

### 目標 A：把 `current_live_support_gate` 死循環拆成可產品化 readiness

**目前真相**
- runtime current bucket：`CAUTION|base_caution_regime_or_bias|q85`
- exact support：`0/50`，gap `50`
- blocker：`unsupported_exact_live_structure_bucket`
- live buy/add：blocked
- paper/shadow：只能作 observation / dry-run / outcome evidence，不可當 live clearance

**成功標準**
- `/api/execution/overview.execution_readiness.gates[]` 同時輸出：
  - `current_lane_actionability_gate`
  - `current_live_support_gate` legacy alias
  - `strict_exact_support_subgate`
  - `shadow_evidence_subgate`
  - `cost_aware_edge_subgate`
- UI 明確說明：strict exact 0/50 是 **live-canary blocker**，不是整個產品停工；下一步是 paper/shadow + cost-aware evidence。
- live buy/add、加倉、自動風險進攻下單仍全部 fail-closed。

### 目標 B：導入 cost-aware execution filter 作為 paper/shadow risk-on 前置

**研究依據**
- 2025/2026 crypto ML trading 研究顯示：扣除交易成本後，naive sign-based 策略容易崩；只有 forecast magnitude 大於交易成本門檻時交易，才可能維持 ROI / Sharpe。

**成功標準**
- `cost_aware_edge_subgate` 必須機器可讀：
  - `forecast_edge_bps`
  - `required_edge_bps`
  - `cost_components_bps.fee_bps / spread_bps / slippage_bps / volatility_buffer_bps / drawdown_buffer_bps`
  - `passed=false` when forecast is missing or forecast edge <= cost threshold
- paper/shadow 風險進攻 candidate 只有在 `shadow_evidence_subgate=true` 且 `cost_aware_edge_subgate=true` 時才可標為 candidate-ready。
- 沒有 forecast 時只能 observation，不可把 OOS ROI proxy 當 live 或 paper risk-on clearance。

### 目標 C：下一波 feature roadmap 聚焦 microstructure + derivatives flow，不先堆黑箱模型

**優先導入**
1. LOB/order-flow features：`orderbook_imbalance_l1/l5`、`spread_bps`、`depth_50bps/200bps`、`microprice_deviation`、`trade_flow_imbalance`、`liquidity_stress_score`。
2. Derivatives / positioning regime：`funding_rate_zscore`、`open_interest_change`、`perp_basis_apr`、`liquidation_imbalance`。
3. ETF / stablecoin / institutional flow 作為 4H/daily liquidity regime，不作 1m entry trigger。

**暫不導入 production**
- LOB Transformer / RL / LLM trading agent：先留 research，不進 live gates。

---

## 下一輪 gate

1. **把 cost-aware 從 non-binding 15bps proxy 推進到動態 edge gate**
   - 驗證：`data/cost_aware_gate_backtest.json.summary.verdict` 不再停在 `cost_gate_non_binding_on_topk`；runtime `forecast_edge_bps` 來自 live microstructure/LOB 或校準模型，而不是只用 static 15bps config。
   - 升級 blocker：若 15bps 繼續 100% retention，則 cost-aware 只能當成本揭露與 fail-closed contract，不可包裝成改善 PnL 的 filter。
2. **建立 LOB/order-flow 最小 contract artifact**
   - 驗證：新增 artifact 或 status payload 欄位能列出 `orderbook_imbalance_l1/l5 / depth_50bps / microprice_deviation / trade_flow_imbalance / liquidity_stress_score` 的來源、freshness、coverage；缺資料時 fail-closed 到 observation。
   - 升級 blocker：若 LOB 資料缺失但 UI 暗示已是 microstructure-aware。
3. **Browser/API 實機 smoke**
   - 驗證：使用正確 backend-served dashboard route，確認 `/execution` 顯示 current lane actionability、cost-aware subgate、`order_submission_enabled=false`；直接 API 維持 `wait=200 no-order`、`buy=409`、`shadow_buy=paper/dry-run`。
4. **graphify rebuild / docs current-state sync**
   - 驗證：修改 code 後執行 `venv/bin/python -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"`，並保持 `ROADMAP.md` 與 machine-readable contract 對齊。

---

## 成功標準

- current runtime truth 優先於 stale artifact：`CAUTION|base_caution_regime_or_bias|q85 = 0/50` 不得被舊 `131/50` 覆蓋。
- UI / API 不再把 strict exact support 當成唯一產品路線。
- strict exact support 不足時：live buy/add blocked，但 paper/shadow observation、cost-aware edge 補證、venue dry-run、24h outcome evidence 仍可前進。
- cost-aware gate 缺 forecast 或 forecast edge 未高於 15bps default / runtime cost threshold 時 fail-closed，不用 ROI proxy 假裝 edge 已過。
- 任何 proxy / broad / semantic support 都不能升級成 live deployment proof。
