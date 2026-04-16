# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 05:10 UTC_

只保留目前計畫，不保留歷史 roadmap。

---

## 已完成
- 已完成本輪 closed-loop diagnostics：
  - `python scripts/hb_parallel_runner.py --fast`
  - `python scripts/recent_drift_report.py`
  - `python scripts/hb_q35_scaling_audit.py`
  - `python scripts/hb_predict_probe.py > data/live_predict_probe.json`
- 已確認本輪 canonical 基線：
  - 1440m canonical rows = **12709**
  - `simulated_pyramid_win = 0.6470`
  - Global IC = **17 / 30**
  - TW-IC = **26 / 30**
  - regime-aware IC = **Bear 5/8 / Bull 6/8 / Chop 4/8**
- 已完成本輪 real forward-progress patch：
  - `scripts/recent_drift_report.py` 現在會輸出 `expected_compressed_count / expected_compressed_examples`
  - 新增 `feat_atr_pct -> raw_market_data.volatility` 的 compression provenance 判定（`underlying_raw_volatility_compression`）
  - `ARCHITECTURE.md` 已同步記錄 expected-compression provenance contract
- 已完成驗證：
  - `python -m pytest tests/test_recent_drift_report.py -q` → **9 passed**
  - `python scripts/recent_drift_report.py` → artifact 已刷新
- 已刷新本輪 artifact：
  - `data/recent_drift_report.json`
  - `data/live_predict_probe.json`
  - `data/q35_scaling_audit.json`
  - `data/heartbeat_fast_summary.json`
- 已確認 current live q35 狀態：
  - `bull / CAUTION / q35`
  - `entry_quality = 0.804`
  - `allowed_layers_raw = 2`
  - `allowed_layers = 0`
  - `q35_discriminative_redesign_applied = true`
  - **但** `deployment_blocker = unsupported_exact_live_structure_bucket`
  - `current_live_structure_bucket_rows = 0`
- 已確認 recent pathology 狀態：
  - `expected_compressed_count = 0`
  - `feat_atr_pct` **仍是** `new_unexpected_compressed_features`
  - recent 100 canonical window 仍是 `100x1 bull pocket`

---

## 主目標

### 目標 A：把 q35 主 blocker 正式切換成 exact bucket missing，不再誤寫成 under-minimum 或 floor gap
重點：
- current row 已可跨 trade floor，這件事已驗證完成
- current blocker 已不是 `1/50`，而是 **0 exact rows**
- 在 `current_live_structure_bucket_rows >= 50` 前，不可把 q35 redesign 當成 deployment closure

### 目標 B：把 recent pathology 直接收斂到 `feat_atr_pct` unexpected compression root cause
重點：
- 本輪已補 provenance contract，能分辨 ATR 壓縮是否來自 raw volatility 同步壓縮
- 但真實資料 `expected_compressed_count = 0`，表示 `feat_atr_pct` 仍未被證明只是正常波動收縮
- 下一輪必須留下 `feat_atr_pct` patch 或明確 blocker，不可只重跑 drift report

### 目標 C：把 profile split 保持在次要層，避免搶走 q35/support 主線焦點
重點：
- `leaderboard=core_only` vs `train=core_plus_macro` 目前仍是 dual-role governance
- 在 q35 support 尚未恢復前，這不是主 closure lane
- 只有在 q35 support 狀態穩定後，才判斷這是健康雙角色治理還是 parity blocker

---

## 下一步
1. 下一輪先讀 `data/live_predict_probe.json`：確認 current blocker 是否仍是 `unsupported_exact_live_structure_bucket`
2. 若 current row 仍在 q35 且 `entry_quality >= 0.55`、`q35_discriminative_redesign_applied = true`：
   - 直接追 exact support accumulation / bucket presence
   - 不可再重回 floor-gap 或 under-minimum 舊敘事
3. 直接追 `data/recent_drift_report.json`：
   - 確認 `expected_compressed_count` 是否仍為 0
   - 檢查 `new_unexpected_compressed_features=feat_atr_pct` 是否仍在
4. 只有在 q35/support 主線清楚後，才回頭看 profile split / sparse-source auth blocker

---

## 成功標準
- current live q35 blocker 語義穩定寫成：`unsupported_exact_live_structure_bucket`
- `current_live_structure_bucket_rows` 從 0 開始累積，不再是 exact bucket missing
- `feat_atr_pct` 至少有 1 個 root-cause patch + verify
- `ISSUES.md` / `ROADMAP.md` / `ARCHITECTURE.md` / `data/live_predict_probe.json` / `data/recent_drift_report.json` 對 blocker 與 pathology 語義一致

---

## Fallback if fail
- 若 q35 exact support 連續兩輪仍為 0：升級成 explicit `exact_bucket_missing` blocker，禁止再把 q35 redesign 寫成 closure
- 若 recent pathology 仍無 patch：下一輪只能做 `feat_atr_pct` pathology 修復，不再接受報告式心跳
- 若 current bucket / blocker 再切換：先重寫文件，再做其他 closure 判斷

---

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `ARCHITECTURE.md`（若 drift provenance contract 再擴張）
- `data/live_predict_probe.json`
- `data/recent_drift_report.json`
- `data/q35_scaling_audit.json`
- `data/heartbeat_fast_summary.json`

---

## Carry-forward input for next heartbeat
1. Step 0.5 先讀 `ISSUES.md` / `ROADMAP.md`，確認本輪已把 q35 主 blocker 改寫為 **unsupported exact bucket**, 不是 1/50 也不是 floor gap。
2. 先讀最新 `data/live_predict_probe.json`：
   - current row 是否仍是 `bull / CAUTION / q35`
   - `entry_quality` 是否仍 ≥ 0.55
   - `q35_discriminative_redesign_applied` 是否仍為 true
   - `deployment_blocker` 是否仍是 `unsupported_exact_live_structure_bucket`
   - `current_live_structure_bucket_rows` 是否仍為 0
3. 再讀 `data/recent_drift_report.json`：
   - `expected_compressed_count` 是否維持 0
   - `new_unexpected_compressed_features` 是否仍含 `feat_atr_pct`
   - `new_compressed=feat_atr_pct` 是否仍在 sibling-window summary
4. 若 q35 redesign 仍有效但 support 沒出現，不可重回 floor-gap 敘事；下一輪必須直接留下 support accumulation 證據或 blocker 升級。
5. 若 pathology 仍只剩 `feat_atr_pct`，下一輪不得再追 VIX frozen；必須直接做 ATR 壓縮根因分析。
