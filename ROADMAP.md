# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 05:46 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- heartbeat 主線已固定為產品化，不再退化成研究報告
- `scripts/hb_predict_probe.py` 現在執行時會同步覆寫 `data/live_predict_probe.json`
- q15 live blocker 相關 artifacts 已重新對齊同一個 current probe snapshot：
  - `data/live_predict_probe.json`
  - `docs/analysis/live_decision_quality_drilldown.md`
  - `data/q15_support_audit.json`
- 目前 runtime current truth 已確認：
  - live path：`bull / CAUTION / D`
  - bucket：`CAUTION|structure_quality_caution|q15`
  - exact support：`4 / 50`
  - blocker：`under_minimum_exact_live_structure_bucket`
  - support progress：`accumulating`

驗證完成：
- `./venv/bin/python -m pytest tests/test_hb_predict_probe.py tests/test_q15_support_audit.py tests/test_hb_parallel_runner.py::test_collect_q15_support_audit_diagnostics_reads_support_and_floor_verdicts -q` → **10 passed**
- `./venv/bin/python scripts/hb_predict_probe.py` → 會落地最新 probe artifact
- `./venv/bin/python scripts/live_decision_quality_drilldown.py` → 產出最新 q15 drilldown
- `HB_RUN_LABEL=20260417-cron ./venv/bin/python scripts/hb_q15_support_audit.py` → support progress 已更新為 `4 / 50`, `accumulating`

---

## 主目標

### 目標 A：把 q15 exact support 從「已出現」推進到「可部署」
重點：
- current live blocker 已從「沒有 exact rows」前進到「已有 exact rows 但只有 4/50」
- 下一輪主線不是再證明 blocker 存在，而是持續 machine-check 它是否**真的在累積**
- exact support 未達 50 前，不得用 proxy / neighbor / component research 當 release 依據

### 目標 B：把 q15 component patch 保留在合法邊界內
重點：
- `feat_4h_bias50` 是目前最佳單點 component 候選
- 但 q15 audit 已明確：`math_cross_possible_but_illegal_without_exact_support`
- 因此下一階段只能先追 support，不能跳步把 bias50 patch 包裝成 live closure

### 目標 C：重新做 collect-enabled freshness 閉環
重點：
- 本輪修的是 runtime artifact truth，不是 freshness 本身
- 下一輪要同時確認：
  - collect / watchdog / freshness 健康
  - q15 support progress 與 live blocker 仍一致
  - docs / probe / audit / summary 不再分裂

---

## 下一步
1. 追蹤 q15 `support_progress`，確認 exact rows 是持續增加、停滯、還是回退
2. 在 support 未達標前，維持 `feat_4h_bias50` 為 reference-only research，不做 deployment release
3. 重跑 collect-enabled heartbeat，驗證 freshness + runtime truth + governance 三者一致

---

## 成功標準
- `data/live_predict_probe.json` 永遠代表最新 probe，而不是舊 snapshot
- q15 exact support 持續增加，最終達到 `50`，或明確升級為 support stagnation blocker
- component patch 只在 exact support ready 後才進入 deployment-grade 驗證
- collect-enabled heartbeat 能同時證明 freshness、runtime blocker、support progress 與文件一致
