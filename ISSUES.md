# ISSUES.md — Current State Only

_最後更新：2026-04-15 21:16 UTC — Heartbeat #fast（本輪把 **q35 exact support readiness** 從單點 row-count 升級成 machine-read `support_progress` contract，讓 probe / heartbeat summary 可以直接分辨「仍在累積 / 缺少可比歷史 / stalled 候選 blocker」。）_

本文件只保留**目前仍有效的問題、證據、下一步與 carry-forward 指令**，不保留歷史流水帳。

---

## Step 0.5 承接上輪輸入

### 文件中的上輪要求本輪處理
- **Next focus**
  1. 追 q35 exact support readiness；
  2. 判斷 dual-role 是否需要升級成 post-threshold leaderboard sync；
  3. 維持 q15 standby route truthfulness。
- **Success gate**
  1. next run 必須留下至少一個與 **q35 exact support** 或 **leaderboard sync** 直接相關的 patch / artifact / verify；
  2. `governance_contract` 必須仍存在且語義正確；
  3. q35 current live path 必須維持 `entry_quality>=0.55`、`allowed_layers>0`、`live_predict_probe.allowed_layers=1`。
- **Fallback if fail**
  - 若 governance contract 又被誤解為 parity blocker，回查 probe / summary contract persistence；
  - 若 q35 exact support 長期停在 `<50`，升級成專門的 support-accumulation blocker；
  - 若 current live row 離開 q35，改追 active lane。

### 本輪承接結果
- **已處理**
  - `scripts/hb_leaderboard_candidate_probe.py`
    - 新增 `support_progress={status,reason,current_rows,previous_rows,delta_vs_previous,stagnant_run_count,stalled_support_accumulation,escalate_to_blocker,history}`；
    - `governance_contract` 會同步帶出 `support_progress`，未來可直接 machine-read `#PROFILE_GOVERNANCE_STALLED` 候選 blocker。
  - `scripts/hb_parallel_runner.py`
    - `run_leaderboard_candidate_probe()` 現在會傳入 `HB_RUN_LABEL`；
    - heartbeat summary 新增 `leaderboard_candidate_diagnostics.support_progress / minimum_support_rows / live_current_structure_bucket_gap_to_minimum`。
  - `tests/test_hb_leaderboard_candidate_probe.py`
    - 新增 stalled exact-support regression test。
  - `tests/test_hb_parallel_runner.py`
    - 新增 heartbeat summary persistence regression（support_progress / gap / minimum rows）。
- **驗證已完成**
  - `source venv/bin/activate && python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **41 passed**
  - `/home/kazuha/Poly-Trader/venv/bin/python scripts/hb_parallel_runner.py --fast` → **通過**
- **本輪 machine-read 結論**
  - `leaderboard_feature_profile_probe.alignment.governance_contract.verdict = dual_role_governance_active`
  - `support_governance_route = exact_live_bucket_present_but_below_minimum`
  - `support_progress.status = no_recent_comparable_history`
  - `support_progress.current_rows = 13 / minimum_support_rows = 50 / gap = 37`
- **本輪明確不做**
  - 不把 leaderboard ranking 直接切到 production profile；exact support 尚未達標。
  - 不把 q15 standby route 寫成 current-live closure；current row 仍是 q35。
  - 不先處理 sparse-source auth；`fin_netflow` 仍是 source blocker，但不是本輪主 closure。

---

## 目前系統狀態

### 本輪 patch / 驗證
- **Patch（已落地）**
  - `scripts/hb_leaderboard_candidate_probe.py`：新增 `support_progress` machine-read contract，讓 q35 exact support readiness 不再只剩單點 row-count。
  - `scripts/hb_parallel_runner.py`：heartbeat summary 會同步持久化 `support_progress / minimum_support_rows / live_current_structure_bucket_gap_to_minimum`，且 probe 會接收 `HB_RUN_LABEL`。
  - `tests/test_hb_leaderboard_candidate_probe.py`、`tests/test_hb_parallel_runner.py`：新增 regression tests 鎖住 stalled-support contract。
- **Tests（已通過）**
  - `python -m pytest tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **41 passed**
- **Runtime verify（已通過）**
  - `venv/bin/python scripts/hb_parallel_runner.py --fast` → **通過**
  - `leaderboard_feature_profile_probe.json` 與 `heartbeat_fast_summary.json` 已同步帶出 `support_progress`。

