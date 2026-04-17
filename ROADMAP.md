# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 10:38 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- 修復 `scripts/hb_predict_probe.py` 的 **q15 probe ↔ audit artifact split-brain**：
  - 當 q15 audit refresh 改變 patch readiness 時，probe 會 replay predictor
  - 當 q15 audit 的 `current_live` 仍停在 baseline、但最終 probe 已進入 patch-active runtime 時，probe 會 **force-refresh q15 audit** 再重寫最終 JSON
- 新 regression 已鎖住：
  - q15 refresh 需要二次同步時，最終 probe 仍必須維持 `patch active + allowed_layers=1`
  - 內嵌 `q15_support_audit.current_live` 必須與最終 probe 對齊
- 當前 runtime 已驗證：
  - `hb_predict_probe.py` → `q15_exact_supported_component_patch_applied=true`、`allowed_layers=1`、`runtime_closure_state=capacity_opened_signal_hold`
  - `hb_q15_support_audit.py` → `current_live.entry_quality=0.55`、`current_live.allowed_layers=1`、`component_experiment_verdict=exact_supported_component_experiment_ready`
  - `live_decision_quality_drilldown.py` → `q15_exact_supported_component_patch_applied=true`、`allowed_layers=1`

---

## 主目標

### 目標 A：把 q15 runtime closure 從研究 artifact 推進到 execution / operator 真相
重點：
- 現在 q15 已不是 support blocker，而是 **capacity opened but HOLD** 的 runtime 狀態
- 下一步不是再做 q15 research，而是把這個狀態同步到 execution / API / Dashboard，避免 operator 誤判

成功標準：
- `/api/status`、execution metadata、Dashboard live status 都顯示同一套 `allowed_layers_raw / allowed_layers / runtime_closure_state / deployment_blocker` contract
- 不再出現「probe 說可開 1 層、status surface 卻仍像未開啟」的 split-brain

### 目標 B：以 Binance 為第一優先完成 execution reconciliation 真相鏈
重點：
- venue productization 不能只剩 config / docs readiness
- 必須有 account / order / position / external monitor / API status 的單一真相

成功標準：
- Binance execution metadata / reconciliation monitor / `/api/status` 對同一時間點給出一致 machine-read 結論
- 若不可部署，能明確指出 blocker；若可部署，也能清楚區分 HOLD / capacity-opened / order-emitted

### 目標 C：把同一套 operator contract 擴散到 Dashboard / Strategy Lab / OKX
重點：
- Dashboard / Strategy Lab 不可再只顯示研究語言或信心分數
- OKX 必須沿用已在 Binance 驗證過的 execution truth contract，而不是另起一套

成功標準：
- Dashboard / Strategy Lab 對 live/runtime 狀態的主敘事與 probe / API 完全一致
- OKX readiness 以 Binance 已收斂的 reconciliation contract 為模板延伸

---

## 下一步
1. 審查 `/api/status`、execution metadata monitor、Dashboard live surface，補上 `capacity_opened_signal_hold` 的 operator-facing contract；驗證用 pytest + runtime scripts + API payload
2. 盤點 Binance execution truth 鏈：account snapshot、order state、position truth、external monitor、status API 是否一致；若不一致，先補 reconciliation blocker surface
3. Binance 收斂後，再把同一套 execution truth contract 套到 OKX 與 Strategy Lab live/operator surface

---

## 成功標準
- q15 不再回退成 artifact split-brain，也不再把 patch-active runtime 誤寫成 baseline D/0 layers
- execution / API / Dashboard 都能正確表達：**現在是 1 層 capacity opened，但 signal 仍是 HOLD**
- Binance venue readiness 有可驗證的 reconciliation / recovery / blocker contract，而不是文件宣稱
