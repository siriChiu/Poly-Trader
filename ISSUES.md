# ISSUES.md — Current State Only

_最後更新：2026-04-18 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留歷史流水帳。

---

## 當前主線
本輪把 heartbeat 治理 truth 拉回 **current live bucket**：
- `scripts/auto_propose_fixes.py` 現在會優先讀 `data/live_predict_probe.json` 的 `current_live_structure_bucket/current_live_structure_bucket_rows`
- 舊的 lane-specific blocker（例如 `P1_current_q35_exact_support`、`P1_q35_redesign_support_blocked`）不再因 `issues.json` 殘留或 stale leaderboard snapshot 而繼續誤導 current state
- 重新跑 `python scripts/hb_parallel_runner.py --fast` 後，當前主 blocker 已正確收斂為：
  - live bucket = `CAUTION|structure_quality_caution|q35`
  - exact support = `0/50`
  - live probe `entry_quality=0.5548`、`allowed_layers_raw=1`、`allowed_layers=0`
  - 最終 deployment blocker = `unsupported_exact_live_structure_bucket`

已驗證：
- `source venv/bin/activate && pytest tests/test_auto_propose_fixes.py -q`
- `source venv/bin/activate && python scripts/auto_propose_fixes.py`
- `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast`

---

## Open Issues

### P0. recent canonical window 仍是 bull-concentrated distribution pathology
**現況**
- fast heartbeat：recent 500 rows = `distribution_pathology`
- `win_rate=0.8400`、`avg_quality=0.3716`、`avg_dd_penalty=0.1460`
- top shifts 仍集中在 `feat_4h_bb_pct_b / feat_4h_bias20 / feat_4h_ma_order`
- `new_compressed=feat_dxy/feat_vix`

**風險**
- calibration scope 可能被 bull-concentrated pathology slice 稀釋
- heartbeat 若只看高 recent win rate，會把 distribution pathology 誤寫成健康 closure

**下一步**
- 直接 drill into recent canonical rows 的 feature variance / distinct-count / target-path root cause
- 保持 decision-quality guardrails 開啟，直到 pathology 被解釋或修掉

### P1. current live q35 exact support 仍為 0/50
**現況**
- 最新 live probe：`current_live_structure_bucket=CAUTION|structure_quality_caution|q35`
- `current_live_structure_bucket_rows=0`
- `minimum_support_rows=50`
- `#H_AUTO_CURRENT_BUCKET_SUPPORT` 現在已會跟著 live bucket 即時改寫

**風險**
- 就算 broader bull scope 有資料，也不能當成 current q35 deployment 放行依據
- 若文件或 issue tracker 沒跟 live bucket 同步，operator 會追錯 blocker

**下一步**
- 累積 q35 exact support
- 若 live bucket 再次切換，立刻重寫 blocker，不可沿用舊 q35 敘事

### P1. q35 discriminative redesign 不是 deployment closure
**現況**
- live probe 顯示 `q35_discriminative_redesign_applied=true`
- `entry_quality` 已被拉到 `0.5548`，`allowed_layers_raw=1`
- 但 `allowed_layers=0`，因 exact live bucket 仍無支持，deployment blocker 依舊成立

**風險**
- 把「跨過 trade floor」誤讀成「可部署」會造成假產品化

**下一步**
- 維持 blocker-first 語義
- 在 exact support 補滿前，不可把 q35 redesign 寫成 release-ready

### P1. model stability / dual-role governance 尚未收斂
**現況**
- `cv_accuracy=0.6978`
- `cv_std=0.1161`
- `cv_worst=0.5445`
- global winner 仍是 `core_only`，production profile 仍是 `core_plus_macro`

**風險**
- 容易把 dual-role governance 誤寫成 parity drift 或單純排名問題

**下一步**
- 繼續把 governance split 明寫為「global ranking vs support-aware production」
- 在 q35 exact support 未補滿前，不把 profile split 當作主 blocker

### P2. sparse-source blockers 仍在背景
**現況**
- blocked features = 8
- 主 blocker 仍是 `fin_netflow` 的 `auth_missing`

**風險**
- 會持續限制研究型 overlay / archive-window coverage
- 但現在不是 current-live deployment 的第一順位 blocker

**下一步**
- defer，等 current live bucket blocker 與 pathology 先收斂

---

## Not Issues
- 舊 q35 issue id 殘留在 `issues.json`：**本輪已修正自動 resolve / rewrite 行為**，不再把它當作 current blocker 本身
- `entry_quality >= 0.55`：**不等於可部署**；exact support = 0 時仍必須擋單
- `core_only` vs `core_plus_macro`：目前是 **dual-role governance**，不是 parity drift

---

## Current Priority
1. **把 current live q35 exact support 從 0/50 往可驗證 support 累積推進**
2. **對 recent distribution pathology 做 root-cause drill-down，而不是只重報指標**
3. **保持 blocker-first 的 runtime / docs / issues 一致語義，避免假 closure**
