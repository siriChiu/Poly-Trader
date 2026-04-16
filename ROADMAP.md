# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 05:11 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- heartbeat 主線已固定為產品化，不再把心跳退化成研究報告
- live predictor / probe / drilldown 現在已明確區分：
  - `allowed_layers_raw_reason`（guardrail 前）
  - `allowed_layers_reason`（最終有效）
- current runtime artifact 已能正確呈現：
  - `allowed_layers_raw=1`
  - `allowed_layers=0`
  - `allowed_layers_raw_reason=entry_quality_C_single_layer`
  - `allowed_layers_reason=under_minimum_exact_live_structure_bucket`
- 驗證完成：
  - `PYTHONPATH=. pytest tests/test_hb_predict_probe.py tests/test_api_feature_history_and_predictor.py::test_infer_deployment_blocker_flags_under_minimum_exact_live_structure_bucket tests/test_api_feature_history_and_predictor.py::test_apply_live_execution_guardrails_caps_layers_for_c_quality_and_guardrailed_window tests/test_hb_parallel_runner.py::test_collect_live_predictor_diagnostics_reads_probe_json -q` → 4 passed
  - `python scripts/hb_predict_probe.py > data/live_predict_probe.json` → 通過
  - `python scripts/live_decision_quality_drilldown.py` → 通過

---

## 主目標

### 目標 A：解除 current live q35 exact support blocker
重點：
- current live bucket = `CAUTION|structure_quality_caution|q35`
- raw sizing 已經不是主問題：`allowed_layers_raw=1`
- 真正 blocker 仍是 `current_live_structure_bucket_rows=1 < minimum_support_rows=50`
- 下一輪必須以 support accumulation / stagnation truth 當 closure 主線

### 目標 B：把 recent pathology 從「警報」推進到「根因修復」
重點：
- recent 100-row canonical window 仍是 `constant_target + bull 100% + regime_shift`
- 已有 drift / sibling-window artifact，但還需要進一步 patch 到 calibration / runtime / product semantics
- 不接受只重報 drift 指標、不做產品化修補

### 目標 C：collect-enabled lane 全鏈路重驗證
重點：
- 下一輪要同時確認：
  - watchdog / collect / freshness 健康
  - candidate governance 維持綠燈
  - runtime blocker 與 docs / probe / summary 一致

---

## 下一步
1. 追 `support_progress`，確認 q35 exact support 是累積、停滯、還是回退
2. 針對 recent canonical pathology 做 root-cause patch，而不是只沿用現有 guardrail
3. 在 collect-enabled fast/full heartbeat 重新驗證 freshness + governance + runtime truth 三者一致

---

## 成功標準
- current live surface 不再混淆 raw sizing 與 final blocked state
- q35 exact support 開始持續累積，或明確升級成 support stagnation blocker
- collect-enabled heartbeat 能同時證明 freshness、candidate governance、runtime blocker 都與文件一致
