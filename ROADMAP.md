# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- fast heartbeat / auto-propose 現在會優先使用 `data/live_predict_probe.json` 的 current live bucket truth
- `#H_AUTO_CURRENT_BUCKET_SUPPORT` 會跟著最新 live bucket 改寫，不再沿用 `issues.json` 舊 title
- 舊的 lane-specific blocker（如 `P1_current_q35_exact_support`、`P1_q35_redesign_support_blocked`）在 live bucket 改變時會自動 resolve，避免 current-state 文件被 stale issue 汙染
- 已用 regression test 鎖住此 contract：
  - `source venv/bin/activate && pytest tests/test_auto_propose_fixes.py -q`
- 已用 runtime 重跑驗證整條心跳鏈：
  - `source venv/bin/activate && python scripts/auto_propose_fixes.py`
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast`

---

## 主目標

### 目標 A：收斂 current live q35 exact-support blocker
**目前真相**
- current live bucket = `CAUTION|structure_quality_caution|q35`
- exact support = `0/50`
- q35 discriminative redesign 已把 `entry_quality` 拉到 `0.5548`
- 但最終仍 `allowed_layers=0`

**成功標準**
- `current_live_structure_bucket_rows >= 50`
- live probe 不再回報 `unsupported_exact_live_structure_bucket`
- `allowed_layers_reason` 與 runtime blocker 文案保持一致，不再有假 deployable 敘事

### 目標 B：把 recent distribution pathology 從觀測升級成 root cause
**目前真相**
- recent 500 canonical rows 仍是 bull-concentrated distribution pathology
- 目前只知道症狀與 top feature shifts，還沒有 product-grade root cause patch

**成功標準**
- heartbeat 產出可重跑的 root-cause artifact / patch
- guardrail reason 能直接引用病灶根因，而不是只回報 high-level alerts

### 目標 C：維持 blocker-first 的治理 surface 一致性
**目前真相**
- live probe、auto-propose、issues.json 已重新對齊 current bucket truth
- leaderboard / bull-pocket heavy artifacts 在 fast lane 仍可能 timeout 並 fallback

**成功標準**
- operator-facing current blocker 永遠以 latest live probe 為準
- heavy artifact timeout 不再讓 current-state docs 回退到舊 bucket / 舊 blocker

---

## 下一步
1. **以 q35 exact support 為主追 current-live blocker**
   - 驗證：`python scripts/hb_predict_probe.py` 顯示 current bucket rows 是否開始累積，且 blocker 文案仍為 current bucket truth
2. **做 recent pathology root-cause drill-down**
   - 驗證：能指出 recent canonical pathology 的 feature / label / scope 根因，不只剩 `distribution_pathology` 摘要
3. **縮短 fast lane heavy artifact 的 stale/fallback 視窗**
   - 驗證：`hb_parallel_runner.py --fast` 的 current-state summary 不再依賴過期 alignment / bull-pocket snapshot 才能說明 current blocker

---

## 成功標準
- `ISSUES.md` / `ROADMAP.md` / `issues.json` 都只描述最新 current live bucket blocker，不殘留舊 lane 敘事
- live probe、auto-propose、fast heartbeat summary 對 current bucket / blocker / layers 給出同一個答案
- q35 redesign 只在 exact support ready 後才升級成 deployment closure；在那之前一律 blocker-first