### 資料 / 新鮮度 / canonical target
- Heartbeat #fast：
  - Raw / Features / Labels：**21786 / 13215 / 43578**
  - canonical target `simulated_pyramid_win`：**0.5806**
  - 240m labels：**21933 rows / target_rows 13011 / freshness=expected_horizon_lag**
  - 1440m labels：**12560 rows / target_rows 12560 / freshness=expected_horizon_lag**
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
- **q35 current-live path（健康但 exact support 不足）**
  - structure bucket：**`CAUTION|structure_quality_caution|q35`**
  - `q35_scaling_audit.overall_verdict = bias50_formula_may_be_too_harsh`
  - `deployment_grade_component_experiment.verdict = runtime_patch_crosses_trade_floor`
  - `entry_quality=0.5507` / `allowed_layers=1` / `q35_discriminative_redesign_applied=true`
  - `live_predict_probe.allowed_layers = 1`
- **profile governance（語義正確，但 current-live exact support 仍不足）**
  - leaderboard：`core_plus_4h`
  - train：`core_plus_macro_plus_4h_structure_shift`
  - `dual_profile_state = leaderboard_global_winner_vs_train_support_fallback`
  - `governance_contract.verdict = dual_role_governance_active`
  - `governance_contract.treat_as_parity_blocker = false`
  - `support_governance_route = exact_live_bucket_present_but_below_minimum`
  - current live q35 exact bucket：**13 / 50**（較上輪 15/50 再退 2）
  - `support_progress.status = no_recent_comparable_history`（本輪開始才有 machine-read contract；後續 heartbeat 可直接判斷是否 stalled）
- **q15 support（仍為 standby）**
  - `q15_support_audit.scope_applicability.status = current_live_not_q15_lane`
  - `support_route.verdict = exact_bucket_present_but_below_minimum`
  - `floor_cross_legality.verdict = floor_crossed_but_support_not_ready`
  - q15 只能維持 governance reference / standby route，不能寫成 current-live closure。

### Source blockers
- `fin_netflow`：**auth_missing / coverage 0.0% / archive_window_coverage 0.0%**
- 其他 blocked sparse features 仍以 `archive_required / snapshot_only` 為主

---

## 目前有效問題

### P1. current live bull q35 exact support 退到 13/50，dual-role governance 仍不能關閉
**現象**
- `support_governance_route = exact_live_bucket_present_but_below_minimum`
- `live_current_structure_bucket_rows = 13 / minimum_support_rows = 50`
- `live_current_structure_bucket_gap_to_minimum = 37`
- 上輪文件記錄為 **15/50**，本輪退到 **13/50**

**判讀**
- dual-role governance 仍是正確語義，**但真正未解 blocker 是 q35 exact support 不足**。
- 本輪已把 support progression machine-read 化；後續 heartbeat 可以直接判斷是否進入 stalled blocker，而不用人工比對多輪 summary。

---

### P1. q15 route 仍是 standby governance，不可誤寫成 current-live closure
**現象**
- `q15_support_audit.scope_applicability.status = current_live_not_q15_lane`
- `support_route.verdict = exact_bucket_present_but_below_minimum`
- `floor_cross_legality.legal_to_relax_runtime_gate = false`

**判讀**
- q15 仍不是 active lane。
- 即使 floor 已跨過，也不能用 proxy / standby route 解除 current-live blocker。

---

### P1. sparse-source blocker 仍存在，`fin_netflow` 仍是 auth blocker
**現象**
- `fin_netflow`: `auth_missing`, `coverage=0.0%`, `archive_window_coverage_pct=0.0%`

**判讀**
- 仍是 source blocker。
- 但優先級低於 current-live q35 exact support readiness 與 q15 truthful governance。

---

## 本輪已清掉的問題

### RESOLVED. q35 exact support readiness 只有單點 row-count，無法 machine-read 判斷是否 stalled
**修前**
- probe / summary 只有 `live_current_structure_bucket_rows` 與 gap；
- heartbeat 需要人工翻多輪 summary 才能判斷 support 是在增加、停滯還是退化。

**本輪 patch + 證據**
- `scripts/hb_leaderboard_candidate_probe.py`
  - 新增 `support_progress` contract
  - `governance_contract` 同步帶出 `support_progress`
- `scripts/hb_parallel_runner.py`
  - summary 持久化 `support_progress`
  - probe 傳入 `HB_RUN_LABEL`
- `tests/test_hb_leaderboard_candidate_probe.py` + `tests/test_hb_parallel_runner.py`
  - regression tests 通過
- `python -m pytest ...` → **41 passed**
- `python scripts/hb_parallel_runner.py --fast` → **通過**

