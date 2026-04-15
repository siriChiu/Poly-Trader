# ISSUES.md — Current State Only

_最後更新：2026-04-15 20:41 UTC — Heartbeat #fast（本輪已把 **profile governance 的單一 machine-read 解釋** 落地到 `scripts/hb_leaderboard_candidate_probe.py` 與 `hb_parallel_runner.py`。現在 `leaderboard_feature_profile_probe.json` / `heartbeat_fast_summary.json` 會明確輸出 `governance_contract={verdict,current_closure,treat_as_parity_blocker,recommended_action,...}`，把 `leaderboard_global_winner_vs_train_support_fallback` 明確定義為 **雙角色治理**，而不是未解 parity drift。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 收斂 `leaderboard_global_winner_vs_train_support_fallback` 的 profile governance，讓 leaderboard / train / heartbeat summary 對雙角色 profile 有單一 machine-read 解釋；
  2. 持續追蹤 q15 exact support，只有 current live row 回到 q15 lane 且 exact rows 達標後，才升級 q15 component route；
  3. 維持 q35 same-run alignment，不得讓 stale probe / stale artifact regression 回來。
- **Success gate**
  1. 至少留下 1 個與 **profile governance 收斂** 或 **q15 exact support readiness** 直接相關的 patch / artifact / verify；
  2. `heartbeat_fast_summary.json` 仍維持 q35 `entry_quality>=0.55`、`allowed_layers>0`、`live_predict_probe.allowed_layers=1`；
  3. `leaderboard_feature_profile_probe.alignment.dual_profile_state` 必須被文件與 summary 明確解釋為雙角色治理，而不是未解 parity drift。
- **Fallback if fail**
  - 若 q35 same-run alignment 再次退化，回查 `hb_q35_scaling_audit.py` second-pass refresh；
  - 若 profile governance 仍無法收斂，升級成專門的 governance contract blocker；
  - 若 q15 current live row 仍 inactive，禁止把 q15 standby route 寫成主 closure。

### 本輪承接結果
- **已處理**
  - `scripts/hb_leaderboard_candidate_probe.py`
    - 新增 `_build_governance_contract()`，把 `dual_profile_state + profile_split + support_governance_route` 收斂成單一 machine-read 治理結論；
    - 讓 probe 直接輸出 `governance_contract.verdict/current_closure/treat_as_parity_blocker/recommended_action`。
  - `scripts/hb_parallel_runner.py`
    - `collect_leaderboard_candidate_diagnostics()` 現在會把 `governance_contract` 同步帶進 heartbeat summary；
    - fast heartbeat 產物已可直接 machine-read「這是雙角色治理，不是 parity drift」。
  - `tests/test_hb_leaderboard_candidate_probe.py`
    - 補 dual-role 與 post-threshold stalled 兩條治理 contract regression。
  - `tests/test_hb_parallel_runner.py`
    - 補 heartbeat summary / diagnostics 對 `governance_contract` 的持久化 regression。
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **40 passed**
  - `/home/kazuha/Poly-Trader/venv/bin/python scripts/hb_parallel_runner.py --fast` → **通過**
- **本輪 machine-read 結論**
  - `leaderboard_feature_profile_probe.alignment.dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `leaderboard_feature_profile_probe.alignment.governance_contract = {`
    - `verdict = dual_role_governance_active`
    - `current_closure = global_ranking_vs_support_aware_production_split`
    - `treat_as_parity_blocker = false`
    - `support_governance_route = exact_live_bucket_present_but_below_minimum`
    - `live_current_structure_bucket_rows = 15 / minimum_support_rows = 50`
    - `recommended_action = 文件與 heartbeat 應把 split 明寫為雙角色治理；在 exact support 未達標前，不要把 production profile fallback 誤報為 parity blocker。`
    - `}`
  - `heartbeat_fast_summary.json` 已同步帶出同一份 `governance_contract`
  - q35 current live path 仍保持：`entry_quality=0.5675 / allowed_layers=1 / q35_discriminative_redesign_applied=true`
- **本輪明確不做**
  - 不把 q15 standby route 拉回主 closure；current live row 仍不是 q15 lane。
  - 不先處理 sparse-source auth；`fin_netflow` 仍是 source blocker，但不是本輪主 closure。
  - 不在本輪把 leaderboard ranking policy 直接切到 production profile；先把治理語義 machine-read 化，再決定是否升級成 post-threshold sync issue。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_leaderboard_candidate_probe.py`：新增 `governance_contract`，把 dual-role / stale snapshot / post-threshold stalled 三種治理狀態變成單一 machine-read contract。
  - `scripts/hb_parallel_runner.py`：heartbeat summary 會同步持久化 `leaderboard_candidate_diagnostics.governance_contract`。
  - `tests/test_hb_leaderboard_candidate_probe.py`、`tests/test_hb_parallel_runner.py`：新增 regression tests 鎖住治理 contract。
