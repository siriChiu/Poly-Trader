# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 00:35 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **deployment profile 產品化可見化已落地**：`backtesting/model_leaderboard.py` 的 promoted deployment profiles 已補齊 scan winner 缺的 `nose_max/pulse_min`，leaderboard candidate 現在能直接選到 code-backed promoted profile，而不是只停在 `scan_backed_best`。
- **leaderboard stale-cache semantic drift 已修復**：`scripts/hb_leaderboard_candidate_probe.py` 現在會在 stale cache 缺少 `selected_feature_profile / selected_deployment_profile` 時自動 live rebuild；本輪也已把 model leaderboard API cache 刷新為 fresh。
- **Strategy Lab product UX 已驗證吃到新的 deployment contract**：`/lab` 瀏覽器實測顯示 `deployment: 穩定轉折 · Bull/Chop 嚴格 v1 · code-backed promoted from scan`，不再只露出 artifact-only profile 名稱。
- **q15 exact support 已恢復達標**：current live bucket `CAUTION|structure_quality_caution|q15` 現在 `69 >= 50` rows，support shortage 不再是主 blocker；真正 blocker 仍是 breaker + trade floor。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live 真相，直到真正解除
**目前真相**
- canonical `1440m` recent `50` 只贏 `0/50`
- `streak=77`
- 距離 release floor `15/50` 還差 `15` 勝

**成功標準**
- 要嘛 recent `50` 提升到 `>=15` 勝且 breaker 解除；
- 要嘛所有 operator / heartbeat / docs 都只把 breaker release math 當成唯一 current-live blocker。

### 目標 B：把 recent canonical tail pathology 轉成可修的 root cause
**目前真相**
- primary drift window = `1000`
- `interpretation=distribution_pathology`
- `dominant_regime=bull 92.0%`
- canonical tail 已 `77x0`
- `feat_4h_bias50` 仍是 current q15 lane 的最大單點 floor gap component

**成功標準**
- 能清楚指出 recent `50 / 100 / 1000` 為何持續形成 loss tail；
- 對應 patch 必須能用 `recent_drift_report.py` / `hb_predict_probe.py` / targeted regression test 重跑驗證。

### 目標 C：完成 exact-supported post-threshold leaderboard governance sync
**目前真相**
- deployment profile promotion 已完成，top model 已是 code-backed promoted profile
- 但 candidate probe 仍顯示 `post_threshold_governance_contract_needs_leaderboard_sync`
- leaderboard global winner = `core_only`
- train/runtime production profile = `core_plus_macro_plus_4h_structure_shift`

**成功標準**
- heartbeat / docs / operator payload 都能清楚區分 `global shrinkage winner` 與 `exact-supported production profile` 的角色；
- 若需要顯式同步，必須讓 leaderboard payload 與 Strategy Lab 不再留下任何舊的 fallback 語義。

### 目標 D：保持 execution/runtime/operator surface 同步，且不掩蓋 venue blocker
**目前真相**
- `/api/status` 與 `/lab` 已可同時顯示 breaker 與 venue-readiness blockers
- live exchange credential / order ack / fill lifecycle 仍未驗證

**成功標準**
- 即使 breaker 將來解除，operator surface 仍必須保留 venue readiness blocker，直到 runtime 證據真的 closure。

---

## 下一步
1. **針對 bull recent tail 做真正 patch，而不是只維持觀測**
   - 驗證：`recent_drift_report.py`、`hb_predict_probe.py`、新增 regression test
2. **把 exact-supported post-threshold governance 明確同步到 leaderboard / docs / operator payload**
   - 驗證：`hb_leaderboard_candidate_probe.py`、`hb_model_leaderboard_api_probe.py`、瀏覽器 `/lab`
3. **持續保留 breaker-first truth 與 venue blockers 同步可見**
   - 驗證：`/execution/status`、`/execution`、`/api/status`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- recent tail pathology 有可重跑、可驗證的 root cause / patch / regression evidence
- canonical leaderboard deployment profile 已產品化，且 post-threshold governance 敘事與 runtime 同步
- heartbeat 維持：**issue 對齊 → 主動修復 P0/P1 → verify → docs overwrite → commit → push**
