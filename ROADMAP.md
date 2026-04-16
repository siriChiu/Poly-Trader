# ROADMAP.md — Current Plan Only

_最後更新：2026-04-16 00:47 UTC_

只保留目前計畫，不保留歷史 roadmap。

---

## 已完成
- fast heartbeat 已刷新 core artifacts：collect / full IC / regime IC / drift / live probe / q35-q15 audits / candidate probe
- 本輪 collect 實際推進：**Raw +1 / Features +1 / Labels +3**
- current live bucket 已從上一輪 q15 轉成：`bull / CAUTION / q35`
- q35 discriminative redesign 已在 live runtime 對齊 current row：
  - `entry_quality = 0.5544`
  - `allowed_layers = 1`
  - `q35_discriminative_redesign_applied = true`
- q15 audit 已被降級成 standby route readiness，避免再污染 current-live 判斷
- governance 結論維持：`dual_role_governance_active`
  - leaderboard：`core_plus_4h`
  - production/runtime：`core_plus_macro`

---

## 主目標

### 目標 A：讓 current live q35 exact support 往 deployment-ready 前進
重點：
- 持續追 `current_live_structure_bucket_rows`
- 明確區分「q35 runtime 已改善」與「q35 support 已達 deployment-grade」
- 不讓舊 q15 blocker 或舊 bucket 敘事再污染下一輪決策

### 目標 B：把 q35 runtime patch 和 deployment verify 分開治理
重點：
- runtime patch 已證明 current row 可跨過 trade floor
- 但 support 未達標前，不把 q35 redesign 誤寫成 deploy closure
- 只有 support 與 runtime 同時成立，才往 deployment readiness 推進

### 目標 C：提升模型穩定度
重點：
- 壓低 `cv_std`
- 拉高 `cv_worst`
- 比較 support-aware profile 與 global shrinkage winner 在 current q35 bucket 的 robustness

---

## 下一步
1. 下一輪先確認 current live bucket 是否仍是 `CAUTION|structure_quality_caution|q35`
2. 追 `current_live_structure_bucket_rows` 是否從 **7 / 50** 往上累積
3. 若 q35 仍是 current bucket，驗證 live probe 是否仍維持 `entry_quality >= 0.55` 且 `allowed_layers > 0`
4. 若 support 長期停滯，升級成明確 governance blocker
5. sparse-source auth/archive 暫列後段

---

## 成功標準
- current live q35 exact support 不再停在 **7 / 50**
- q35 current-live lane 仍可維持 `entry_quality >= 0.55`、`allowed_layers > 0`
- `issues.json` / ISSUES.md / ROADMAP.md 對 current bucket、support route、governance contract 保持一致
- `cv_std` 下降
- `cv_worst` 高於目前 **0.5445**

---

## Fallback if fail
- 若 current q35 support 無法累積：升級為 governance blocker，而不是繼續把 runtime patch 當 closure
- 若 live bucket 再切換：立即重寫 current blocker 與 carry-forward input，避免 stale q35 anchor
- 若 runtime 再跌回 `entry_quality < 0.55`：回頭審核 q35 redesign 是否只對窄 pocket 有效
- 若 stability 無改善：改做 current-bucket robustness / shrinkage 對比，不再只看整體 CV 均值

---

## Documents to update next round
- `ISSUES.md`
- `ROADMAP.md`
- `issues.json`
- 如 governance contract 或 runtime contract 再變化，更新 `ARCHITECTURE.md`

---

## Carry-forward input for next heartbeat
1. 先執行 Step 0.5：從 `ISSUES.md`、`ROADMAP.md`、`issues.json` 抽出 current q35 bucket / support gate / success gate。
2. 先檢查 `data/live_predict_probe.json`、`data/q35_scaling_audit.json`、`data/leaderboard_feature_profile_probe.json`：
   - current live bucket 是不是還是 `CAUTION|structure_quality_caution|q35`
   - q35 redesign 是否仍套用在 current row
   - support rows 是否仍低於 `50`
   - governance 是否仍是 `dual_role_governance_active`
3. 若 bucket 已切換，先改 issue 與 roadmap，再做任何 closure 判斷。
4. 只有在 current q35 support 或 model stability 有實質前進時，才把 runtime readiness 往前推；否則升級 blocker，不可只報告數字。
