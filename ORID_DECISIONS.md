# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-05-02 09:14:43 CST_

---

## 心跳 #1166 ORID

### O｜客觀事實
- collect + diagnostics refresh 完成：`Raw=32559 / Features=23977 / Labels=65737`，`simulated_pyramid_win=56.77%`，兩年歷史覆蓋 `ok=True`。
- current live：`signal=ABSTAIN`、`allowed_layers=0`、`deployment_blocker=under_minimum_exact_live_structure_bucket`、`execution_guardrail_reason=under_minimum_exact_live_structure_bucket`。
- current q35 bucket：`CAUTION|base_caution_regime_or_bias|q35`，exact support `20/50`，gap `30`，`support_route_verdict=exact_bucket_present_but_below_minimum`。
- High-conviction Top-K matrix：`rows=24`、`deployable_rows=0`、`risk_qualified_rows=6`、`runtime_blocked_candidate_rows=6`。
- Nearest deployment candidate：`logistic_regression top_2pct`，`oos_roi=0.9324`、`win_rate=86.21%`、`profit_factor=19.8864`、`max_drawdown=0.022`、`worst_fold=0.2068`、`trades=58`；仍因 live support `20/50` 而 `runtime_blocked_oos_pass / not_deployable`。
- 本輪 patch：API compact Top-K rows 與 Strategy Lab row UI 補上 `signal / allowed_layers / execution_guardrail_reason / live truth source`，使 operator 在看高 ROI 候選時也能看到即時不可部署原因。

### R｜感受直覺
- 最危險的產品誤讀不是模型表現差，而是 OOS winner 看起來很強，卻被 operator 誤認為可以立刻部署。
- `86% win_rate` 與 `ROI 0.9324` 必須被 `ABSTAIN / allowed_layers=0 / support 20/50` 同畫面約束，否則 Strategy Lab 會從研究工具變成錯誤下單暗示。

### I｜意義洞察
1. **Productization gate 的本質是可拒單**：好候選要先能被 live support / venue proof 正確拒絕，才有資格逐步走向影子驗證或小流量。
2. **OOS gate 與 live gate 必須同列顯示**：只顯示 ROI/win-rate 會鼓勵錯誤行動；row-level runtime truth 是部署安全契約的一部分。
3. **q35 blocker 仍是 exact-support，不是 scoring closure**：base-stack redesign 可作 score-only 線索，但 support 未達 `50` 前仍不可部署。

### D｜決策行動
- **本輪已決策並完成**：將 High-conviction Top-K row-level live truth productize 到 API 與 Strategy Lab UI；補 regression tests；用 runtime probe 與 build 驗證。
- **維持策略**：所有 `runtime_blocked_oos_pass` rows 只能 shadow / observe；不得標成 deployable。
- **下一步**：
  1. 追 q35 exact bucket support 從 `20/50` 往 `50/50` 累積。
  2. 保持 Top-K matrix freshness，並確保 live overlay 取最新 `data/live_predict_probe.json`。
  3. 補 venue runtime proof 與 CoinGlass auth，否則 production trade gate 不開。
- **驗證證據**：`pytest tests/test_model_leaderboard.py -k high_conviction_topk`、`pytest tests/test_frontend_decision_contract.py -k high_conviction_topk_gate_contract`、runtime probe、`npm run build`。
