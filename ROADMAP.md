# ROADMAP.md — Current Plan Only

_最後更新：2026-05-02 09:14:43 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成（本輪）

- **Heartbeat #1166 diagnostics refresh**：collect 成功，`Raw=32559 / Features=23977 / Labels=65737`，`simulated_pyramid_win=56.77%`，兩年歷史覆蓋 `ok=True`。
- **High-conviction Top-K runtime truth productization**：
  - API compact rows 現在輸出 row-level `signal / allowed_layers / execution_guardrail_reason / source_live_probe_generated_at / live_truth_source_artifact`。
  - Strategy Lab 高信心 OOS Top-K 部署門檻面板會直接顯示「即時訊號 / 可用層 / 原因」，讓 operator 看到 ROI/win-rate 同時也看到 live blocker。
  - Regression coverage 已補在 `tests/test_model_leaderboard.py` 與 `tests/test_frontend_decision_contract.py`。
- **Verification**：high-conviction pytest、frontend contract pytest、runtime probe、`npm run build` 均通過。

---

## 主目標

### 目標 A — 保持 current-live exact-support blocker 為唯一部署真相
**目前真相**
- `signal=ABSTAIN` / `allowed_layers=0` / `deployment_blocker=under_minimum_exact_live_structure_bucket`。
- `current_live_structure_bucket=CAUTION|base_caution_regime_or_bias|q35`，exact support `20/50`，gap `30`。

**成功標準**
- Dashboard、Strategy Lab、Execution Console、`/api/status`、`/api/trade` 都以 `under_minimum_exact_live_structure_bucket` fail-closed；buy/add exposure 不可繞過 blocker，reduce/sell risk-off 可保留。

### 目標 B — 把 high-conviction Top-K 從研究 winner 變成可拒單部署 gate
**目前真相**
- `data/high_conviction_topk_oos_matrix.json`：`rows=24` / `deployable_rows=0` / `risk_qualified_rows=6` / `runtime_blocked_candidate_rows=6`。
- Nearest candidate：`logistic_regression top_2pct`，`oos_roi=0.9324`、`win_rate=86.21%`、`profit_factor=19.8864`、`max_drawdown=0.022`、`worst_fold=0.2068`、`trades=58`，但因 current-live support `20/50` 仍 `not_deployable`。
- 本輪 API/UI 已把 row-level `ABSTAIN / allowed_layers=0 / under_minimum_exact_live_structure_bucket` 顯示出來。

**成功標準**
- `/api/models/leaderboard.high_conviction_topk` 與 Strategy Lab 必須同時顯示 OOS/風控結果與 live guardrail；`runtime_blocked_oos_pass` 不得被標成 deployable。
- 只有當 OOS gate、drawdown、worst-fold、current-live support、venue runtime proof 全部通過，才允許從影子驗證進入小流量部署候選。

### 目標 C — q35 formula / base-stack redesign 必須與 execution gate 分離
**目前真相**
- q35 audit：`bias50_formula_may_be_too_harsh`；base-stack redesign 可跨 score floor，但 runtime 仍 `allowed_layers=0`。

**成功標準**
- 分數改善只能標成 score-only evidence；exact-support 與 execution guardrail 未通過前不得當 deployment closure。

### 目標 D — 補齊 venue / sparse-source production proof
**目前真相**
- `fin_netflow` 仍因 `COINGLASS_API_KEY` 缺失而 `source_auth_blocked`。
- Binance/OKX 仍缺 live credential、order ack lifecycle、fill lifecycle runtime proof。

**成功標準**
- CoinGlass auth 可用且 successful snapshots 開始累積。
- 每個 venue 都有 machine-readable credential、ack、fill/reconciliation proof；未完成前 UI 持續顯示 blocker。

---

## 下一輪 Gate

1. **q35 support accumulation gate**：確認 current bucket rows 是否從 `20/50` 增加；未增長則追 feature/label/current bucket pipeline。
2. **Top-K freshness + live overlay gate**：重跑 Top-K matrix 或保持 freshness；確認 API/UI rows 繼續輸出 `signal / allowed_layers / execution_guardrail_reason`。
3. **Execution guardrail gate**：用 `/api/trade` regression 確認 buy/add exposure 在 blocker active 時仍 409 fail-closed。
4. **Venue proof gate**：為 Binance/OKX 補最小 credential + order lifecycle proof。
5. **Source auth gate**：配置 CoinGlass auth 後重新觀察 `fin_netflow` coverage。

---

## 成功標準摘要

- current-live blocker 清楚且唯一：`under_minimum_exact_live_structure_bucket`。
- current-live bucket support truth 維持可見：`20/50`, gap `30`。
- High-conviction Top-K：OOS winner 必須同時顯示 live runtime truth；未過 support/venue gates 前只能 shadow / observe。
- Venue/source blockers 持續可見，不得被 ROI 或 leaderboard success 掩蓋。
