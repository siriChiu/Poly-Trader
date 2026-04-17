# ROADMAP.md — Current Plan Only

_最後更新：2026-04-17 11:43 UTC_

只保留目前計畫；每輪 heartbeat 必須覆蓋更新，不保留舊 roadmap 歷史。

---

## 已完成
- **q15 root-cause blocker truth 對齊**
  - `scripts/hb_q15_bucket_root_cause.py` 已在 `CIRCUIT_BREAKER` 活躍時回報 `runtime_blocker_preempts_bucket_root_cause`
  - 不再把被 breaker 預先擋下的 live path 誤寫成 `missing_structure_quality` / `live_row_projection`
  - regression test 已補上：`python -m pytest tests/test_q15_bucket_root_cause.py -q` → **4 passed**
- **Fast heartbeat evidence refresh**
  - `Raw=30609 / Features=22027 / Labels=61781`
  - canonical runtime：`Global IC 14/30`、`TW-IC 28/30`、`CIRCUIT_BREAKER`、recent 50=`8/50`

---

## 主目標

### 目標 A：維持 breaker-first canonical runtime truth
重點：
- `circuit_breaker_active` 仍是真正 deployment blocker
- q15 / q35 / profile governance 只能當背景治理，不可覆蓋 live blocker
- heartbeat 必須直接回答距 release 還差多少勝

成功標準：
- recent 50 win rate 回到 `>= 30%`
- recent 50 至少達 `15/50`
- probe / drilldown / status / q15 root-cause 全部維持同一 breaker-first truth

### 目標 B：把 fast governance de-timeout 推進到「真 cache hit」
重點：
- 不是再增加 timeout fallback，而是讓重型 lane 真正 reuse fresh artifact
- summary 必須清楚區分 `cached / fresh recompute / timeout fallback`

成功標準：
- 下一輪 fast run 至少一條重型 governance lane 顯示 `cached=True`
- operator 能直接分辨哪條 lane 是 fresh、哪條只是 fallback

### 目標 C：把 recent canonical distribution pathology 收斂成 machine-readable 根因
重點：
- current primary pathology 仍是 `window=500` bull concentration
- 必須把高 win rate 與 deployment readiness 分離
- 直接追 target-path / feature variance / distinct-count 根因

成功標準：
- recent pathology 不再只是 `distribution_pathology` 黑盒標籤
- heartbeat / probe / docs 對同一 root cause 給出一致結論
- 不再長期只靠 guardrail 掩蓋 unexplained pocket

### 目標 D：把 Binance execution lane 推進到真實 venue-backed closure
重點：
- 不再只停在 product surface 完整
- 補 partial-fill / cancel / restart-replay 真實 artifact 鏈
- 維持低頻高信念原則，不用降 gate 換假進展

成功標準：
- Binance lane 進入 `venue_backed_path_ready`
- `/api/status`、Dashboard、Strategy Lab 對同一 lane 顯示同一 execution truth
- provenance 不再停在 dry-run / internal-only

---

## 下一步
1. **Tail root cause**：直接拆 canonical recent 50/500 的 target path，回答為何仍停在 `8/50`
2. **Fast cache hit**：先做一條重型治理 lane 的 semantic freshness reuse，拿到真實 `cached=True`
3. **Venue-backed artifacts**：補 Binance partial-fill / cancel / restart-replay 的真實 artifact 鏈

---

## 成功標準
- breaker-first runtime truth 在所有主要 surface 保持一致
- fast heartbeat 具備 **cron-safe + machine-readable + actual cache-hit evidence**
- recent canonical pathology 被縮小或明確解釋，不再只是 blocker 黑盒
- execution lane 具備 **真實 venue-backed artifact**，而不只是產品外觀完整
