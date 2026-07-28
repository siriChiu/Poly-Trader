# Poly-Trader 個人策略放行與不確定性分級政策

_狀態：Active — `owner_approved_personal_use`_

## 目的

本政策把過去混在一起的三件事拆開：

1. **策略研究證據**：OOS、walk-forward、樣本數、exact-bucket support、fold dispersion。
2. **擁有者風險決策**：Kazuha 是否接受統計不確定性，將指定策略放行供個人使用。
3. **技術執行安全**：exact model binding、signed permit、bounded canary、stale quote、防重複下單、曝險上限與 kill switch。

固定樣本門檻不再是個人策略放行的永久二元阻塞點；它改為 evidence tier 與部位上限的輸入。技術執行安全仍維持 fail-closed，且不可被 owner approval 覆蓋。

## 已核准策略

| 欄位 | 值 |
|---|---|
| Decision ID | `poly-trader-personal-release-2026-07-19` |
| 核准者 | Kazuha |
| Model | `logistic_regression` |
| Feature profile | `current_full` |
| Regime | `all` |
| Top-K | `top_1pct` |
| Release status | `owner_approved_personal_use` |
| Statistical gate policy | `advisory_with_uncertainty_sizing` |

最新重建證據：

- OOS ROI：`24.65%`
- 勝率：`68.97%`
- Profit Factor：`4.3797`
- 最大回撤：`4.78%`
- Worst fold ROI：`+9.94%`
- 策略交易樣本：`29`
- current exact-support：`34/50`
- evidence tier：`caution`
- evidence score：`0.63`
- full evidence 前建議上限：**第一層**

以上數值是歷史／模擬證據，不是獲利保證。

## 決策規則

### Statistical evidence — advisory

下列條件在 owner-approved 個人策略上改為警示：

- `min_trades_not_met`
- `support_route_not_deployable`
- `under_minimum_exact_live_structure_bucket`
- `unsupported_exact_live_structure_bucket`

它們會：

- 降低 `evidence_tier`
- 限制 `recommended_max_layers`
- 保留完整 evidence snapshot 與警告
- 不因 sliding-window bucket 的樣本數升降而撤銷已核准策略

它們不會再把工作主線改回「被動累積到 50 筆」。長期無進展應觸發模型、特徵、分桶、驗證方法或 runtime binding 的可操作改善。

### Strategy hard-risk evidence

Owner approval 不會把明顯失敗的研究證據偽裝成可用策略。最大回撤超標、Profit Factor 不足、負向 worst fold 等 hard-risk failure 仍會使新候選無法取得 owner-approved release。

已核准策略只有在 owner 明確撤銷或策略版本／selector 改變時才改變 release state；即時技術事故只阻塞執行，不默默撤銷策略 release。

### Execution safety — mandatory

下列技術 gate 不可 override：

- runtime 必須綁定到同一份 fitted model、feature schema 與 checksum
- live order 必須有 signed、short-lived、single-use execution permit
- bounded live-canary policy 與 symbol-specific quantity cap
- stale quote／market-data freshness
- idempotency 與防重複下單
- 曝險、資金與部位上限
- kill switch
- venue adapter、credentials boolean 與 order-lifecycle reconciliation

## 目前 execution 狀態

```text
strategy_release_status = owner_approved_personal_use
strategy_release_ready  = true
statistical_gate_blocking = false
evidence_tier = caution
recommended_max_layers = 1
runtime_binding_verified = false
deployment_blocker = owner_approved_strategy_binding_required
```

因此，**策略已放行，但 live runtime 尚未放行**。現在的可操作待辦是建立並驗證 exact fitted Logistic Regression artifact binding，而不是等待 support 從 34 變成 50。

在 binding 完成前：

- paper／shadow 可繼續驗證
- 真實買入／加倉維持 fail-closed
- 減風險路徑與 kill switch 不受影響

## Machine-readable surfaces

- `config.yaml > strategy_release`
- `data/high_conviction_topk_oos_matrix.json`
- `data/live_predict_probe.json`
- `/api/model-leaderboard` 的 `high_conviction_topk`
- `/api/status` 的 runtime closure fields
- Strategy Lab 高信心 OOS 區塊

主要欄位：

- `owner_approved`
- `owner_approval_decision_id`
- `strategy_release_status`
- `strategy_release_ready`
- `statistical_gate_blocking`
- `statistical_warnings`
- `technical_execution_blockers`
- `hard_gate_failures`
- `support_evidence_ratio`
- `model_evidence_ratio`
- `evidence_score`
- `evidence_tier`
- `recommended_max_layers`
- `runtime_binding_verified`
- `technical_execution_gates_required`

## 重建與驗證

```bash
python scripts/hb_predict_probe.py
python scripts/topk_walkforward_precision.py
python -m pytest tests/test_personal_release_policy.py -q
python -m pytest tests/test_execution_service.py -q
```

Heartbeat／current-state docs 必須優先顯示 `owner_approved_personal_use`，並把 current support 寫成統計警示；不得再把「補到固定 50 筆」描述為唯一下一步。
