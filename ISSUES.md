# ISSUES.md — Current State Only

_最後更新：2026-04-17 10:38 CST_

只保留目前有效問題；每輪 heartbeat 必須覆蓋更新，不保留舊流水帳。

---

## 當前主線
本輪已修復 **q15 exact-supported patch 的 probe ↔ audit artifact split-brain**：
- `scripts/hb_predict_probe.py` 現在會在 q15 audit 改變 patch readiness、或 audit `current_live` 與最終 probe 不一致時，**強制二次同步 q15 audit**，避免先寫 baseline probe、再讓 `hb_q15_support_audit.py` 讀到舊 probe 把 runtime 又打回未開啟狀態。
- 這個修正解決了會自我回退的產品化問題：**probe / q15 audit / live drilldown 以前可能彼此矛盾，甚至讓後續 predictor 再次讀到 stale audit 而關閉已驗證的 q15 patch**。
- 新 regression 已鎖住：當 q15 audit 第一次 refresh 仍是 baseline current_live、但第二次 force refresh 需要對齊最終 probe 時，probe 必須輸出 patch-active，且嵌入的 `q15_support_audit.current_live` 必須同步到最終 runtime 真相。

### 本輪驗證後的 runtime 真相
- live path：`bull / CAUTION / q15`
- current live structure bucket rows：`79 / 50` → **exact-supported**
- live predictor：
  - `signal=HOLD`
  - `entry_quality=0.55`
  - `entry_quality_label=C`
  - `allowed_layers=1`
  - `q15_exact_supported_component_patch_applied=true`
  - `runtime_closure_state=capacity_opened_signal_hold`
- q15 audit / live drilldown：
  - `support_route_verdict=exact_bucket_supported`
  - `current_live.entry_quality=0.55`
  - `current_live.allowed_layers=1`
  - `component_experiment_verdict=exact_supported_component_experiment_ready`

---

## Open Issues

### P0. Execution / venue surface 還沒把「capacity opened but HOLD」產品語義完整落地
**現況**
- q15 patch 已經真的把 current live row 拉到 `entry_quality=0.55`、`allowed_layers=1`
- 但目前 runtime 仍是 `signal=HOLD`
- 這代表系統現在進入的是 **deployment capacity opened**，不是自動下單，也不是 venue-ready 已完成

**風險**
- 如果 `/api/status`、execution metadata、Dashboard 文案沒有同步這層語義，operator 會把「1 層 capacity」誤讀成「已經應該下單」或「venue 路徑已完成」
- execution / reconciliation / venue guardrail 可能仍停在研究型 surface，而非產品 runtime surface

**下一步**
- 把 `capacity_opened_signal_hold` / `allowed_layers_raw -> allowed_layers` / `deployment_blocker` 語義同步到 `/api/status`、execution metadata monitor、Dashboard live status surface
- 驗證要同時覆蓋：runtime script、API payload、前端 copy、pytest

### P1. Binance / OKX execution readiness 還缺少單一真相的 reconciliation surface
**現況**
- q15 live lane blocker已不再是 support / patch replay
- 下一個產品化主問題不再是 calibration 研究，而是：**account / order / venue / reconcile 是否有同一個 operator-facing truth**

**風險**
- 若 execution monitor、order manager、status API、Dashboard 對 venue 狀態各說各話，產品看起來 ready，實際上 operator 仍無法安全判斷是否可部署

**下一步**
- 以 Binance 為第一優先，補齊 execution metadata、external monitor、status API 的單一真相鏈
- OKX 維持第二 venue，但不能先跳過 Binance 的 reconciliation closure

---

## Not Issues
- 不是 q15 exact support 不足：**目前 `79 / 50`，已 exact-supported**
- 不是 q15 patch 仍停在 audit 文件層：**live predictor / hb_predict_probe / live_decision_quality_drilldown 已對齊 `patch active + allowed_layers=1`**
- 不是 q15 runtime 還被假 blocker 擋住：**`deployment_blocker=null`，當前狀態是 `capacity_opened_signal_hold`，不是 support blocker**

---

## Current Priority
1. 把 **capacity-opened-but-HOLD** 正式變成 execution / API / Dashboard 的產品語義
2. 用 Binance 先收斂 **execution reconciliation / venue truth**
3. 再把同一套 contract 推到 OKX 與 Strategy Lab / Dashboard 的 operator surface
