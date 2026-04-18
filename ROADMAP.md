# ROADMAP.md — Current Plan Only

_最後更新：2026-04-18 18:40 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **q15 probe/audit truth sync 修復**：`scripts/hb_predict_probe.py` 現在會先 refresh `q15_support_audit`、在 support-ready 狀態改變時 replay prediction、audit 與 probe current-live 不一致時 force-refresh，避免 stale audit 把 live probe 誤寫成 patch-ready。
- **model leaderboard placeholder contract 修復**：`server/routes/api.py` 現在會保留並快取 `placeholder_rows / placeholder_count / leaderboard_warning`；zero-trade models 不再被正常排行榜吞掉或重新偽裝成 top rank。
- **cache loader 支援 placeholder-only snapshot**：placeholder-only cache 不再被當成空 cache 忽略，`/api/models/leaderboard` 可以正確回放 `count=0 / placeholder_count>0` 的 honest state。
- **驗證完成**：
  - `python -m pytest tests/test_hb_predict_probe.py tests/test_model_leaderboard.py tests/test_model_leaderboard_api_cache.py tests/test_hb_model_leaderboard_api_probe.py tests/test_strategy_leaderboard_contract.py tests/test_q15_support_audit.py -q` → `57 passed`
  - `python -m pytest tests/test_frontend_decision_contract.py tests/test_server_startup.py -q` → `36 passed`
  - `cd web && npm run build` → PASS

---

## 主目標

### 目標 A：把 q15 current-live lane 從「support 已 closure」推進到真正的 live closure
**目前真相**
- `support_route_verdict=exact_bucket_supported`
- `support_rows=96 / 50`
- top-level live probe 仍是 `entry_quality=0.4181 / D / allowed_layers=0`
- `q15_support_audit` 雖然已經產出 `exact_supported_component_experiment_ready`，但這仍是 audit/component experiment 語義，不是 live deployment closure

**成功標準**
- `hb_predict_probe.py` top-level live truth 要嘛真正達成 `entry_quality >= 0.55 && allowed_layers > 0`，要嘛維持明確 no-deploy governance；不能再讓 audit-ready 語義冒充 live-ready。
- operator-facing surface 必須清楚分開 `support closure`、`component experiment ready`、`execution closure`。

### 目標 B：把 model leaderboard 從 honest placeholder-only state 推進到 usable comparable ranking
**目前真相**
- `/api/models/leaderboard` 已誠實回傳 `count=0 / placeholder_count=6`
- 排名 bug 已修掉，但目前沒有任何可比較的 model row

**成功標準**
- 要嘛至少出現 `comparable_count > 0` 的真正可比較 row，
- 要嘛在 Strategy Lab / operator UX 上把 placeholder-only state 明確產品化，不讓使用者誤以為還有可部署名次。

---

## 下一步
1. **q15 live-vs-audit semantic split**
   - 驗證：`python scripts/hb_predict_probe.py` 必須能清楚區分 live baseline 與 q15 component experiment；若 patch 未真的生效，不得再在 current-live surface 上看起來像已 closure。
2. **model leaderboard trade-generation root cause**
   - 驗證：`python scripts/hb_model_leaderboard_api_probe.py` 先維持 placeholder warning；修好後至少出現 `comparable_count > 0`。
3. **維持回歸與前端 build 綠燈**
   - 驗證：沿用本輪兩組 pytest + `npm run build`。

---

## 成功標準
- q15 current-live blocker 以 live predictor truth 為主，不再被 stale audit 或 component experiment 混淆
- model leaderboard 不再只是「誠實的空榜」，而是至少能提供一條可比較候選，或在 UI 上完成 placeholder-only 治理
- heartbeat 仍維持：**issue 對齊 → patch → verify → docs overwrite → commit → push**
