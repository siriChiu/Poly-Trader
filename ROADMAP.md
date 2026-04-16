# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 03:24 UTC_

只保留目前計畫，不保留歷史 roadmap。

---

## 已完成
- 已執行本輪 collect / feature / label 前進：**Raw +1 / Features +1 / Labels +24**
- 已重跑 canonical diagnostics：
  - Global IC = **17 / 30**
  - TW-IC = **28 / 30**
  - regime-aware IC = **Bear 5/8 / Bull 6/8 / Chop 4/8**
  - recent drift primary window = **100**，interpretation = `distribution_pathology`
- 已重跑 current live probe，確認 current bucket 仍是 **q35**：
  - `bull / CAUTION / q35`
  - `entry_quality = 0.5956`
  - `allowed_layers_raw = 1`
  - `allowed_layers = 0`
  - `deployment_blocker = under_minimum_exact_live_structure_bucket`
- 已重跑 q35 scaling audit，確認：
  - `q35_discriminative_redesign_applied = true`
  - runtime redesign **已跨 trade floor**
  - 但 exact support 仍只有 **4 / 50**，仍不可 deploy
- 已重跑 leaderboard candidate probe，確認：
  - leaderboard global winner = `core_only`
  - production/runtime profile = `core_plus_macro`
  - governance = `dual_role_governance_active`
  - q35 support progress = `stalled_under_minimum`
- 已完成 governance patch：
  - `scripts/issues.py` 現在會把 `next_actions` / summary fallback 正規化成 machine-readable `action`
  - `scripts/auto_propose_fixes.py` 現在會正確顯示 current-state issues 的治理 action，不再出現空白箭頭
- 已完成驗證：
  - `python -m pytest tests/test_issues_tracker.py tests/test_auto_propose_fixes.py tests/test_hb_leaderboard_candidate_probe.py tests/test_hb_parallel_runner.py -q` → **62 passed**
- 已刷新 current-state artifacts：
  - `data/heartbeat_fast_summary.json`
  - `data/live_predict_probe.json`
  - `data/q35_scaling_audit.json`
  - `data/leaderboard_feature_profile_probe.json`
  - `data/recent_drift_report.json`
  - `issues.json`

---

## 主目標

### 目標 A：讓 current live q35 exact support 脫離停滯
重點：
- 持續追 `current_live_structure_bucket_rows`
- 明確區分「q35 lane active」與「q35 lane deployable」
- support 未增加前，不把 q35 redesign 誤寫成部署進度

### 目標 B：維持 q35 redesign runtime patch 與 deployment legality 分開治理
重點：
- runtime redesign 已證明可把 q35 lane 推過 floor
- 但 final execution 仍被 support gate 壓到 `allowed_layers = 0`
- 只有 support 與 runtime legality 同時成立，才往 deployment readiness 推進

### 目標 C：把 drift pathology 從觀察升級成 root-cause patch
重點：
- 100-row recent bull pocket 仍是 `distribution_pathology`
- 下一輪必須直接追 frozen / compressed features 與 target-path drill-down
- 沒有 root-cause patch，不算進度

---

## 下一步
1. 下一輪先確認 current live bucket 是否仍是 `CAUTION|structure_quality_caution|q35`
2. 追 `current_live_structure_bucket_rows` 是否從 **4 / 50** 往上累積
3. 若 q35 仍是 current bucket，驗證 live probe 是否仍維持 `entry_quality >= 0.55`、`allowed_layers_raw > 0`，且 blocker 語義仍正確
4. 直接對 recent pathology 做 drill-down：優先檢查 `feat_vix`, `feat_body`, `feat_ear`, `feat_tongue`, `feat_atr_pct`
5. 若 support 未動或回落，明確升級為 governance blocker；若 drift 仍無 patch，升級為 heartbeat 空轉治理問題

---

## 成功標準
- current live q35 exact support **高於本輪 4 / 50**
- q35 current-live lane 維持 `entry_quality >= 0.55`、`allowed_layers_raw > 0`
- `ISSUES.md` / `ROADMAP.md` / `issues.json` / heartbeat summary 對 current bucket、support gate、governance contract、blocker 語義保持一致
- 找到並修掉至少 1 個 recent pathology root cause，且留下 verify 證據
- `cv_std` 下降或 `cv_worst` 高於 **0.5445**

---

## Fallback if fail
- 若 q35 support 無法累積或持續停在 4：升級為 governance blocker，而不是繼續把 floor-cross runtime patch 當 closure
- 若 live bucket 再切換：立即重寫 current blocker 與 carry-forward input，避免 stale q35 anchor
- 若 blocker 語義再次回退：優先修診斷 surface，避免 heartbeat 再做假結論
- 若 drift 仍無 root-cause patch：下一輪強制以 pathology 修復為唯一 top fix，禁止只更新數字

---

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `issues.json`
- 如 governance contract 或 current-live decision contract 再變化，更新 `ARCHITECTURE.md`

---

## Carry-forward input for next heartbeat
1. 先執行 Step 0.5：從 `ISSUES.md`、`ROADMAP.md`、`issues.json` 抽出 current q35 bucket / support gate / pathology gate。
2. 先檢查 `data/live_predict_probe.json`、`data/q35_scaling_audit.json`、`data/leaderboard_feature_profile_probe.json`、`data/recent_drift_report.json`：
   - current live bucket 是不是還是 `CAUTION|structure_quality_caution|q35`
   - q35 redesign 是否仍維持 `entry_quality >= 0.55`、`allowed_layers_raw > 0`
   - support rows 是否仍低於 `50`
   - drift 是否仍是 `100-row bull distribution_pathology`
3. 若 bucket 已切換，先改 issue 與 roadmap，再做任何 closure 判斷。
4. 若 live blocker 不再是 `under_minimum_exact_live_structure_bucket`，先檢查 predictor / probe / candidate diagnostics 是否失真。
5. 只有在 q35 support 或 pathology root-cause patch 有實質前進時，才把 q35 runtime readiness 往前推；否則明確維持 blocker，不可只報告數字。