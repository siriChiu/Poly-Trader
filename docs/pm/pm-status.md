# PM Status — Poly-Trader Current Delivery State Only

_最後更新：2026-05-18 03:09:47 CST_

> Current-state PM interpretation. Do not append hourly history here; update only when PM classification, blocker interpretation, customer-usable lane, engineering ask, or next gate changes.

---

## 1. PM decision

**State：`YELLOW_shadow_or_paper_usable`**

PM 判定：PM 必須站在**客戶成功**一側，主動幫客戶把 Poly-Trader 變成現在可理解、可操作、可驗證的產品。工程端「不能放行 risk-on live buy/add」目前有 artifact 支撐，但這只能阻止真實買入/加倉，不能成為讓客戶繼續等待的理由。當前正確 PM 解法不是繼續說等，也不是降低交易安全 gate，而是把產品交付切成：

1. **現在可用**：Dashboard / Strategy Lab / Execution Console 的診斷、研究、paper/shadow、dry-run readiness。
2. **現在不可用**：真實買入 / 加倉 / 啟用自動送單。
3. **下一小時推進**：要求 engineering heartbeat 交付一個安全可用 lane、可驗證 release evidence、或 customer-facing UX/copy；不得只回報等待。
4. **framework-capture 檢查**：若 Poly-Trader 自訂 skills、文件或 harness 規則讓 agent 只會重複 fail-closed 敘事，PM 必須標記 `ORANGE_framework_capture_risk` 並要求簡化/修補框架，而不是被框架限制。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `2026-05-17T18:11:54.202806Z`.
- `signal=HOLD` / `should_trade=false`.
- `deployment_blocker=under_minimum_exact_live_structure_bucket`.
- `current_live_structure_bucket=CAUTION|structure_quality_caution|q15`.
- `current_live_structure_bucket_rows=3` / `minimum_support_rows=50` / `gap=47`.
- `allowed_layers_raw=1` but `allowed_layers=0` because `allowed_layers_reason=under_minimum_exact_live_structure_bucket`.

**PM verdict：接受「live buy/add 現在不能放行」；不接受把這句話延伸成「產品不能被使用」。**

### Research-to-delivery candidates

- `data/high_conviction_topk_oos_matrix.json` shows high-conviction OOS candidates exist, but live support overlay keeps them runtime-blocked.
- Support context: `support_route_verdict=exact_bucket_present_but_below_minimum`, `current_live_structure_bucket_rows=3/50`, `support_rows_needed=47`.
- Current acceptable use: research comparison, nearest-deployable explanation, and paper/shadow observation.

**PM verdict：可展示「接近部署候選」與「為何還不能部署」，但不可標成 live deployable。**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `2026-05-17T18:12:03.686659Z`.
- `runtime_ready=false` / `runtime_ready_count=0`.
- OKX: public metadata OK, credentials not configured, order ack/fill lifecycle missing.
- Binance: unsupported/disabled metadata contract failed, runtime proof missing.

**PM verdict：可以推 venue dry-run / readiness checklist；不可宣稱 live venue ready。**

### Recent market/model risk

- `data/recent_drift_report.json` generated at `2026-05-17T18:11:51.508175+00:00`.
- Latest 100 rows: `win_rate=17.0%`, dominant regime `bear=87.0%`, `avg_simulated_quality=-0.1521`, `avg_simulated_pnl=-0.0083`.

**PM verdict：近期品質惡化支持 fail-closed；更需要清楚的 customer-facing safe lane。**

---

## 3. Customer expectation vs PM answer

### Customer expectation

客戶想「現在就能用產品」，而不是看工程心跳每小時都說等。

### PM answer

可以立刻使用的產品價值應被明確交付：

1. **Strategy Lab**：用 high-conviction Top-K / leaderboard 看候選策略、OOS ROI、drawdown、profit factor、runtime-blocked 原因。
2. **Dashboard**：看 current-live blocker、4H context、decision quality、feature continuity / source blockers。
3. **Execution Console**：只做 paper/shadow、dry-run readiness、風險降低 / 診斷，不做真實買入 / 加倉。
4. **Venue readiness**：OKX/Binance proof checklist 告訴客戶還差 credential、order ack、fill lifecycle 哪一段。
5. **Canary rehearsal**：先做 canary gap checklist；等 support rows、venue proof、runtime gates 通過再談極小額 live canary。

---

## 4. Framework-capture guard

客戶提出「太多 Poly-Trader custom skills 與文件可能限制 PM/agent 判斷」是合理風險。PM 接受此風險為目前治理要求：文件與 skills 只能作為地圖，不得成為阻止客戶價值交付的籠子。

PM 下次讀取任何 skill/doc 規則時，都要回答：

1. 這條規則是否保護客戶資金與 live trading safety？
2. 還是它只是讓工程/agent 更容易維持「等待」敘事？
3. 若是後者，最小安全修補是什麼？

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付下列其中一個可驗證結果：

1. **Support evidence lane**：刷新 q15 support audit，直接顯示 current rows、rows needed、delta vs previous、stagnant count、下一筆 exact row 如何累積。
2. **Customer-usable lane**：確認 `/execution` 的 paper/shadow 或 dry-run readiness 是可操作的，並用 route/API/test 證明。
3. **Venue proof lane**：產出 OKX dry-run / metadata-to-runtime proof checklist，明確 credential present 只顯示布林，不泄漏 secret。
4. **Strategy Lab lane**：把 nearest-deployable Top-K 候選的「可用於研究 / 不可 live」狀態用操作員繁中 copy 顯示清楚。
5. **Deadlock evidence lane**：如果仍主張不能推進，必須指出是 Map / Tool / Signal / Constraint / Review 哪個 harness gap，並提出一小時內的 harness repair。
6. **Framework simplification lane**：若 custom skills/docs 造成反覆等待，必須點名限制來源並提出不降低安全 gate 的簡化、旁路或文件修補。

---

## 6. Next-hour gate

**Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據；工程 heartbeat 提供的不是「等」，而是一個 artifact / route / test / UI proof。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 將把狀態升級為 `ORANGE_customer_value_gap`；若原因來自文件/skills/harness 過度限制，升級為 `ORANGE_framework_capture_risk` 並要求先修框架；若連續三次沒有 artifact movement，升級為 `RED_delivery_deadlock` 並要求工程 heartbeat 先修 harness gap。
