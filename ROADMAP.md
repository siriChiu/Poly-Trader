# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 03:57 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **full train / support-aware profile refresh 已落地**：`feature_group_ablation.py`、`bull_4h_pocket_ablation.py`、`model/train.py` 已重跑，`model/last_metrics.json` 從過期的 exact-supported `core_plus_macro_plus_4h_structure_shift` 更新為 support-aware `core_plus_macro`。
- **leaderboard governance 已回到健康雙角色治理**：`hb_leaderboard_candidate_probe.py` 與 `/api/models/leaderboard` 現在顯示 `dual_profile_state=leaderboard_global_winner_vs_train_support_fallback`、`governance_contract=dual_role_governance_active`；global 排名保留 `core_only`，production 配置改為 `core_plus_macro`。
- **Strategy Lab / Execution diagnostics 已同步最新 current-live truth**：瀏覽器 `/lab` 與 `/execution/status` 都顯示 circuit-breaker-first blocker、support `41/50`、bull exact-vs-spillover 對照，以及 venue readiness blockers。

---

## 主目標

### 目標 A：維持 breaker release math 作為唯一 current-live 真相，直到真正解除
**目前真相**
- canonical `1440m` recent `50` 只贏 `0/50`
- `streak=137`
- 距離 release floor `15/50` 還差 `15` 勝
- `allowed_layers=0`

**成功標準**
- 要嘛 recent `50` 提升到 `>=15` 勝且 breaker 解除；
- 要嘛所有 operator / heartbeat / docs 都只把 breaker release math 當成唯一 current-live blocker。

### 目標 B：把 q15 under-minimum support 維持在正確的 support-aware production fallback，而不是再回退成 stale exact-supported 敘事
**目前真相**
- `current_live_structure_bucket_rows=41 / minimum_support_rows=50`
- `support_progress.status=stalled_under_minimum`
- `train_selected_profile=core_plus_macro`
- `train_selected_profile_source=bull_4h_pocket_ablation.support_aware_profile`
- `leaderboard_selected_profile=core_only`
- `dual_profile_state=leaderboard_global_winner_vs_train_support_fallback`

**成功標準**
- 在 exact bucket `<50` rows 期間，train metadata、candidate probe、API payload、`/lab` governance banner 全部一致承認 support-aware production fallback；
- 若 exact bucket 回到 `>=50` rows`，再由 full refresh 把 production profile 升回 exact-supported 路徑。

### 目標 C：把 bull exact-vs-spillover pathology 轉成正式 patch
**目前真相**
- exact live lane：`41 rows / WR=100% / quality=0.697 / pnl=+2.20%`
- broader spillover：`bull|ALLOW 159 rows / WR=0% / quality=-0.276 / pnl=-1.03%`
- recent pathology 仍是 `100x0`
- top shifts 仍集中在 `feat_4h_bias200 / feat_4h_dist_swing_low / feat_4h_dist_bb_lower`

**成功標準**
- 能清楚指出為何 broader bull spillover 仍污染 current-live 決策，並把它落成 gate / calibration / training 的可重跑 patch；
- 對應 patch 必須能用 drilldown artifact、probe、pytest、browser surface 重跑驗證。

### 目標 D：保持 execution/runtime/operator surface 同步，且不掩蓋 venue blocker
**目前真相**
- `/lab` 與 `/execution/status` 已同步顯示 circuit breaker、support `41/50`、exact-vs-spillover 對照
- venue blockers 仍是：credential / order ack / fill lifecycle 尚未驗證

**成功標準**
- 即使 breaker 將來解除，operator surface 仍必須保留 venue readiness blocker，直到 runtime 證據真的 closure。

---

## 下一步
1. **持續用 support-aware production fallback 治理 q15 under-minimum support，直到 exact bucket 補滿 50 rows**
   - 驗證：`python scripts/hb_leaderboard_candidate_probe.py`、`python scripts/hb_model_leaderboard_api_probe.py`、`python scripts/hb_predict_probe.py`、瀏覽器 `/lab` 模型排行榜治理卡
2. **把 bull|ALLOW spillover 159 rows 轉成可重跑 patch，而不是只停在可視化**
   - 驗證：`data/live_decision_quality_drilldown.json`、`python scripts/hb_predict_probe.py`、targeted pytest、瀏覽器 `/lab` 的 `🧬 Live lane / spillover 對照`
3. **持續維持 breaker-first truth 與 venue blockers 同步可見**
   - 驗證：`python scripts/hb_predict_probe.py`、瀏覽器 `/lab`、`/execution/status`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- q15 support / train profile / leaderboard governance 對 `41/50 under minimum support` 的 machine-read truth 完全一致，且 production fallback 明確為 support-aware `core_plus_macro`
- bull exact-vs-spillover pathology 有可重跑、可驗證的 root cause / patch / regression evidence
- heartbeat 維持：**issue 對齊 → 主動修復 P0/P1 → verify → docs overwrite → commit → push**