- **Tests（已通過）**
  - `python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **40 passed**
- **Runtime verify（已通過）**
  - `python scripts/hb_parallel_runner.py --fast` → **通過**
  - q35 current live path 與 q35 audit / probe / drilldown 仍同輪對齊，且 governance contract 已寫進 summary。

### 資料 / 新鮮度 / canonical target
- Heartbeat #fast：
  - Raw / Features / Labels：**21784 / 13213 / 43574**
  - canonical target `simulated_pyramid_win`：**0.5805**
  - 240m labels：**21931 rows / target_rows 13009 / freshness=expected_horizon_lag**
  - 1440m labels：**12558 rows / target_rows 12558 / freshness=expected_horizon_lag**
  - recent raw age：**約 0.5 分鐘**
  - continuity repair：**4h=0 / 1h=0 / bridge=0**

### IC / drift
- Global IC：**18/30 pass**
- TW-IC：**26/30 pass**
- drift primary window：**250**
  - alerts：`label_imbalance`, `regime_concentration`, `regime_shift`
  - interpretation：**distribution_pathology**
  - dominant_regime：**bull 100.0%**
  - win_rate：**0.8920**

### Live contract / q35 / q15 / governance
- **q35 current-live path（健康）**
  - structure bucket：**`CAUTION|structure_quality_caution|q35`**
  - `q35_scaling_audit.deployment_grade_component_experiment.verdict = runtime_patch_crosses_trade_floor`
  - `entry_quality=0.5675` / `allowed_layers=1` / `q35_discriminative_redesign_applied=true`
  - `live_predict_probe.allowed_layers=1`
- **profile governance（已 machine-read 收斂，但未完全結案）**
  - leaderboard：`core_plus_4h`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `governance_contract.verdict = dual_role_governance_active`
  - `governance_contract.treat_as_parity_blocker = false`
  - `support_governance_route = exact_live_bucket_present_but_below_minimum`
  - current q35 exact live bucket rows：**15 / 50**
- **q15 support（仍為 standby）**
  - `q15_support_audit.scope_applicability.status = current_live_not_q15_lane`
  - `support_governance_route = exact_bucket_present_but_below_minimum`
  - q15 exact bucket rows gap：**35**（以 current-live q35 bucket 計）

### Source blockers
- `fin_netflow`：**auth_missing / coverage 0.0% / archive_window_coverage 0.0%**
- 其他 blocked sparse features 仍以 `archive_required / snapshot_only` 為主

---

## 目前有效問題

### P1. current live bull q35 exact support 仍不足，production profile 只能維持 dual-role governance
**現象**
- `leaderboard_feature_profile_probe.alignment.governance_contract.verdict = dual_role_governance_active`
- `support_governance_route = exact_live_bucket_present_but_below_minimum`
- current live q35 exact bucket rows：**15 / 50**

**判讀**
- 這已**不是 parity drift**；本輪 patch 已把語義明確化。
- 真正未解的是：current live exact support 未達 minimum，production profile 仍需保留 support-aware / exact-supported 治理角色，不能直接把 leaderboard global winner 視為 production closure。

---

### P1. q15 exact support 仍不足，只能維持 standby route
**現象**
- `q15_support_audit.scope_applicability.status = current_live_not_q15_lane`
- q15 仍非 current-live 主 closure
- q15 support route：`exact_bucket_present_but_below_minimum`

**判讀**
- q15 目前只能維持 standby governance。
- 在 current live row 不回到 q15 lane 且 exact support 未達標前，不得把 q15 component experiment 寫成 deployment closure。

---

### P1. sparse-source blocker 仍存在，`fin_netflow` 仍是 auth blocker
**現象**
- `fin_netflow`: `auth_missing`, `coverage=0.0%`, `archive_window_coverage_pct=0.0%`

**判讀**
- 仍是 source blocker。
- 但優先級低於 current-live support governance 與 q15 standby truthfulness。

---

## 本輪已清掉的問題

### RESOLVED. `leaderboard_global_winner_vs_train_support_fallback` 缺少單一 machine-read 解釋，容易被誤讀成 parity drift
**修前**
- probe / heartbeat summary 雖有 `dual_profile_state` 與 `profile_split`，但沒有單一治理 verdict；
- 文件很難直接 machine-read「這是雙角色治理」還是「這是未解 blocker」。

**本輪 patch + 證據**
- `scripts/hb_leaderboard_candidate_probe.py`
  - 新增 `_build_governance_contract()`
  - 輸出 `governance_contract.verdict/current_closure/treat_as_parity_blocker/recommended_action`
- `scripts/hb_parallel_runner.py`
  - 把 `governance_contract` 同步寫進 `heartbeat_fast_summary.json`
- `tests/test_hb_leaderboard_candidate_probe.py` + `tests/test_hb_parallel_runner.py`
  - regression tests 通過
- `python -m pytest ...` → **40 passed**
- `python scripts/hb_parallel_runner.py --fast` → **通過**，且 summary 已持久化 `governance_contract`

**狀態**
- **已修復**：雙角色治理的語義已 machine-read 化
- **後續不再把這件事本身當 parity drift blocker**；下一輪應直接處理 support readiness / leaderboard 是否需要 post-threshold sync

---

## 本輪決策（收斂版）

### 策略後果表
| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 只在文件手寫說明 dual-profile | 改動小 | heartbeat JSON / summary 仍無法 machine-read，下一輪仍會反覆誤判 | 治標 | 只需人工閱讀 | ❌ 不建議 |
| 在 probe + heartbeat summary 落地單一 `governance_contract` | probe / summary / docs 可共用同一治理語義 | 需要補 regression test | 治本 | 當前主問題是 profile governance 解釋不一致 | ✅ 推薦 |
| 直接把 leaderboard 改成 production profile | 可能快速消除 split | exact support 尚未達 minimum，容易把 current-live support blocker 蓋掉 | 治標 | exact bucket 已充分支持且確認應升級 ranking | ❌ 本輪不建議 |

### 效益前提驗證
| 情境 | 效益 |
|---|---|
| `governance_contract` 能在 probe / summary 同步輸出 | ✅ 前提成立，本輪已實現 |
| exact support 尚未達標，但能先把 split 定義成雙角色治理 | ✅ 前提成立，可先關掉語義歧義 |
| 直接切 leaderboard=production 而不看 support readiness | ❌ 前提不成立，會把 support blocker 包裝成已解 |

### 本輪要推進的 3 件事
1. 把 profile governance 收斂成單一 machine-read contract。 ✅
2. 用 pytest + fast heartbeat 驗證 contract 進 probe / summary。 ✅
3. 把主 blocker 重新定位為 support readiness，而不是 parity drift。 ✅

### 本輪不做
- 不直接切 leaderboard 排名到 production profile；
- 不把 q15 standby route 拉回主 closure；
- 不先做 sparse-source auth 修復。

---

## Next gate

- **Next focus:**
  1. 釐清 `dual_role_governance_active` 是否仍應維持，或已進入需要 `post_threshold_governance_contract_needs_leaderboard_sync` 的條件；
  2. 繼續追 current live q35 exact support（15/50 → 50/50）；
  3. 維持 q15 standby route truthfulness，不得把 inactive q15 lane 寫成 current-live closure。

- **Success gate:**
  1. 下一輪至少留下 1 個與 **q35 exact support readiness** 或 **post-threshold leaderboard sync** 直接相關的 patch / artifact / verify；
  2. `leaderboard_feature_profile_probe.alignment.governance_contract` 必須持續存在，且 `treat_as_parity_blocker=false` 直到 exact support 條件真的翻轉；
  3. `live_predict_probe` 仍維持 `entry_quality>=0.55`、`allowed_layers=1`、`q35_discriminative_redesign_applied=true`。

- **Fallback if fail:**
  - 若 `governance_contract` 消失或又被 summary 漏掉，直接回查 `hb_leaderboard_candidate_probe.py` / `hb_parallel_runner.py` 的 contract 持久化；
  - 若 current live q35 exact support 仍卡在 <50 且無新增治理 patch，下一輪升級為 `#PROFILE_GOVERNANCE_STALLED` blocker；
  - 若 live row 離開 q35，依 `scope_applicability` 改追 active lane，不得硬守 q35。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 governance contract 再新增 machine-read 欄位）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_fast_summary.json` 的 `leaderboard_candidate_diagnostics.governance_contract`；
  2. 再讀：
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
  3. 若 `governance_contract.verdict = dual_role_governance_active` 且 `support_governance_route = exact_live_bucket_present_but_below_minimum`，下一輪**不得再把 profile split 說成 parity drift**；必須直接處理 **q35 exact support readiness** 或 **post-threshold leaderboard sync 條件**。
