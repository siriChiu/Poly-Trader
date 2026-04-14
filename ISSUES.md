# ISSUES.md — Current State Only

_最後更新：2026-04-14 13:39 UTC — Heartbeat #729（修正 leaderboard candidate probe warning hygiene）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#728）要求本輪處理
- **Next focus**：
  1. 追蹤 bull `CAUTION|structure_quality_caution|q35` exact bucket 是否仍為 0 rows；
  2. 持續維持 `core_only`（leaderboard winner）與 `core_plus_macro`（train fallback）雙軌語義對齊；
  3. 視需要處理 leaderboard probe / fast heartbeat 的 warning hygiene。
- **Success gate**：
  1. next run 能直接指出 `leaderboard_candidate_diagnostics.dual_profile_state` 與 `blocked_candidate_profiles`；
  2. bull live exact bucket 0-support 的狀態，在 live probe / bull pocket artifact / leaderboard probe / docs 之間零漂移；
  3. 若 exact bucket rows 有變化，四條路徑能同輪同步更新結論。
- **Fallback if fail**：
  - exact bucket 若仍 0 support，維持 `0 layers`；
  - 若 candidate probe 或 summary 缺欄位 / 漂移，下一輪先修 contract；
  - 若 warning hygiene 未修，至少不得讓 warnings 蓋掉真正錯誤。

### 本輪承接結果
- **已處理**：
  - bull exact bucket 仍為 **0 rows**，本輪已再次用 `data/live_predict_probe.json`、`data/bull_4h_pocket_ablation.json`、`data/leaderboard_feature_profile_probe.json`、`data/heartbeat_729_summary.json` 四條路徑交叉確認，結論一致。
  - `core_only`（leaderboard winner）與 `core_plus_macro`（train support-aware fallback）雙軌語義仍維持 machine-readable 對齊。
  - **warning hygiene 已實修**：`scripts/hb_leaderboard_candidate_probe.py` 現在會抑制已知 sklearn feature-name warnings，fast heartbeat stderr 不再被大量無害警告淹沒。
- **仍未解**：
  - bull live exact bucket `CAUTION|structure_quality_caution|q35` 仍是 **0 rows**，runtime 仍必須維持 `0 layers`。
  - `core_plus_macro` 仍只是 **train support-aware fallback**，不是可部署的 leaderboard winner。
  - `fin_netflow` 仍是 **auth_missing**。
- **本輪明確不做**：
  - 不放寬 bull live guardrail。
  - 不把 broader spillover lane 當成 exact bucket 已修好。
  - 不把 `fin_netflow` auth blocker 誤包裝成本地 calibration 問題。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_leaderboard_candidate_probe.py`
    - 新增 `_suppress_known_feature_name_warnings()`，針對已知 sklearn `X has feature names, but ... was fitted without feature names` warnings 做精準抑制。
    - 目標：讓 heartbeat / cron stderr 保留真實錯誤，而不是被 probe 評估過程的無害警告洗版。
  - `tests/test_hb_leaderboard_candidate_probe.py`
    - 新增 regression test，鎖住上述 warning hygiene 行為。
  - `ARCHITECTURE.md`
    - 同步 fast-heartbeat / leaderboard candidate probe 的 warning hygiene contract。

- **驗證（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **10 passed**
  - `source venv/bin/activate && python scripts/hb_leaderboard_candidate_probe.py >/tmp/hb_leaderboard_probe.out 2>/tmp/hb_leaderboard_probe.err` → **stderr 0 行**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 729` → **通過**

### 資料 / 新鮮度 / canonical target
來自 Heartbeat #729：
- Raw / Features / Labels：**21410 / 12839 / 42914**
- 本輪增量：**+1 raw / +1 features / +2 labels**
- canonical target `simulated_pyramid_win`：**0.5749**
- 240m labels：**21558 rows / target_rows 12636 / lag_vs_raw 3.0h**
- 1440m labels：**12271 rows / target_rows 12271 / lag_vs_raw 23.4h**
- recent raw age：**約 4.2 分鐘**
- continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**17/30 pass**
- TW-IC：**26/30 pass**
- TW 歷史：**#729=26/30，#728=26/30，#727=24/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 4/8**
- primary drift window：**recent 250**
  - alerts：`constant_target`, `regime_concentration`
  - interpretation：**supported_extreme_trend**
  - win_rate：**1.0000**
  - dominant_regime：**chop 100%**
  - avg_quality：**0.6662**
  - avg_pnl：**+0.0206**
  - avg_drawdown_penalty：**0.0353**
