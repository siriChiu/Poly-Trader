# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 19:50 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **q15 fast-heartbeat runtime resync**：`scripts/hb_parallel_runner.py` 現在會在 q15 support audit 已經說明 `exact_supported_component_experiment_ready`、但先前 live probe/drilldown 仍停在 pre-patch 狀態時，自動重跑 `hb_predict_probe.py` 與 `live_decision_quality_drilldown.py`，讓最終 `heartbeat_<run>_summary.json` 鎖定 resynced current-live truth。
- **q15 current-live truth 已同步到 operator surface**：最新 fast heartbeat 與 `/execution/status` 都顯示 `q15 patch active`、`layers 1 → 0`、`support 96 / 50`、`runtime_closure_state=patch_active_but_execution_blocked`，不再回退成 `patch inactive / support missing`。
- **回歸驗證完成**：
  - `python -m pytest tests/test_hb_parallel_runner.py tests/test_hb_predict_probe.py tests/test_live_decision_quality_drilldown.py tests/test_execution_console_overview.py tests/test_server_startup.py tests/test_frontend_decision_contract.py -q` → `113 passed`
  - `cd web && npm run build` → PASS
  - `python scripts/hb_parallel_runner.py --fast --hb 20260418b` → PASS（含 q15 runtime resync）
  - Browser `/execution/status` → 顯示 `q15 patch active`、`layers 1 → 0`、`support 96 / 50`

---

## 主目標

### 目標 A：把 q15 從 patch-active raw capacity 推進到真正的 execution closure
**目前真相**
- q15 已 `exact_bucket_supported (96 / 50)`
- q15 patch 已把 raw path 拉到 `entry_quality=0.5501 / allowed_layers_raw=1`
- final execution 仍被 `decision_quality_below_trade_floor` 壓回 `allowed_layers=0`
- `/execution/status` 主 blocker 仍包含 venue/product readiness：`live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證`

**成功標準**
- 要嘛 final execution path 真正出現 `allowed_layers > 0`，且 operator surface 清楚說明為何可部署；
- 要嘛把 no-deploy governance 收斂成明確的單一 closure 語義，讓 operator 能直接分辨是 **decision-quality blocker** 還是 **venue readiness blocker**，不再混成單一模糊 blocked 訊息。

### 目標 B：把 model leaderboard 從 honest placeholder-only state 推進到 usable ranking
**目前真相**
- `count=0 / comparable_count=0 / placeholder_count=6`
- placeholder-only warning 與 stale-while-revalidate 仍正常運作
- candidate profile governance 已對齊，不是目前主要 blocker

**成功標準**
- 至少產生 `comparable_count > 0` 的真正可比較 row，
- 或在 Strategy Lab / operator UX 上把 placeholder-only state 產品化到不再需要人工解讀「為什麼這一版還是空榜」。

### 目標 C：維持 execution/runtime/frontend contract 同步
**目前真相**
- q15 resync 已修掉 fast heartbeat 與 `/execution/status` 的 stale current-live truth 問題
- 但 execution surface 仍同時承載 runtime blocker 與 venue readiness blocker，後續容易再次語義混淆

**成功標準**
- heartbeat summary、`/execution/status`、Dashboard/Execution Console 對同一條 live lane 必須回報相同 closure state、相同 layers 轉換與相同 blocker hierarchy。

---

## 下一步
1. **拆清 q15 final execution blocker vs venue readiness blocker**
   - 驗證：`python scripts/hb_predict_probe.py`、`python scripts/live_decision_quality_drilldown.py`、瀏覽器 `/execution/status`
2. **追 leaderboard zero-trade 根因**
   - 驗證：`python scripts/hb_model_leaderboard_api_probe.py` 或 cache/API payload 出現 `comparable_count>0`
3. **維持 q15 resync 回歸與前端 build 綠燈**
   - 驗證：沿用本輪 113 tests + `npm run build` + fast heartbeat

---

## 成功標準
- q15 current-live lane 不再只有 raw patch capacity，而是能清楚回答最終 execution 為何被放行或阻擋
- model leaderboard 不再只是誠實的空榜，而是能提供至少一條可比較候選，或把 placeholder-only state 完整產品化
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
