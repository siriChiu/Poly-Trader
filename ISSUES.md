# ISSUES.md — Current State Only

_最後更新：2026-04-17 14:52 UTC_

只保留目前有效 blocker；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前產品化事實
- Fast heartbeat 最新實測：Raw=30661、Features=22079、Labels=61805
- Canonical target：`simulated_pyramid_win`
- Global IC：14/30 pass；TW-IC：29/30 pass
- Live predictor：`signal=HOLD`、`regime_gate=ALLOW`、`structure_bucket=ALLOW|base_allow|q65`、`entry_quality=0.5304 (D)`、`allowed_layers=0`
- `q35_scaling_audit` 現在是 **reference-only**；current live blocker 不再是 q35，而是 current q65 lane 的 exact support = 0
- **本輪已修復**：`recent_drift_report.py` 不再因慢查詢拖垮 fast heartbeat；SQLite 現在有 drift/governance 必要的 composite indexes，fresh run 已可在 fast 預算內完成，未變更時可安全 reuse fresh artifact

---

## Open Issues

### P0. Current live `ALLOW|base_allow|q65` exact support = 0，runtime 仍被 unsupported-exact-support 擋下
**現況**
- `current_live_structure_bucket_rows=0`
- `allowed_layers_reason=decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket_blocks_trade`
- `remaining_gap_to_floor=0.0196`
- `best_single_component=feat_4h_bias50`，單點數學上可補 floor，但 **support 未達 deployment 門檻**

**風險**
- runtime / operator surface 仍沒有 current q65 exact evidence 可放行
- 若把研究型 component 調整誤包裝成 deployment patch，會破壞 support-aware guardrail 紀律

**下一步**
- 所有 support / blocker / docs 主線完全對齊 current q65 lane
- 先補 current q65 exact support 或安全 proxy 治理證據，再談 runtime 放寬
- 用 `feat_4h_bias50` 當 component research 主探針，但只保留 reference-only，不能越過 support gate

### P0. Recent canonical pathology 還在，但現在已經有 fresh / reusable drift artifact，不再接受 timeout 當藉口
**現況**
- primary window = recent 500
- alerts = `label_imbalance + regime_concentration + regime_shift`
- win_rate=0.814、dominant_regime≈bull 99.2%
- feature diagnostics：low_variance 10/56、low_distinct 10/56、null_heavy 10/56
- top shifts：`feat_4h_bias20`、`feat_4h_bb_pct_b`、`feat_4h_ma_order`
- new compressed：`feat_dxy`、`feat_vix`

**風險**
- calibration / decision-quality scope 仍可能被 recent bull pocket 汙染
- 若只修 timeout、不追 root cause，heartbeat 仍只是更快地重報 pathology

**下一步**
- 直接沿 fresh drift artifact 追 feature compression / regime concentration / target-path root cause
- 把 recent pathology 的修復物件收斂成可 patch 的 data/runtime contract，而不是只停在統計摘要

### P1. Fast governance lane 仍有 3 個 timeout blocker
**現況**
- `feature_group_ablation.py` timeout（20s）→ fallback artifact age ≈ 7h+
- `bull_4h_pocket_ablation.py` timeout（20s）→ fallback artifact age ≈ 7h+
- `hb_leaderboard_candidate_probe.py` timeout（20s）→ fallback artifact age ≈ 7h+

**風險**
- operator 看到的是 stale governance artifact，不是本輪 fresh evidence
- fast heartbeat 雖已不再被 drift report 卡死，但 governance 主線仍不夠 cron-safe

**下一步**
- 比照 drift lane，替這 3 條 script 補 current-context short-circuit / semantic cache reuse / budgeted refresh
- summary 必須明示 fresh / cached / fallback，不再讓 timeout 成為常態路徑

### P1. Governance split 仍存在，但目前不是主 blocker
**現況**
- leaderboard global winner = `core_only`
- train selected profile = `core_plus_macro`
- probe verdict = `dual_role_governance_active`

**風險**
- 若 current q65 support 尚未補齊，就太早把主線改寫成 profile parity 問題

**下一步**
- 先解 current q65 support / runtime blocker 與 3 條 governance timeout
- exact support 達標後，再決定是否升級成 post-threshold leaderboard sync blocker

### P2. Sparse-source auth / archive blockers 仍存在
**現況**
- 8 個 blocked features 未解除
- `fin_netflow` 仍是 `auth_missing`（缺 `COINGLASS_API_KEY`）

**風險**
- feature maturity 仍有 research / blocked 混雜區

**下一步**
- auth blocker 與 archive/backfill 繼續分開治理
- 優先順序仍低於 current live runtime blocker 與 fast governance timeout

---

## Not Issues
- 不是再把 q35 calibration 當 current live 主 blocker
- 不是 `recent_drift_report` 30s timeout；本輪已解除這個 fast-lane blocker
- 不是直接下調 trade floor / 放寬 gate 來假性製造交易

---

## Current Priority
1. 關閉 current q65 exact-support blocker，讓 runtime / docs / operator surface 完全對齊 current live lane
2. 清掉剩餘 3 條 fast governance timeout（feature ablation / bull pocket / leaderboard probe）
3. 用現在已可快取/快跑的 drift artifact 直接追 recent pathology root cause，而不是只重報數字
