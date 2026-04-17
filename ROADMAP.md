# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 14:12 UTC_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- Canonical target 已穩定對齊 `simulated_pyramid_win`
- Fast heartbeat collect / IC / live probe / q15 系列 artifact 仍可閉環運作
- **本輪完成：`q35_scaling_audit` 快路徑產品化**
  - current live row 不在 q35 時，直接輸出 reference-only artifact
  - runtime 若先被 circuit breaker 擋下，直接輸出 blocker-preempt artifact
  - q35 audit 不再把非 q35 current row 包裝成 q35 blocker，也不再強迫跑重型 historical lane 分析
  - 新增 regression tests，鎖住「aligned probe reuse / non-q35 short-circuit / breaker preempt short-circuit」

---

## 主目標

### 目標 A：關閉 recent pathology 的 fast-timeout 與 root-cause 黑箱
**重點**
- 讓 `recent_drift_report.py` 在 fast heartbeat 預算內完成，或明確使用安全快取
- 把 recent canonical pathology 從「數字摘要」升級為可修復的 root-cause artifact

**成功標準**
- fast heartbeat 不再對 `recent_drift_report` timeout
- recent 500 / 100 canonical pathology 有 machine-read root cause 與 verify path
- heartbeat summary 不再依賴 timeout fallback 才能知道 recent 問題

### 目標 B：把 current live bucket 治理完全切到 `ALLOW|base_allow|q65`
**重點**
- q35 已降級為 reference-only；接下來要把所有 support / blocker / calibration 分析切到 current q65 bucket
- current live blocker 必須以 exact support 與 current trade-floor gap 為主，而不是沿用舊 q35 blocker

**成功標準**
- probe / audit / docs 一致指向 q65 current bucket
- `current_live_structure_bucket_rows`、support route、remaining gap to floor 在主要 surface 可直接看懂
- 不再出現「current row 明明不是 q35，文件仍把 q35 當主 blocker」

### 目標 C：清掉 fast governance lane 的剩餘 timeout
**重點**
- `feature_group_ablation.py`
- `bull_4h_pocket_ablation.py`
- `hb_leaderboard_candidate_probe.py`

**成功標準**
- 以上 3 條 script 在 fast heartbeat 中要嘛通過、要嘛走明確安全 reuse；不能再以 timeout 作為常態路徑
- heartbeat summary 直接註明 artifact 是 fresh / cached / fallback，而不是只看到 timeout 後的人類摘要

---

## 下一步
1. 優先產品化 `recent_drift_report` 的 fast-safe 執行路徑
2. 把 current live q65 bucket support / blocker drilldown 變成主治理 lane
3. 依序替 feature ablation、bull pocket、leaderboard probe 補 short-circuit / semantic cache reuse

---

## 成功標準
- Fast heartbeat 真正變成可運營的 operator loop，而不是 timeout + fallback loop
- Current live blocker 永遠跟著 current live bucket 走，不再被舊 q35 敘事綁架
- Governance artifact 全部能在 fast lane 中提供新鮮、可執行、machine-read 的產品化證據
