# ROADMAP.md — Current Plan Only

_最後更新：2026-04-19 02:58 CST_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留歷史 roadmap 流水帳。

---

## 已完成
- **bull q15 bias50 fail-close veto 已落地到 live + backtest**：`model/predictor.py` 與 `backtesting/strategy_lab.py` 已共用 `bull_q15_bias50_overextended_block` 規則，避免 stretched q15 bounce 再被包裝成可部署 `CAUTION` lane。
- **exact-live-lane vs spillover operator surface 已落地**：`/api/status` 現在會輸出 `decision_quality_scope_pathology_summary`，Dashboard 與 Strategy Lab 都已直接顯示 `🧬 Live lane / spillover 對照` 卡片，並已用瀏覽器驗證路由可達、內容可見、console 無錯。
- **fast heartbeat 仍維持閉環**：本輪 `Raw=31031 / Features=22449 / Labels=62297`，新增 `+2 / +2 / +11`，證明資料管線仍在前進，不是 frozen 狀態。

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

### 目標 B：把 bull exact-lane vs spillover pathology 轉成正式 patch
**目前真相**
- current live bucket = `BLOCK|bull_q15_bias50_overextended_block|q15`
- exact live lane：`41 rows / WR=100% / quality=0.697`
- broader spillover：`bull|ALLOW` 額外 `159 rows / WR=0% / quality=-0.276`
- recent canonical `100` rows 仍是 `100x0`
- top shifts：`feat_4h_bias200 / feat_4h_dist_swing_low / feat_4h_dist_bb_lower`

**成功標準**
- 能清楚指出為何 broader bull spillover 仍污染 current-live 決策，並把它落成 gate / calibration / training 的可重跑 patch；
- 對應 patch 必須能用 `recent_drift_report.py` / `hb_predict_probe.py` / targeted pytest / browser surface 重跑驗證。

### 目標 C：刷新 stale-under-minimum 的 support-aware profile / leaderboard governance
**目前真相**
- `dual_profile_state=train_exact_supported_profile_stale_under_minimum`
- `governance_contract=train_profile_contract_stale_against_current_support`
- `live_current_structure_bucket_rows=41 / minimum_support_rows=50`
- `/api/models/leaderboard` 目前 `comparable_count=0 / placeholder_count=4`
- `hb_leaderboard_candidate_probe.py` 直接執行仍 timeout-prone

**成功標準**
- train metadata、candidate probe、leaderboard governance 三者都回到 `under minimum support` 的同一套敘事；
- `/lab` 與 API 不再殘留「exact-supported production profile 已 closure」的舊語義。

### 目標 D：保持 execution/runtime/operator surface 同步，且不掩蓋 venue blocker
**目前真相**
- `/api/status`、Dashboard、Strategy Lab 都已同步顯示 breaker / venue blockers / live lane vs spillover
- live exchange credential / order ack / fill lifecycle 仍未驗證

**成功標準**
- 即使 breaker 將來解除，operator surface 仍必須保留 venue readiness blocker，直到 runtime 證據真的 closure。

---

## 下一步
1. **把 broader bull spillover 159 rows 轉成 root-cause patch，而不是只停在可視化**
   - 驗證：`python scripts/recent_drift_report.py`、`python scripts/hb_predict_probe.py`、`PYTHONPATH=. pytest tests/test_api_feature_history_and_predictor.py tests/test_strategy_lab.py -q`
2. **重跑 support-aware profile / leaderboard governance refresh，消除 stale-under-minimum 敘事**
   - 驗證：`python scripts/hb_model_leaderboard_api_probe.py`、`python scripts/hb_leaderboard_candidate_probe.py`、`PYTHONPATH=. pytest tests/test_model_leaderboard_api_cache.py -q`、瀏覽器 `/lab`
3. **持續保留 breaker-first truth 與 venue blockers 同步可見**
   - 驗證：瀏覽器 `/`、`/lab`、`/execution/status` 與 `/api/status`

---

## 成功標準
- current-live blocker 清楚且唯一：**breaker release math**
- bull exact-lane vs spillover pathology 有可重跑、可驗證的 root cause / patch / regression evidence
- train / leaderboard governance 不再殘留 stale exact-supported production profile 敘事
- heartbeat 維持：**issue 對齊 → 主動修復 P0/P1 → verify → docs overwrite → commit → push**