- 判讀：近期 canonical 視窗仍是**被支持的極端趨勢視窗**，不是 bull exact bucket 已修好的證據。

### 模型 / shrinkage / leaderboard candidate 對齊
- `model/last_metrics.json`
  - train profile：**`core_plus_macro`**
  - source：**`bull_4h_pocket_ablation.support_aware_profile`**
  - support cohort：**`bull_supported_neighbor_buckets_proxy`**
  - support rows：**84**
  - exact live bucket rows：**0**
  - train accuracy / CV：**0.6333 / 0.7530**
- `data/feature_group_ablation.json`
  - global recommended profile：**`core_only`**
  - `current_full` cv：**0.5767**
- `data/leaderboard_feature_profile_probe.json`
  - leaderboard selected profile：**`core_only`**
  - dual profile state：**`leaderboard_global_winner_vs_train_support_fallback`**
  - blocked candidate：**`core_plus_macro` → `unsupported_exact_live_structure_bucket`**
  - bull support-aware profile：**`core_plus_macro`**
  - bull supported-neighbor rows：**84**
  - live current structure bucket rows：**0**
- 判讀：**雙軌語義仍穩定對齊**；本輪改善的是 console / cron 可讀性，不是 bull blocker root cause 本身。

### Live predictor / bull blocker
來自 `data/live_predict_probe.json`：
- signal：**HOLD**
- confidence：**0.18663**
- regime：**bull**
- gate：**CAUTION**
- entry quality：**0.4139 (D)**
- allowed layers：**0 → 0**
- should trade：**false**
- calibration scope：**`regime_label`**
- execution guardrail：
  - `decision_quality_below_trade_floor`
  - `unsupported_exact_live_structure_bucket_blocks_trade`
- exact live lane：**17 rows / win_rate 0.2353 / quality -0.0626 / true_negative_rows 13 (76.47%)**
- worst narrowed scope：**`regime_label+entry_quality_label` = 147 rows / win_rate 0.0748 / quality -0.2098**
- current live structure bucket：**`CAUTION|structure_quality_caution|q35` rows = 0**
- 判讀：guardrail 仍是在**正確擋壞 pocket**，不是過度保守。

### Source blockers
- blocked sparse features：**8 個**
- blocker 分布：
  - `archive_required`: **3**
  - `snapshot_only`: **4**
  - `short_window_public_api`: **1**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）
- 判讀：這仍是**外部授權 blocker**。

---

## 目前有效問題

### P1. bull live exact bucket 仍是 0-support，runtime 必須維持 0 layers
**現象**
- live 仍是 **bull / CAUTION / D / 0 layers**。
- `unsupported_exact_live_structure_bucket_blocks_trade` 仍成立。
- current live structure bucket：`CAUTION|structure_quality_caution|q35`
- `data/bull_4h_pocket_ablation.json`：**current_live_structure_bucket_rows = 0**
- `data/live_predict_probe.json`：exact live lane **17 rows**，且 quality 為負。

**判讀**
- 目前 blocker 不是 contract / warnings / 文件漂移，而是**exact bucket 本身沒有可用支持樣本**。
- 任何 broader lane 的較高 win rate，都不能當成 exact bucket 已可部署。

**下一步方向**
- 維持 `0 layers`。
- 下一輪直接推進 **bull exact bucket 支持樣本治理**，不能再只重報 0-support。

---

### P1. train fallback 與 leaderboard winner 仍是雙軌，語義已對齊但尚未收斂到同一條可部署路徑
**現象**
- train path：**`core_plus_macro`**（support-aware fallback）
- leaderboard winner：**`core_only`**（global shrinkage winner）
- `data/leaderboard_feature_profile_probe.json` 已明確輸出：
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `blocked_candidate_profiles[0].blocker_reason = unsupported_exact_live_structure_bucket`

**判讀**
- 語義治理已完成，但**根本衝突仍存在**：train fallback 仍依賴 bull supported-neighbor proxy，而不是 exact live bucket 自身支持。

