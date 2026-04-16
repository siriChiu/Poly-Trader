# ISSUES.md — Current State Only

_最後更新：2026-04-17 05:11 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
Poly-Trader 本輪主線是 **live decision-quality runtime truth**：
- current live path 仍是 `bull / CAUTION / q35`
- `entry_quality=0.5717`、`allowed_layers_raw=1`
- 但 exact support 僅 **1/50**，最終 `allowed_layers=0`
- 本輪已修正一個產品化誤導點：**runtime surface 以前會把 `allowed_layers_reason` 留在 raw sizing 文案，造成 UI / probe / drilldown 看起來像仍可單層部署；現在已拆成 raw reason 與 final reason**

本輪已完成的直接產品化前進：
- `model/predictor.py` 現在同時輸出：
  - `allowed_layers_raw_reason` = guardrail 前原始 sizing 解釋
  - `allowed_layers_reason` = 最終有效層數原因
- `scripts/hb_predict_probe.py`、`scripts/live_decision_quality_drilldown.py`、`scripts/hb_parallel_runner.py` 已同步吃這個 contract
- runtime artifact 已刷新，當前 live row 現在明確顯示：
  - `allowed_layers_raw_reason=entry_quality_C_single_layer`
  - `allowed_layers_reason=under_minimum_exact_live_structure_bucket`

驗證：
- `PYTHONPATH=. pytest tests/test_hb_predict_probe.py tests/test_api_feature_history_and_predictor.py::test_infer_deployment_blocker_flags_under_minimum_exact_live_structure_bucket tests/test_api_feature_history_and_predictor.py::test_apply_live_execution_guardrails_caps_layers_for_c_quality_and_guardrailed_window tests/test_hb_parallel_runner.py::test_collect_live_predictor_diagnostics_reads_probe_json -q` → **4 passed**
- runtime：
  - `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
  - `python scripts/live_decision_quality_drilldown.py`
- 產物確認：
  - `data/live_predict_probe.json` 已含 `allowed_layers_raw_reason` / `allowed_layers_reason`
  - `docs/analysis/live_decision_quality_drilldown.md` 已明確顯示 `1 → 0` 與兩種原因

---

## Open Issues

### P0. current live q35 exact support 仍嚴重不足，仍是 deployment blocker
**現況**
- live path：`bull / CAUTION / q35`
- `entry_quality=0.5717`，`allowed_layers_raw=1`
- `current_live_structure_bucket_rows=1`
- `minimum_support_rows=50`
- 最終 blocker：`under_minimum_exact_live_structure_bucket`

**風險**
- 即使 q35 redesign 已跨過 trade floor，如果 exact support 未補滿，仍不能部署
- 任何只看 raw sizing 的 surface 都可能重新把這條 lane 誤讀成可單層上線

**下一步**
- 持續 machine-check `support_progress`
- 若連續 heartbeat 停滯，升級成 support accumulation blocker

### P0. recent canonical 100-row window 仍是 distribution pathology
**現況**
- recent 100 rows：`win_rate=1.0000`
- dominant regime：`bull (100%)`
- alerts：`constant_target / regime_concentration / regime_shift`
- interpretation：`distribution_pathology`

**風險**
- recent calibration slice 仍可能把 live expectation 拉向假樂觀
- 若 guardrail 沒有被所有 surface 正確消費，會再產生「看起來健康」的假訊號

**下一步**
- 繼續沿 sibling-window / feature-shift artifact 做 root-cause patch
- 在 pathology 根因未收斂前維持 current guardrail

### P1. collect-enabled freshness 尚未在本輪重新驗證
**現況**
- 本輪重點是 runtime reason contract truth，不是 freshness repair
- `labels[240m/1440m]` 是否在 collect-enabled lane 完全恢復，本輪未重新驗證

**風險**
- 若把本輪 probe/drilldown 修正誤讀成整體 live-ready，會忽略 freshness 仍需閉環

**下一步**
- 下一輪在 collect-enabled fast/full lane 重新驗證 watchdog / candidate probe / freshness 三者同時健康

---

## Not Issues
- 不是「current live blocker 不清楚」：目前 blocker 很清楚，就是 `under_minimum_exact_live_structure_bucket`
- 不是「q35 redesign 沒有作用」：raw sizing 已到 `allowed_layers_raw=1`
- 不是「drilldown 還在說可以單層部署」：本輪已修正 raw/final reason 分離，surface 現在能正確說明 `1 → 0`

---

## Current Priority
1. 累積 current live q35 exact support，直到 `current_live_structure_bucket_rows >= 50`
2. 繼續處理 recent canonical distribution pathology 的根因，而不是只看 alert
3. 在 collect-enabled lane 驗證 freshness 與 governance/runtime contract 同步健康
