# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 21:46 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **current-state issue truth 已產品化到 machine-readable 層**：`scripts/auto_propose_fixes.py` 現在在 live probe 進入 `CIRCUIT_BREAKER` / `circuit_breaker_active` 時，會停止沿用 stale q15 bucket history，改由 breaker release math 生成 `#H_AUTO_CIRCUIT_BREAKER`，並自動 resolve 舊的 `P0_q15_patch_active_but_execution_blocked`。
- **回歸測試已補上**：`python -m pytest tests/test_auto_propose_fixes.py -q` → `19 passed`；`python -m pytest tests/test_api_feature_history_and_predictor.py tests/test_hb_predict_probe.py tests/test_q15_support_audit.py tests/test_auto_propose_fixes.py tests/test_server_startup.py -q` → `129 passed`。
- **fast heartbeat 已重新對齊 current-live truth**：`python scripts/hb_parallel_runner.py --fast --hb 20260418f` 成功完成 collect / IC / drift / q35 / q15 / breaker / auto-propose 閉環，並把 current-live truth 切回 `circuit_breaker_active`。
- **operator UI 已驗證 breaker truth**：瀏覽器 `http://127.0.0.1:5173/execution` 與 `/execution/status` 均顯示 `circuit_breaker_active`、`circuit_breaker_blocks_trade`、`layers — → 0`，並保留 venue readiness blocker。
- **leaderboard honesty 仍被守住**：瀏覽器 `fetch('/api/models/leaderboard')` 驗證 `count=0 / comparable_count=0 / placeholder_count=4 / stale=true / refreshing=true`；目前仍是誠實空榜，而不是假排名。

---

## 主目標

### 目標 A：解除 current-live circuit breaker，或至少把 release math 維持成唯一真相
**目前真相**
- current live path 已不是 q15/q35 floor-gap 主導，而是 `circuit_breaker_active`
- recent 50 只贏 `4/50`，距離 release floor `15/50` 還差 `11` 勝
- `streak=45`，tail pathology 仍在擴大

**成功標準**
- 要嘛 recent 50 視窗提升到 `>=15` 勝並解除 breaker；
- 要嘛所有 operator / heartbeat / docs 只把 breaker release math 當成唯一 current-live blocker，不再混入 stale q15/q35 敘事。

### 目標 B：把 recent canonical tail pathology 轉成可修的 root cause
**目前真相**
- primary drift window = `1000`
- `interpretation=distribution_pathology`
- `dominant_regime=bull 88.8%`
- tail streak 已到 `45x0`

**成功標準**
- 能清楚指出 recent 50 / 100 / 1000 為何持續輸出 loss tail；
- 對應 patch 必須能用 `hb_predict_probe.py` / `hb_circuit_breaker_audit.py` / `recent_drift_report.py` 重跑驗證，而不是只靠主觀描述。

### 目標 C：讓 canonical leaderboard 脫離 placeholder-only
**目前真相**
- `/api/models/leaderboard` 仍 `count=0 / comparable_count=0 / placeholder_count=4`
- API 雖已誠實標示 `stale=true / refreshing=true`，但 עדיין沒有任何可部署 canonical row

**成功標準**
- 至少出現一條 `comparable_count > 0` 的 canonical row；
- 在做到之前，前端 / API 都必須維持 placeholder-only warning，不可把背景重算中的空榜包裝成正常排名。

### 目標 D：保持 execution/runtime/operator surface 同步，且不掩蓋 venue blocker
**目前真相**
- `/execution`、`/execution/status` 已能顯示 breaker truth
- venue blocker 仍存在：credentials / order ack / fill lifecycle 尚未驗證

**成功標準**
- 即使 breaker 將來解除，operator surfaces 仍必須保留 venue readiness blocker，直到 runtime 證據真的 closure。

---

## 下一步
1. **把 circuit breaker release math 當成唯一 current-live P0**
   - 方向：沿 `hb_predict_probe.py`、`hb_circuit_breaker_audit.py`、`recent_drift_report.py` 追 recent 50/1000 canonical tail，找出能提升 recent 50 勝數的直接根因
   - 驗證：`python scripts/hb_parallel_runner.py --fast --hb <N>`、`python scripts/hb_predict_probe.py`、`python scripts/hb_circuit_breaker_audit.py <N>`、瀏覽器 `/execution/status`
2. **把 tail pathology 轉成具體 patch，而不是繼續用 q15/q35 敘事繞路**
   - 方向：針對 recent tail 的 target path、regime mix、4H feature shifts 做 root-cause drill-down；若 patch 會影響 current-live blocker，優先加回歸測試
   - 驗證：`recent_drift_report.py`、相關 pytest、fast heartbeat
3. **把 canonical leaderboard 推出至少一條 comparable row**
   - 方向：讓 canonical deployment profile 真正產生交易，不再只依賴 placeholder row；必要時同步處理 cache stale-while-revalidate 與 candidate refresh
   - 驗證：`/api/models/leaderboard`、Strategy Lab `/lab`、必要時 `hb_model_leaderboard_api_probe.py`
4. **保持 venue blocker 可見，不得被 breaker 或 leaderboard 修復遮蔽**
   - 方向：繼續以 `/execution` / `/execution/status` 作 operator-facing truth surface
   - 驗證：瀏覽器 UI + 對應 `/api/status` payload

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- recent tail pathology 有可重跑、可驗證的 root cause / patch / regression evidence
- canonical leaderboard 不再只是 placeholder-only 空榜
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