**下一步方向**
- 若 exact bucket 仍 0，維持雙 baseline；不得把 `core_plus_macro` 誤寫成已被 leaderboard 正式選中。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- forward archive 雖然 ready，但內容仍是 auth_missing snapshot。

**判讀**
- 這仍是**外部憑證缺失 blocker**。
- 未補憑證前，不應列為主決策成熟特徵。

---

## 本輪已清掉的問題

### RESOLVED. leaderboard candidate probe / fast heartbeat warning hygiene
**現象（上輪）**
- `scripts/hb_leaderboard_candidate_probe.py` 與 fast heartbeat 在 stderr 中會大量出現 sklearn feature-name warnings，污染 cron 摘要可讀性。

**本輪 patch + 證據**
- `scripts/hb_leaderboard_candidate_probe.py` 已新增精準 warning suppression。
- 實測 `python scripts/hb_leaderboard_candidate_probe.py` → **stderr 0 行**。
- regression test 已加入並通過。

**狀態**
- **已修復**；除非 warnings 再次回來或遮蔽真錯誤，否則下一輪不再作為主目標。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **重新確認 bull exact bucket / dual-profile 語義是否漂移**。✅
2. **實修 leaderboard candidate probe warning hygiene**，避免 fast heartbeat stderr 被無害警告淹沒。✅
3. **用 #729 事實覆寫 ISSUES / ROADMAP / ARCHITECTURE**，把本輪 patch 與 blocker 狀態同步。✅

### 本輪不做
- 不放寬 bull live guardrail。
- 不把 broader spillover lane 當作 exact bucket 已修好。
- 不把 `fin_netflow` auth blocker 當本地 code 問題。

---

## 下一輪 gate

- **Next focus:**
  1. 直接推進 **bull exact bucket 支持樣本治理**，不要再只做 blocker 重報；
  2. 持續維持 `core_only`（leaderboard winner）與 `core_plus_macro`（train fallback）雙軌語義零漂移；
  3. 繼續把 `fin_netflow` 當外部 source blocker 顯式管理。

- **Success gate:**
  1. next run 必須留下至少一個與 **bull exact bucket 支持樣本治理** 直接相關的 patch / artifact / verify；
  2. 若 exact bucket 仍 0，heartbeat 必須明確維持 `0 layers` 並指出 blocker 未解；若 >0，必須同輪同步更新 live probe / bull pocket / leaderboard probe / docs；
  3. 文件、probe、heartbeat summary 對 `core_only`、`core_plus_macro`、bull blocker 的敘述零漂移。

- **Fallback if fail:**
  - 若 exact bucket 仍 0 support 且本輪無法直接補樣本，下一輪必須至少把 **支持樣本治理路徑** machine-readable 化（例如 exact bucket source / join / selection contract），不得再回到 warning hygiene 或一般敘述性報告；
  - 若 probe / summary 再次缺欄位或漂移，下一輪優先修 contract；
  - 若 `fin_netflow` auth 未修，持續標記 blocked，不准把 coverage 改善寫成既成事實。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - 若 bull exact bucket governance contract 再變，更新 `ARCHITECTURE.md`

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_729_summary.json`、`data/leaderboard_feature_profile_probe.json`、`data/live_predict_probe.json`、`data/bull_4h_pocket_ablation.json`。
  2. 逐條確認：
     - `leaderboard_candidate_diagnostics.selected_feature_profile` 是否仍為 `core_only`；
     - `leaderboard_candidate_diagnostics.dual_profile_state` 是否仍為 `leaderboard_global_winner_vs_train_support_fallback`；
     - `leaderboard_candidate_diagnostics.live_current_structure_bucket_rows` 是否仍為 0；
     - `leaderboard_candidate_diagnostics.blocked_candidate_profiles[0].blocker_reason` 是否仍為 `unsupported_exact_live_structure_bucket`；
     - `live_predict_probe.execution_guardrail_reason` 是否仍包含 `unsupported_exact_live_structure_bucket_blocks_trade`。
  3. 若以上五項有四項以上完全不變，下一輪不得只重跑 fast heartbeat；必須直接推進 **bull exact bucket 支持樣本治理**。