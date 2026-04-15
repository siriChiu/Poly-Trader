# ISSUES.md — Current State Only

_最後更新：2026-04-15 00:40 UTC — Heartbeat #747（本輪已把 **global shrinkage winner vs production bull profile** 正式 machine-read 化：leaderboard probe / fast heartbeat summary 現在會明確輸出 `profile_split={global_profile_role, production_profile_role, verdict}`，不再只靠人工解讀 `core_only` vs `core_plus_macro_plus_4h_structure_shift` 的分工。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 上輪（#746）要求本輪處理
- **Next focus**：
  1. 驗證 `feat_4h_bias50` 與 q35 4H structure scaling 是否過度懲罰 bull current lane；
  2. 把 global `core_only` 與 production `core_plus_macro_plus_4h_structure_shift` 正式定義成不同治理角色；
  3. 持續把 `fin_netflow` 當外部 source blocker 管理。
- **Success gate**：
  1. 至少留下 1 個與 **bias50 / q35 structure scaling / production profile split** 直接相關的 patch / artifact / verify；
  2. `train_selected_profile / leaderboard_selected_profile / dual_profile_state / support_blocker_state / proxy_boundary_verdict / decision_quality_exact_live_lane_bucket_verdict / allowed_layers_reason / entry_quality_components` 在 artifact / docs / summary 間零漂移；
  3. 若 q35 仍是 `CAUTION / D / 0-layer`，必須同輪明確回答：這是「公式過嚴」還是「hold-only lane 正確治理」。
- **Fallback if fail**：
  - 若 `entry_quality_components` 再次缺失，視為 live semantics regression；
  - 若 exact-lane verdict 又回退成 `sub_buckets_present_but_not_toxic`，視為 diagnostic regression；
  - 若 train / leaderboard 再次分裂，立刻回升為 `exact_supported_train_frame_parity_blocker`；
  - 若 source auth 未修，持續標記 blocked，不准寫成即將恢復。

### 本輪承接結果
- **已處理**：
  - `scripts/hb_leaderboard_candidate_probe.py`
    - 新增 `profile_split`：
      - `global_profile / global_profile_role`
      - `production_profile / production_profile_role`
      - `split_required / verdict / reason`
    - 讓 `core_only` 與 `core_plus_macro_plus_4h_structure_shift` 的分工從人工解讀升級為可機器檢查的治理契約。
  - `scripts/hb_parallel_runner.py`
    - `feature_ablation.profile_role` 已顯式標記 global shrinkage winner；
    - `bull_4h_pocket_ablation.production_profile_role` 已顯式標記 production bull profile；
    - `leaderboard_candidate_diagnostics.profile_split` 已同步進 heartbeat summary。
  - `tests/test_hb_parallel_runner.py`
    - 新增 regression，鎖住上述三組新欄位，避免之後又退回「只有 profile 名稱、沒有治理語義」。
- **驗證已完成**：
  - `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py -q` → **11 passed**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 747` → **通過**
- **本輪前提更新**：
  - live current path 仍是 `bull / CAUTION / D / allowed_layers=0`；
  - 但現在不只知道 global/profile 不同，還能明確 machine-read：
    - `global_profile = core_only`
    - `global_profile_role = global_shrinkage_winner`
    - `production_profile = core_plus_macro_plus_4h_structure_shift`
    - `production_profile_role = bull_exact_supported_production_profile`
    - `profile_split.verdict = dual_role_required`
  - 也就是說：**profile split 不是 drift/blocker，而是刻意保留的雙軌治理。**
- **本輪明確不做**：
  - 不在證據不足時直接調低 q35 `trade_floor`；
  - 不把 exact lane 的 90-row 高勝率直接翻譯成「現在該放行」；
  - 不把 `fin_netflow` auth 缺失混成 q35 lane root cause。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_leaderboard_candidate_probe.py`
  - `scripts/hb_parallel_runner.py`
  - `tests/test_hb_parallel_runner.py`
- **Tests（已通過）**
  - `source venv/bin/activate && python -m pytest tests/test_hb_parallel_runner.py -q` → **11 passed**
- **Runtime verify（已通過）**
  - `source venv/bin/activate && python scripts/hb_parallel_runner.py --fast --hb 747`