**狀態**
- **已修復**：support accumulation 現在已有 machine-read contract
- **尚未關閉的 blocker**：current q35 exact support 仍只有 **13/50**，只是現在終於能在後續 heartbeat 直接 machine-read 判讀它是否 stalled

---

## 本輪決策（收斂版）

### 策略後果表
| 策略 | 好處 | 風險／代價 | 治標/治本 | 適用條件 | 建議 |
|---|---|---|---|---|---|
| 只在文件手寫「q35 support 仍不足」 | 改動小 | 下輪仍需人工翻多輪 summary，無法 machine-read stalled | 治標 | 只做人工閱讀 | ❌ 不建議 |
| 在 probe + heartbeat summary 落地 `support_progress` | 直接 machine-read q35 support 是累積、缺歷史、或 stalled 候選 blocker | 需要補 regression tests | 治本 | 主 blocker已從語義收斂轉成 support readiness | ✅ 推薦 |
| 直接把 leaderboard 切到 production profile | 可能快速消除 split | exact support 還沒達標，會把未解 blocker 誤包裝成 closure | 治標 | exact bucket 已充分支持且確定要同步 ranking | ❌ 本輪不建議 |

### 效益前提驗證
| 情境 | 效益 |
|---|---|
| probe / summary 能同步輸出 `support_progress` | ✅ 前提成立，本輪已落地 |
| current live q35 exact support 尚未達標，但先 machine-read 化 progression | ✅ 前提成立，可先消除人工比對成本 |
| exact support 未達標就直接切 leaderboard=production | ❌ 前提不成立，會把 blocker 假裝成已解 |

### 本輪要推進的 3 件事
1. 把 q35 exact support readiness 升級成 machine-read `support_progress` contract。 ✅
2. 用 pytest + fast heartbeat 驗證 contract 進 probe / summary。 ✅
3. 保持 q35 runtime path 健康，同時重新聚焦在 exact support gap，而不是 profile 語義。 ✅

### 本輪不做
- 不把 leaderboard ranking 直接切到 production profile；
- 不把 q15 standby route 拉回主 closure；
- 不先做 sparse-source auth 修復。

---

## Next gate

- **Next focus:**
  1. 追 q35 current-live exact support（13/50 → 50/50）；
  2. 觀察 `support_progress` 是否從 `no_recent_comparable_history` 轉成 `accumulating` 或 `stalled_under_minimum`；
  3. 維持 q15 standby route truthfulness，不得把 inactive q15 lane 寫成 current-live closure。

- **Success gate:**
  1. 下一輪至少留下 1 個與 **q35 exact support readiness** 或 **support_progress blocker governance** 直接相關的 patch / artifact / verify；
  2. `leaderboard_feature_profile_probe.alignment.governance_contract` 必須持續存在，且在 support 未翻轉前維持 `treat_as_parity_blocker=false`；
  3. `support_progress` 必須持續被 probe / summary 持久化，且能 machine-read current rows / gap / status；
  4. `live_predict_probe` 仍維持 `entry_quality>=0.55`、`allowed_layers=1`、`q35_discriminative_redesign_applied=true`。

- **Fallback if fail:**
  - 若 `support_progress` 消失或 summary 漏掉，直接回查 `hb_leaderboard_candidate_probe.py` / `hb_parallel_runner.py` 的 contract persistence；
  - 若 q35 exact support 在後續可比 heartbeat 仍停在 `<50` 且 `support_progress.stalled_under_minimum=true`，下一輪升級為 `#PROFILE_GOVERNANCE_STALLED` blocker；
  - 若 current live row 離開 q35，依 `scope_applicability` 改追 active lane，不得硬守 q35。

- **Documents to update next round:**
  - `ISSUES.md`
  - `ROADMAP.md`
  - `ARCHITECTURE.md`（若 `support_progress` contract 再擴充欄位）

- **Carry-forward input for next heartbeat:**
  1. 先讀 `data/heartbeat_fast_summary.json` 的 `leaderboard_candidate_diagnostics.governance_contract` 與 `leaderboard_candidate_diagnostics.support_progress`；
  2. 再讀：
     - `data/leaderboard_feature_profile_probe.json`
     - `data/live_predict_probe.json`
     - `data/q35_scaling_audit.json`
     - `data/q15_support_audit.json`
  3. 若 `support_governance_route = exact_live_bucket_present_but_below_minimum`，先看 `support_progress.status`：
     - `accumulating` → 繼續追 exact support readiness；
     - `stalled_under_minimum` → 升級 `#PROFILE_GOVERNANCE_STALLED` 評估；
     - `no_recent_comparable_history` → 至少再留一輪 machine-read history，不得回頭把 profile split 說成 parity drift。
