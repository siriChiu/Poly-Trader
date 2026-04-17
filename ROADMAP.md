# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 13:38 UTC_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- **Leaderboard candidate fast-cache 已從 contract 變成 live evidence**
  - `scripts/hb_parallel_runner.py` 新增 leaderboard candidate artifact 的 **alignment snapshot refresh**
  - 當 semantic signature 不變、只是 code dependency 更新時，runner 會先輕量刷新 `data/leaderboard_feature_profile_probe.json`，再安全 reuse
  - 最新 fast run 已驗證：`serial_results.hb_leaderboard_candidate_probe.cached=true`
  - `cache_reason=refreshed_leaderboard_candidate_artifact_reused`
- **Regression guard 補齊**
  - `tests/test_hb_parallel_runner.py` 新增 refresh+reuse 案例
  - 驗證：`python -m pytest tests/test_hb_parallel_runner.py -q` → **48 passed**
- **Fast heartbeat runtime evidence refresh**
  - `Raw=30615 / Features=22033 / Labels=61792`
  - canonical runtime：`Global IC 14/30`、`TW-IC 28/30`、`CIRCUIT_BREAKER`、recent 50=`11/50`

---

## 主目標

### 目標 A：把 fast cache-hit 從單一 leaderboard lane 擴成可複用機制
重點：
- 目前已證明 leaderboard candidate lane 可 `refresh + reuse`
- 下一步不是再寫新的 timeout fallback，而是把同一套 safe cache / refresh 原則擴到其他重型治理 lanes
- 優先候選：`recent_drift_report`、`feature_group_ablation`、`bull_4h_pocket_ablation`

成功標準：
- 下一輪 fast run 至少再多一條重型 lane 顯示 `cached=true`
- summary 能清楚區分 `cached / refreshed / timeout fallback`
- operator 能直接看懂哪些 artifact 是本輪真刷新、哪些是安全重用

### 目標 B：維持 breaker-first canonical runtime truth
重點：
- `circuit_breaker_active` 仍是真正 deployment blocker
- q15 / q35 / profile governance 只能當 background governance，不可覆蓋 live blocker
- heartbeat 必須直接回答距 release 還差多少勝

成功標準：
- recent 50 win rate 回到 `>= 30%`
- recent 50 至少達 `15/50`
- predictor / drilldown / breaker audit / docs 維持同一 breaker-first truth

### 目標 C：把 recent canonical pathology 轉成可 patch 根因
重點：
- current primary pathology 仍是 `window=500` bull concentration
- 必須把「局部高 win rate」與 deployment readiness 分離
- 直接追 target-path / feature variance / distinct-count / sibling-window shift

成功標準：
- recent pathology 不再只是 `distribution_pathology` 黑盒標籤
- heartbeat / probe / docs 對同一 root cause 給出一致 machine-readable 結論
- 至少留下一個可驗證 patch 或明確 blocker，而不是只報數

### 目標 D：q35/base-stack redesign 僅保留治理候選身份
重點：
- q35 scaling artifact 目前仍顯示 redesign 候選有價值，但 live runtime 被 breaker 先擋
- 這條線暫時只能作治理候選，不是 deployment closure

成功標準：
- breaker 未解除前，不再把 q35/base-stack 改動寫成 live-ready
- breaker 一旦鬆動，立即重跑 probe / q35 audit 驗證 runtime contract

---

## 下一步
1. **擴第二條 cache-hit lane**：先挑 `recent_drift_report` 或 `feature_group_ablation` 做 safe refresh / reuse
2. **Tail root cause**：直接拆 canonical recent 50/500 的 target path，回答為何仍停在 `11/50`
3. **Breaker-first discipline**：在 breaker 未解除前，所有 q15/q35/base-stack 僅作治理候選

---

## 成功標準
- fast heartbeat 具備 **至少兩條真 cache-hit 的重型治理 lane**
- breaker-first runtime truth 在所有主要 surface 保持一致
- recent canonical pathology 被縮小或明確解釋，不再只是 blocker 黑盒
- q15/q35/base-stack 未經 breaker release 前，不再被誤包裝成 live closure
