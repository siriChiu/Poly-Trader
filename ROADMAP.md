# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 11:18 UTC_

只保留目前計畫，不保留歷史 roadmap。

---

## 已完成
- 已完成本輪 closed-loop diagnostics：
  - `python scripts/recent_drift_report.py`
  - `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
  - `python scripts/live_decision_quality_drilldown.py`
  - `python scripts/hb_q15_support_audit.py`
  - `python scripts/hb_q15_bucket_root_cause.py`
  - `python scripts/hb_q15_boundary_replay.py`
  - `python scripts/full_ic.py`
  - `python scripts/regime_aware_ic.py`
  - `python tests/comprehensive_test.py`
- 已確認本輪 canonical 基線：
  - Raw / Features / Labels = **30527 / 18664 / 43750**
  - 1440m canonical rows = **12709**
  - `simulated_pyramid_win = 0.6470`
  - Global IC = **17 / 30**
  - TW-IC = **26 / 30**
  - regime-aware IC = **Bear 5/8 / Bull 6/8 / Chop 4/8**
- 已完成本輪 real forward-progress patch：
  - `scripts/recent_drift_report.py` 新增 **`feat_4h_rsi14` expected-compression provenance**
  - `scripts/recent_drift_report.py` 補上 proxy 欄位缺失時的 safe guard，避免精簡測試資料集直接崩潰
  - `tests/test_recent_drift_report.py` 新增 `feat_4h_rsi14` provenance regression
  - `ARCHITECTURE.md` 同步新增 4H RSI14 provenance contract
- 已完成驗證：
  - `python -m pytest tests/test_recent_drift_report.py -q` → **17 passed**
  - `python scripts/recent_drift_report.py`
  - `python scripts/hb_q15_support_audit.py`
  - `python scripts/hb_q15_bucket_root_cause.py`
  - `python tests/comprehensive_test.py` → **6/6 PASS**
- 已刷新本輪 artifact：
  - `data/recent_drift_report.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/q15_support_audit.json`
  - `docs/analysis/q15_support_audit.md`
  - `data/q15_bucket_root_cause.json`
  - `docs/analysis/q15_bucket_root_cause.md`
  - `data/q15_boundary_replay.json`
  - `docs/analysis/q15_boundary_replay.md`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
- 已確認上輪 carry-forward 的落地結果：
  - `feat_4h_bias20` **不再是 current primary unexpected-compressed blocker**
  - q15 `support_progress` **已從 no_recent_comparable_history → accumulating**
  - q15 current blocker 與 recent drift 已共同收斂到 **`feat_4h_bb_pct_b`**

---

## 主目標

### 目標 A：直接處理 `feat_4h_bb_pct_b` 的 q15→q35 結構差距
重點：
- recent drift primary window 的 sibling `new_compressed = feat_4h_bb_pct_b`
- q15 root-cause 的 `candidate_patch_feature = feat_4h_bb_pct_b`
- 這表示下一輪主線不能再分散到 bias20 / rsi14 / q35 舊敘事

### 目標 B：讓 q15 support accumulation 持續可比較
重點：
- 目前 exact q15 rows = **4 / 50**
- `support_progress.status = accumulating`
- 下一輪必須持續保留同一 bucket 歷史，確認是繼續增加、停滯，或回退

### 目標 C：維持 bias50 / q35 的 reference-only 合法性邊界
重點：
- `feat_4h_bias50` 雖然數學上可跨 floor，但仍非法放行
- q35 只是 dominant neighbor bucket，不是 current-live closure
- 任何 component / bucket 實驗都不得越權解除 exact-support blocker

---

## 下一步
1. 下一輪先讀 `data/recent_drift_report.json`：
   - 確認 primary window 的 sibling `new_compressed` 是否仍為 `feat_4h_bb_pct_b`
   - 若仍是，直接做 `feat_4h_bb_pct_b` 最小 counterfactual / scoring 檢查
2. 再讀 `data/q15_support_audit.json`：
   - 檢查 `support_progress.status`
   - 檢查 `support_progress.current_rows / minimum_support_rows`
   - 檢查 `support_progress.delta_vs_previous`
   - 檢查 `support_progress.stagnant_run_count`
   - 檢查 `support_progress.escalate_to_blocker`
3. 再讀 `data/q15_bucket_root_cause.json`：
   - 若 `candidate_patch_feature` 仍是 `feat_4h_bb_pct_b`
   - 對 current row vs dominant q35 neighbor 做最小 component counterfactual
4. 若 q15 rows 仍低於 50：
   - 維持 `reference_only_until_exact_support_ready`
   - 禁止把 `feat_4h_bias50` floor-cross 寫成 deploy 放行
5. 只有在 A/B/C 三條線明確後，才回頭看 q35 reference artifact 或其他 side quest

---

## 成功標準
- 已留下 1 個針對 `feat_4h_bb_pct_b` 的最小 counterfactual artifact 或 patch，能回答它是否足以把 current row 推近 q35
- `data/q15_support_audit.json` 的 `support_progress.current_rows` 相比本輪 **不下降**，且歷史鏈持續存在
- 若 component 實驗仍只具 reference value，artifact / ISSUES / ROADMAP / probe 都一致保留 `reference_only_until_exact_support_ready`
- `ISSUES.md` / `ROADMAP.md` / `ARCHITECTURE.md` / 最新 artifact 對 current blocker 的描述一致：**現在主線是 `feat_4h_bb_pct_b + q15 support accumulation`**

---

## Fallback if fail
- 若下一輪沒有真正碰 `feat_4h_bb_pct_b`：升級為 heartbeat empty-progress blocker
- 若 q15 rows 停在 4 且 `support_progress` 轉 stalled/regressed：升級為 support accumulation blocker
- 若 current live bucket 再切換：先重寫 current-state docs，再決定是否切回 q35 或其他 lane

---

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`
- `data/recent_drift_report.json`
- `data/live_predict_probe.json`
- `data/live_decision_quality_drilldown.json`
- `data/q15_support_audit.json`
- `docs/analysis/q15_support_audit.md`
- `data/q15_bucket_root_cause.json`
- `docs/analysis/q15_bucket_root_cause.md`
- `data/q15_boundary_replay.json`
- `docs/analysis/q15_boundary_replay.md`

---

## Carry-forward input for next heartbeat
1. Step 0.5 先讀 `ISSUES.md` / `ROADMAP.md`，確認本輪已把主病灶收斂到 `feat_4h_bb_pct_b`，且 `feat_4h_bias20` 已退出 current primary blocker。
2. 先讀最新 `data/recent_drift_report.json`：
   - sibling-window `new_compressed` 是否仍為 `feat_4h_bb_pct_b`
   - recent 100 是否仍為 `100x1 bull pocket`
3. 再讀最新 `data/q15_support_audit.json`：
   - `support_progress.status`
   - `support_progress.current_rows`
   - `support_progress.delta_vs_previous`
   - `support_progress.stagnant_run_count`
   - `support_progress.escalate_to_blocker`
4. 再讀 `data/q15_bucket_root_cause.json`：
   - `candidate_patch_feature`
   - `needed_raw_delta_to_target_p25`
   - `needed_raw_delta_to_cross_q35`
5. 若 q15 support 仍未達標，禁止把 bias50 / q35 敘事寫成 current deploy closure；必須維持 `reference_only_until_exact_support_ready`。
