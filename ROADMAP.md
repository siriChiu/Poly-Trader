# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 14:52 UTC_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- Canonical target 已穩定對齊 `simulated_pyramid_win`
- Fast heartbeat collect / IC / live probe / q15/q35 系列 artifact 仍可閉環運作
- `q35_scaling_audit` 已降級成 **reference-only**，不再把非 q35 current row 誤包裝成 current blocker
- **本輪完成：fast drift lane 產品化修復**
  - `database.models.init_db()` 現在會自動補齊 `idx_labels_horizon_timestamp_symbol`、`idx_features_timestamp_symbol`、`idx_raw_market_timestamp_symbol`
  - `recent_drift_report.py` fresh run 已恢復到 fast 預算內，可在 fast heartbeat 中通過或安全 reuse fresh artifact
  - 新增 regression test，鎖住 SQLite composite index contract，避免 drift lane 再退化回 30s timeout

---

## 主目標

### 目標 A：關閉 current live `ALLOW|base_allow|q65` support blocker
**重點**
- 所有 support / blocker / docs 主線只跟 current q65 live lane 走
- 把 `unsupported_exact_live_structure_bucket_blocks_trade` 當成當前 runtime blocker，而不是沿用舊 q35 敘事
- 把 `feat_4h_bias50` 保留成 reference-only component research，直到 exact support 準備好

**成功標準**
- current live q65 lane 有 exact support 或明確可接受的治理路徑
- `/api/status` / probe / drilldown / docs 一致說同一個 blocker
- 不再出現「current row 是 q65，文件卻還把 q35 當主線」

### 目標 B：清掉剩餘 3 條 fast governance timeout
**重點**
- `feature_group_ablation.py`
- `bull_4h_pocket_ablation.py`
- `hb_leaderboard_candidate_probe.py`

**成功標準**
- 以上 3 條 script 在 fast heartbeat 中要嘛 fresh 通過、要嘛安全 cache reuse
- `data/heartbeat_fast_summary.json` 明確標示 fresh / cached / fallback
- 不再依賴 7h+ stale artifact 作為常態治理證據

### 目標 C：用 fresh drift artifact 直接追 recent pathology root cause
**重點**
- recent 500 bull-concentrated pathology 現在已可穩定讀到，不再被 timeout 阻斷
- 下一步必須把 `feature compression + regime concentration + target path` 收斂成可 patch 的 data/runtime contract

**成功標準**
- heartbeat 不再只重報 `distribution_pathology` 數字
- 至少有一條 root-cause lane 被 patch / guardrail / runtime contract 吸收
- auto-propose / ISSUES / ROADMAP 可直接引用 machine-read root cause，而不是人類補敘事

---

## 下一步
1. 優先把 current q65 live lane 的 support / blocker drilldown 變成主治理 lane
2. 依序替 feature ablation、bull pocket、leaderboard probe 補 short-circuit / semantic cache reuse
3. 針對 recent 500 pathology 做真 root-cause patch，而不是只依賴 drift artifact 報警

---

## 成功標準
- Fast heartbeat 是可運營的 operator loop，而不是 timeout + stale fallback loop
- Current live blocker 永遠跟著 current live bucket 走
- Drift / support / governance 三條主線都能在 fast lane 中提供 fresh 或安全 cache 的產品化證據
