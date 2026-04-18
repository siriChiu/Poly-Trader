# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 22:16 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **fast heartbeat #20260418g 已重新取得最新 current-state facts**：`Raw=30888 / Features=22306 / Labels=62195`，`Global IC=14/30`，`TW-IC=30/30`，並重新落地 drift / q15 / q35 / breaker / live probe artifacts。
- **current-live truth 仍維持 breaker-first**：`hb_predict_probe.py` 與 `hb_circuit_breaker_audit.py` 都確認 canonical 1440m live path 仍是 `circuit_breaker_active`，最近 50 筆只贏 `2/50`，不是 q15/q35 blocker。
- **Strategy Lab placeholder-only UX 已補上可操作 fallback**：模型排行榜仍是 `0 comparable / 4 placeholder`，但 `strategy_param_scan` 現在已在 `web/src/pages/StrategyLab.tsx` 顯示為 fallback candidate cards，並提供 `載入候選` 按鈕。
- **fallback candidate runtime 已驗證**：瀏覽器 `/lab` 已確認可從 fallback panel 直接載入 `Auto Leaderboard · 重掃 rule_baseline #01`，成功切回工作區並帶出策略摘要、圖表與 recent trades。
- **本輪驗證已完成**：`python -m pytest tests/test_frontend_decision_contract.py tests/test_model_leaderboard.py -q` → `38 passed`；`cd web && npm run build` → success；瀏覽器 `/lab` 已驗證 fallback panel 與 load action。

---

## 主目標

### 目標 A：解除 current-live circuit breaker，或至少把 release math 維持成唯一真相
**目前真相**
- canonical 1440m `recent 50` 只贏 `2/50`
- 距離 release floor `15/50` 還差 `13` 勝
- `streak=47`

**成功標準**
- 要嘛 recent 50 視窗提升到 `>=15` 勝並解除 breaker；
- 要嘛所有 operator / heartbeat / docs 都只把 breaker release math 當成唯一 current-live blocker。

### 目標 B：把 recent canonical tail pathology 轉成可修的 root cause
**目前真相**
- primary drift window = `1000`
- `interpretation=distribution_pathology`
- `dominant_regime=bull 89.0%`
- canonical tail 已 `47x0`

**成功標準**
- 能清楚指出 recent 50 / 100 / 1000 為何持續形成 loss tail；
- 對應 patch 必須能用 `recent_drift_report.py` / `hb_predict_probe.py` / `hb_circuit_breaker_audit.py` 重跑驗證。

### 目標 C：讓 canonical model leaderboard 脫離 placeholder-only，或至少維持可操作 fallback
**目前真相**
- `/api/models/leaderboard` 仍 `count=0 / comparable_count=0 / placeholder_count=4`
- `strategy_param_scan` 已有 `6` 個 saved candidates，且 UI fallback 已能直接載入候選

**成功標準**
- 至少出現一條 `comparable_count > 0` 的 canonical model row；
- 在做到前，Strategy Lab 必須持續保留 placeholder-only honesty + loadable fallback candidates，而不是 generic 空榜。

### 目標 D：保持 execution/runtime/operator surface 同步，且不掩蓋 venue blocker
**目前真相**
- breaker truth 已能在 `/lab`、`/execution`、`/execution/status` 同步看到
- venue blocker 仍存在：credentials / order ack / fill lifecycle 尚未驗證

**成功標準**
- 即使 breaker 將來解除，operator surfaces 仍必須保留 venue readiness blocker，直到 runtime 證據真的 closure。

---

## 下一步
1. **把 canonical breaker release math 當成唯一 current-live P0**
   - 方向：沿 `hb_predict_probe.py`、`hb_circuit_breaker_audit.py`、`recent_drift_report.py` 追 recent 50 / 1000 canonical tail，找出可提升 `recent 50 wins` 的直接根因
   - 驗證：`python scripts/hb_parallel_runner.py --fast --hb <N>`、`python scripts/hb_predict_probe.py`、`python scripts/hb_circuit_breaker_audit.py <N>`、瀏覽器 `/execution/status`
2. **把 tail pathology 轉成具體 patch，而不是繼續用 q15/q35 敘事繞路**
   - 方向：針對 recent tail 的 target path、regime mix、4H feature shifts 做 root-cause drill-down；必要時補 regression tests
   - 驗證：`recent_drift_report.py`、相關 pytest、fast heartbeat
3. **把 model leaderboard 從 placeholder-only 推進到 comparable row**
   - 方向：用現有 `strategy_param_scan` / strategy leaderboard 候選反推可部署的 model deployment profile 或 candidate promotion，避免 model leaderboard 永遠停在 0 trades
   - 驗證：`/api/models/leaderboard`、`python scripts/hb_model_leaderboard_api_probe.py`、瀏覽器 `/lab`
4. **保持 venue blocker 可見，不得被 breaker / leaderboard UX 修復遮蔽**
   - 方向：持續以 `/execution` / `/execution/status` / `/api/status` 作 operator-facing truth surface
   - 驗證：瀏覽器 UI + 對應 payload

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- recent tail pathology 有可重跑、可驗證的 root cause / patch / regression evidence
- canonical model leaderboard 不再只是 placeholder-only，或至少有明確且可操作的 fallback candidate workflow
- heartbeat 維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
