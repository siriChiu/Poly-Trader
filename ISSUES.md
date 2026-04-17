# ISSUES.md — Current State Only

_最後更新：2026-04-17 14:12 UTC_

只保留目前有效 blocker；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前產品化事實
- Fast heartbeat 最新實測：Raw=30640、Features=22058、Labels=61800
- Canonical target：`simulated_pyramid_win`
- Global IC：14/30 pass；TW-IC：29/30 pass
- Live predictor：`signal=HOLD`、`regime_gate=ALLOW`、`structure_bucket=ALLOW|base_allow|q65`、`entry_quality=0.4813 (D)`、`allowed_layers=0`
- `q35_scaling_audit` 已產品化為 **快路徑短路**：當 current live row 不在 q35，或 runtime 先被 circuit breaker 擋下時，直接輸出 reference-only / blocker artifact，不再把 q35 當成當前 live blocker 主敘事，也不再在 fast heartbeat 白白燒掉 heavy 歷史分析時間。

---

## Open Issues

### P0. Recent canonical distribution pathology 仍未閉環
**現況**
- `recent_drift_report` 在 fast heartbeat 仍 timeout（30s），但 fallback artifact 持續顯示 recent 500 rows 為 bull-concentrated `distribution_pathology`
- 目前 machine-read 摘要：recent 500 win_rate≈0.814、dominant_regime≈bull 99%+、compressed features=10、spot_long_win_rate≈0.028

**風險**
- 會讓 live calibration / decision-quality scope 被病態 recent slice 汙染
- heartbeat 仍需依賴 timeout 後 fallback artifact，而不是 fast-safe freshly refreshed artifact

**下一步**
- 先把 `recent_drift_report.py` 做成 fast-safe（縮算、快取或明確 serial budget 內完成）
- 直接追 `target-path + feature compression + regime concentration` 的 root cause，而不是只重報 drift 數字

### P0. Current live bucket 已切到 `ALLOW|base_allow|q65`，但 exact support 仍為 0
**現況**
- `q35` 已不是 current live bucket；q35 artifact 現在正確降級成 reference-only
- 真正當前 blocker 變成：current live q65 exact support 不足，`unsupported_exact_live_structure_bucket_blocks_trade`
- Live drilldown 目前給出的可操作根因：`best_single_component=feat_4h_bias50`、`remaining_gap_to_floor≈0.0687`

**風險**
- 若還沿用舊 q35 敘事，會修錯 lane
- runtime / docs / operator 可能把 reference-only q35 artifact 誤當 current blocker

**下一步**
- 把 support-aware governance 完全切到 current q65 bucket
- 所有 probe / audit / docs 都以 current bucket 為主，不再把 q35 當主線 blocker

### P0. Fast governance lane 仍有 3 個 timeout blocker
**現況**
- `feature_group_ablation.py` timeout（20s）
- `bull_4h_pocket_ablation.py` timeout（20s）
- `hb_leaderboard_candidate_probe.py` timeout（20s）
- 目前 fast heartbeat 仍可閉環，但這 3 條 lane 仍靠 timeout + 舊 artifact fail-soft

**風險**
- operator 看到的是 stale governance artifact，不是本輪新鮮證據
- fast cron 預算被 governance scripts 吃掉，壓縮真正 P0 runtime blocker 的處理空間

**下一步**
- 比照本輪 q35 audit，替這 3 條 lane 補齊「current-context short-circuit / semantic cache reuse / budgeted refresh」
- 目標是 fast heartbeat 不再把 timeout 當正常路徑

### P1. Model governance split 仍在，但不能誤判成 parity drift
**現況**
- `feature_group_ablation` 仍建議 `core_only`
- train 側仍走 `core_plus_macro`
- leaderboard probe 顯示：`dual_role_governance_active`

**風險**
- 若 current live bucket support 尚未補齊，就太早把主問題改寫成 leaderboard/profile parity

**下一步**
- 先解 current live bucket support / runtime blocker
- 再處理 leaderboard / production profile 的治理收斂

### P1. Sparse-source auth / archive blocker 仍存在
**現況**
- 8 個 blocked features 尚未解除
- `fin_netflow` 仍是 `auth_missing`（缺 `COINGLASS_API_KEY`）

**風險**
- coverage / feature maturity 仍停在 blocked 或 research-only

**下一步**
- auth blocker 與 historical export/backfill 繼續分開治理
- 但優先順序低於 current live runtime blocker 與 fast governance timeout

---

## Not Issues
- 不是再把 q35 calibration 當 current live 主 blocker
- 不是透過降低 trade floor / gate 假性增加交易
- 不是先美化報表而忽略 fast artifact freshness

---

## Current Priority
1. 修掉 `recent_drift_report` fast-timeout，對 recent pathology 做真 root-cause 閉環
2. 把 support / blocker 主線切到 current live `ALLOW|base_allow|q65`
3. 清掉 fast governance lane 的 3 個 timeout（feature ablation / bull pocket / leaderboard probe）