- **已刷新 artifacts**
  - `data/heartbeat_747_summary.json`
  - `data/full_ic_result.json`
  - `data/ic_regime_analysis.json`
  - `data/recent_drift_report.json`
  - `data/live_predict_probe.json`
  - `data/live_decision_quality_drilldown.json`
  - `data/feature_group_ablation.json`
  - `data/bull_4h_pocket_ablation.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `model/ic_signs.json`

### 資料 / 新鮮度 / canonical target
- 來自 Heartbeat #747：
  - Raw / Features / Labels：**21438 / 12867 / 43061**
  - 本輪增量：**+1 raw / +1 feature / +4 labels**
  - canonical target `simulated_pyramid_win`：**0.5766**
  - 240m labels：**21587 rows / target_rows 12665 / lag_vs_raw 3.1h**
  - 1440m labels：**12389 rows / target_rows 12389 / lag_vs_raw 23.2h**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / regime / drift
- Global IC：**19/30 pass**
- TW-IC：**25/30 pass**
- TW 歷史：**#747=25/30，#746=25/30，#745=25/30**
- Regime IC：**Bear 4/8 / Bull 6/8 / Chop 5/8**
- primary drift window：**recent 100**
  - alerts：`label_imbalance`, `regime_concentration`, `regime_shift`
  - interpretation：**supported_extreme_trend**
  - dominant_regime：**bull 98.0%**
  - win_rate：**0.9700**
  - avg_quality：**0.6773**
  - avg_pnl：**+0.0213**
  - avg_drawdown_penalty：**0.0337**
- 判讀：recent canonical pocket 仍健康；目前 blocker 仍是 live q35 runtime entry-quality，而不是 target pathology。

### Train / leaderboard / live contract
- `model/last_metrics.json`
  - `feature_profile = core_plus_macro_plus_4h_structure_shift`
  - Train=`67.5%`
  - CV=`71.7% ± 9.9pp`
  - `n_features = 21`
- `data/feature_group_ablation.json`
  - `recommended_profile = core_only`
  - `profile_role.role = global_shrinkage_winner`
- `data/bull_4h_pocket_ablation.json`
  - `bull_all.recommended_profile = core_plus_macro_plus_4h_structure_shift`
  - `production_profile_role.role = bull_exact_supported_production_profile`
  - `production_profile_role.support_cohort = bull_all`
  - `production_profile_role.exact_live_bucket_rows = 90`
- `data/leaderboard_feature_profile_probe.json`
  - `train_selected_profile = core_plus_macro_plus_4h_structure_shift`
  - `leaderboard_selected_profile = core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = aligned`
  - `profile_split.verdict = dual_role_required`
  - `profile_split.global_profile = core_only`
  - `profile_split.production_profile = core_plus_macro_plus_4h_structure_shift`
  - `support_blocker_state = exact_live_bucket_supported`
  - `proxy_boundary_verdict = exact_bucket_supported_proxy_not_required`
  - `exact_lane_bucket_verdict = no_exact_lane_sub_bucket_split`
- `data/live_predict_probe.json`
  - signal：**HOLD**
  - confidence：**0.4545**
  - regime：**bull**
  - gate：**CAUTION**
  - entry quality：**0.3726 (D)**
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `execution_guardrail_applied = false`
  - chosen scope：**`regime_label+entry_quality_label` / sample_size=103**
  - exact live lane：**90 rows / win=1.0 / quality=0.7033 / verdict=no_exact_lane_sub_bucket_split**
  - entry-quality decomposition：
    - `base_quality = 0.3450`
    - `structure_quality = 0.4553`
    - `trade_floor_gap = -0.1774`
    - 最大 base blocker：`feat_4h_bias50 = 3.7318 -> normalized_score 0.0`
    - 次要 blocker：`feat_nose = 0.5965 -> 0.4035`、`feat_pulse = 0.4742 -> 0.4742`
    - 健康 base component：`feat_ear = -0.0076 -> 0.9621`
- 判讀：**runtime 仍不放行，主因仍是 raw entry-quality 不達 0.55；但 profile split 已從「看起來矛盾」收斂成「雙軌治理」。**

### Source blockers
- blocked sparse features：**8 個**
- 最關鍵 source blocker：
  - `fin_netflow`：**auth_missing**（缺 `COINGLASS_API_KEY`）

---

## 目前有效問題

### P1. bull q35 current lane 仍是 `CAUTION / D / 0-layer`，但現在要直接回答「公式過嚴」還是「hold-only 正確治理」
**現象**
- exact live lane 目前有 **90 rows**，`win_rate=1.0 / avg_quality=0.7033`；
- 但 current live row 仍是：
  - `entry_quality = 0.3726`
  - `trade_floor_gap = -0.1774`
  - `allowed_layers_reason = entry_quality_below_trade_floor`
  - `execution_guardrail_applied = false`

**component-level 證據**
- `feat_4h_bias50 = 3.7318` → normalized score **0.0**（最大拖累）
- `feat_nose = 0.5965` → normalized score **0.4035**
- `feat_pulse = 0.4742` → normalized score **0.4742**
- `feat_ear = -0.0076` → normalized score **0.9621**（健康，不是 blocker）
- 4H structure：
  - `feat_4h_bb_pct_b = 0.5859`
  - `feat_4h_dist_bb_lower = 1.8400`
  - `feat_4h_dist_swing_low = 5.4610`
  - `structure_quality = 0.4553`

**判讀**
- 這條 q35 lane 已不再是 support blocker；
- 真正待判定的是：
  1. `feat_4h_bias50` 的過熱懲罰是否真的過陡；
  2. q35 structure scaling 是否把可放行 lane 壓成 D；
  3. 若兩者都不成立，就應正式把這類 current row 標成 hold-only。 

---

### P1. global shrinkage winner 與 production bull profile 已證明是「雙軌治理」，但仍需往更多 surface 擴散
**現象**
- `global_recommended_profile = core_only`
- `production_profile = core_plus_macro_plus_4h_structure_shift`
- 新 artifact 已明確輸出：
  - `profile_split.verdict = dual_role_required`
  - `global_profile_role = global_shrinkage_winner`
  - `production_profile_role = bull_exact_supported_production_profile`

**判讀**
- 這不再是 train/leaderboard 對齊問題；
- 現在剩下的是把這組雙軌語義持續同步到 docs / summary /後續 probe，避免未來再被誤寫成 drift/blocker。

---

### P1. `fin_netflow` auth blocker 仍卡住 sparse-source 成熟度
**現象**
- `fin_netflow` coverage：**0.0%**
- latest status：**auth_missing**
- archive_window_coverage：**0.0% (0/1567)**

**判讀**
- 這仍是**外部憑證 blocker**，不是 bull live lane 問題。

---

## 本輪已清掉的問題

### RESOLVED. `core_only` vs `core_plus_macro_plus_4h_structure_shift` 只有 profile 名稱，沒有 machine-readable 治理語義
**修前**
- heartbeat / probe 只看得到兩個 profile 名稱；
- 需要人工猜測「哪個是 global winner、哪個是 production winner」。

**本輪 patch + 證據**
- `scripts/hb_leaderboard_candidate_probe.py`
  - 新增 `profile_split`，直接輸出 `global_profile_role / production_profile_role / verdict / reason`
- `scripts/hb_parallel_runner.py`
  - `feature_ablation.profile_role`
  - `bull_4h_pocket_ablation.production_profile_role`
  - `leaderboard_candidate_diagnostics.profile_split`
- `python -m pytest tests/test_hb_parallel_runner.py -q`
  - **11 passed**
- `python scripts/hb_parallel_runner.py --fast --hb 747`
  - `data/leaderboard_feature_profile_probe.json` 已出現：
    - `profile_split.verdict = dual_role_required`
    - `global_profile_role = global_shrinkage_winner`
    - `production_profile_role = bull_exact_supported_production_profile`

**狀態**
- **已修復**：這組雙軌治理已正式 machine-read；後續 heartbeat 不得再把它寫成抽象「global 跟 production 看起來不同」。

---

## 本輪決策（收斂版）

### 本輪要推進的 3 件事
1. **把 global winner vs production winner 正式 machine-read 化。** ✅
2. **重新跑 fast heartbeat，驗證這組新語義真的進入 summary / probe / artifacts。** ✅
3. **把 live q35 blocker 收斂成下一輪的公式判定題：bias50 / structure scaling vs hold-only。** ✅

### 本輪不做
- 不直接修改 `trade_floor`；
- 不直接放寬 q35 gate；
- 不把 source auth blocker 混進 live q35 root cause。

---

## 下一輪 gate

- **Next focus:**
  1. 直接驗證 `feat_4h_bias50` 與 q35 structure scaling 是否過度懲罰 bull current lane；
  2. 若證據不支持放寬，明確把這類 q35 current row 定義成 hold-only lane；
  3. 維持 `profile_split` 與 `fin_netflow` blocker 的零漂移治理。

- **Success gate:**
  1. next run 必須留下至少一個與 **bias50 scaling / q35 structure scaling / hold-only verdict** 直接相關的 patch / artifact / verify；
  2. `profile_split / global_profile_role / production_profile_role / train_selected_profile / leaderboard_selected_profile / dual_profile_state / support_blocker_state / proxy_boundary_verdict / allowed_layers_reason / entry_quality_components` 在 artifact / docs / summary 間零漂移；
  3. 必須同輪明確回答：目前的 `CAUTION / D / 0-layer` 是公式過嚴，還是正確保守治理。

- **Fallback if fail:**
  - 若 `profile_split` 在任何 surface 消失，視為 governance regression；
  - 若 exact-lane verdict 回退或 train/leaderboard 再分裂，立刻回升為 blocker；
  - 若 scaling audit 做不出結論，下一輪必須新增更直接的 lane-level audit artifact，而不是只重述現象；
  - 若 source auth 未修，持續標記 blocked，不准寫成即將恢復。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若新增 scaling / hold-only contract）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_747_summary.json`
  2. 再讀：
     - `data/live_predict_probe.json`
     - `data/live_decision_quality_drilldown.json`
     - `data/feature_group_ablation.json`
     - `data/bull_4h_pocket_ablation.json`
     - `data/leaderboard_feature_profile_probe.json`
  3. 若下輪仍同時看到：
     - `regime_gate = CAUTION`
     - `entry_quality_label = D`
     - `allowed_layers_reason = entry_quality_below_trade_floor`
     - `execution_guardrail_applied = false`
     - `entry_quality_components.base_components[feat_4h_bias50].normalized_score = 0.0`
     - `profile_split.verdict = dual_role_required`
     - `global_profile = core_only`
     - `production_profile = core_plus_macro_plus_4h_structure_shift`
     - `support_blocker_state = exact_live_bucket_supported`
     則不得再只說「trade floor 太低」；必須直接推進 **bias50 scaling / q35 structure scaling / hold-only verdict**，並保留 `profile_split` / source blocker 的顯式治理。
