# Poly-Trader As-Is Gating Lineage Audit

> 目的：把「策略好不好」「owner 願不願承擔」「目前訊號能不能進」「這筆訂單能不能送」拆開。現況欄是 source-backed characterization；to-be 欄只是重構方向。

## 1. 正確的狀態維度

現行 payload 經常用 `deployable/live_ready/allowed_layers` 承載不同問題。實際至少有五個獨立維度：

1. `evidence_status` — 研究證據是否足以評估。
2. `release_status` — owner 是否核准某個 strategy identity。
3. `runtime_binding_status` — 執行 runtime 是否載入同一 identity。
4. `market_actionability` — 當前 market snapshot 是否允許持有/進場/加層。
5. `order_authorization` — 這筆 order 是否可在 venue 上送出。

只有第 5 項能授權訂單；前四項都不能單獨轉成 live permit。

## 2. Gate lineage matrix

| Gate | 現行計算者 | 權威輸入 | 現行輸出/持久化 | 類型 | 已知問題 | To-be owner |
|---|---|---|---|---|---|---|
| Data continuity/freshness | collector、feature coverage、API sync | DB timestamps/source status | runtime status、API、JSON/docs | capability | 同一 freshness 在多處重算；no-collect heartbeat 可偷偷 maintenance write | DataReadinessService |
| Feature eligibility | preprocessor/train/coverage scripts | feature rows/non-null counts | DB、coverage artifacts | evidence/capability | feature version 未鎖；missing 0/None/median 語義混合 | FeatureContract |
| Label eligibility | labeling/train | 1440m rows/target non-null | labels DB | evidence | label definition 無 version；固定金字塔 target 與可變 strategy 可能 mismatch | LabelContract |
| Model evidence | ModelLeaderboard/Top-K | walk-forward folds、ROI/DD/PF/trades | memory/disk/DB/JSON | advisory/release input | cache、request overlay、artifact freshness 多層；排名與 release 混用 | StrategyEvidenceService |
| Exact support | predictor DQ + q15/q35 artifacts | current semantic bucket rows | predictor/Top-K/artifacts/docs | 現況同時作 blocker/advisory | owner release 已將統計支持降 advisory，但 predictor 仍可先令 layers=0；語義衝突 | EvidencePolicy（不直接碰訂單） |
| Owner personal release | `personal_release.py` | config selector、OOS row | predictor/Top-K fields | release | `apply_runtime_release_policy` 未再次 selector-match；release status 可出現在不匹配 runtime 上 | ReleaseRegistry |
| Runtime binding | personal release + strategy bundle + live runner | model/profile boolean；另一路 artifact SHA/schema | payload/bundle/files | deployment | 兩套 proof 未整合；personal binding 不驗 SHA/schema/regime/top-k | BundleRegistry |
| Regime/entry quality | strategy_lab + predictor + live_runner | latest features | signal/profile/payload | market actionability | 同一公式多份；predictor有patch/overrides，runner 另算 baseline | DecisionKernel |
| Decision quality/toxicity | predictor | historical labels/scopes/artifacts | allowed_layers/blocker | market capacity | 診斷、支持、trade floor、patch 同函式；artifact可 override DB-derived result | RiskCapacityPolicy |
| Circuit breaker | predictor | recent canonical labels | signal/blocker/audit | hard risk | 由 labels 而非 actual realized executions 驅動；名稱像 execution breaker 但本質是 model outcome breaker | ModelHealthCircuitBreaker |
| Microstructure/cost-aware edge | API status | microstructure artifact + config costs | API projection | observation-only | 在 API 組裝，未成為 order boundary；`order_submission_enabled=false` 是 copy，不是 enforcement | MarketExecutionQualityPolicy |
| Venue readiness | metadata smoke/adapter health | config/env/CCXT/proofs | artifact/API | capability | artifact readiness與 adapter實際 call 分離；可能 stale | VenueCapabilityService |
| Live config triple | ExecutionService | mode/live flag/dry_run/adapter dry_run | reject code | hard safety | 正確 fail-closed；應保留 | ExecutionAuthorizer |
| Canary policy | ExecutionService + strategy bundle/API helper | enabled/allowlist/cap/kill switch | reject/readiness fields | hard safety | allowlist 為空時實作不拒絕，與「explicit allowlist」文案矛盾 | ExecutionAuthorizer |
| Execution permit | ExecutionService | signed claims、scope、TTL、nonce DB | permit consumption/reject | hard safety | manual API/runner不傳 permit，沒有成功 live journey | PermitService |
| Order normalization | adapter/ExecutionService | market rules/min qty/tick/notional | reject/lifecycle | hard safety | 應保留；metadata freshness需綁 quote/market snapshot | VenueOrderGateway |
| Duplicate/idempotency | live runner + permit nonce | decision count/feature timestamp | DB decisions | hard safety | check-then-write非 atomic；client ID contract未成為 unique invariant | OrderIntentRepository |
| Order lifecycle/reconciliation | ExecutionService/control plane | venue result/trade/order events | DB/artifact/API | hard safety | local rehearsal可用，但 exchange runtime proof缺；run ledger與trade ledger分離 | OrderLifecycleService |
| Artifact freshness | heartbeat/API/PM | mtime/generated_at/semantic signature | JSON/docs/UI | governance | TTL與語義 identity分散；fresh 不代表同 generation | ArtifactRegistry |
| Worker liveness | control plane/worker tests | PID/heartbeat/lease/run row | API | operations | persisted `running` 不等於 live worker；測試已識別但 projection仍複雜 | WorkerLeaseService |

## 3. Gate ownership violations

### 3.1 Exact support 同時扮演三種角色

- predictor 把低於 50 exact rows 轉成 deployment blocker並令 layers=0；
- personal release 把 statistical gate 降成 position-sizing warning；
- Top-K live overlay 再算一次 deployable；
- PM/current docs 又把 support 當 72h single failed gate。

這不是單一「門檻太高」，而是同一數字沒有固定分類。To-be 必須由 owner 決定：它是 evidence advisory、release gate、deployment gate，還是 execution gate；不可同時是四者。

### 3.2 Runtime binding 有兩個真相

`personal_release._binding_matches()` 的實際契約：

- `binding.verified is True`
- model 相等
- feature profile 相等

但 `strategy_bundle`/live runner 的 exact artifact 契約還包括策略定義、fitted artifact、SHA、schema、target 等。文件宣稱後者，release overlay 實作卻只用前者，造成「顯示 binding verified」不等於可重現 bundle。

### 3.3 `allowed_layers` 同時是策略輸出與 safety override

原始層數由 regime/entry-quality 決定；DQ、support、breaker、release binding 再依序改寫同一欄位。雖另有 `allowed_layers_raw`，但 reason 仍會被不同 overlay 覆蓋。API/UI 只能看到最終結果，難以分辨：

- 市場真的沒有 entry；
- 統計 evidence 不足；
- owner strategy 不匹配；
- execution plumbing 不完整。

To-be 應輸出 `market_capacity`, `evidence_cap`, `technical_cap`, `final_capacity` 四欄，而不是反覆 mutate。

### 3.4 Circuit breaker 命名混淆

目前 breaker 讀的是 1440m `simulated_pyramid_win` label，不是實際 live order PnL。它是**model/outcome health gate**；ExecutionService 另有 daily loss、consecutive failure、kill switch。兩者都叫風控/熔斷，容易被 AI 合併。

### 3.5 Readiness projection 不等於 enforcement

- API 的 microstructure/cost-aware edge 設 `order_submission_enabled=false`，但這是 projection。
- ExecutionService 的 live triple/canary/permit 才是真正 enforcement。
- metadata smoke artifact 可說 venue not ready，但 order boundary 最終仍以 adapter/config/call 判斷。

To-be 每個 gate 必須標 `enforced_at`，避免只改 UI JSON 就以為安全已落地。

## 4. 資訊世代與 fallback 問題

### 4.1 多世代 aggregate

一次 `/api/status` 可能同時包含：

- request-time predictor結果；
- DB latest features/labels；
- config/env；
- `data/*.json` 的上一輪 q15/q35/drift/venue proof；
- process-global refresh狀態；
- fallback operator copy。

payload 沒有共同 `generation_id/as_of/input_versions`，所以欄位各自 fresh 仍可能彼此不一致。

### 4.2 Fallback 隱藏 capability failure

常見模式：

- 4H fetch exception → neutral/default；
- missing feature → 0/median；
- missing regime → heuristic/neutral；
- missing model → DummyPredictor或 runtime retrain；
- stale cache → disk/memory/background refresh；
- missing artifact field →從 blocker/exact scope/q15 artifact多路回填。

Fallback 對研究 UI 可用，但若沒有 `source`, `fallback_used`, `degraded_reason`，會污染 deployment判斷。

### 4.3 Generated docs feedback loop

`hb_parallel_runner.py` 根據 artifacts 覆寫 `ISSUES.md/ROADMAP.md/ORID_DECISIONS.md`；`AGENTS.md` 又要求 heartbeat agent 先讀它們。這形成：

```text
artifact → generated narrative → agent priority → scripts/artifacts → generated narrative
```

若 narrative 持續強調 q15/support/72h，AI 會把框架內的下一步當成唯一可能方案，即使真正瓶頸已是 label/version/runtime binding。

## 5. Deadlock patterns

1. **Wait-to-fix fallacy**：只等 rows 增加，卻不修 label/feature/identity mismatch。
2. **Moving bucket**：market regime/bucket改變，exact support counter重新開始；固定 50 在動態 identity 上可能永不 closure。
3. **Reference evidence rejection loop**：歷史/all-window rows被標 reference-only；current window不足；沒有 rebaseline authority，所以永遠 under-minimum。
4. **Patch-on-patch**：q15/q35 artifact修正 predictor，predictor再產生新 bucket，下一輪 artifact又以舊 bucket判 mismatch。
5. **Release/runtime split without registry**：owner 核准 logistic candidate，但 runtime跑 global/regime/random-forest；release保留、execution永遠 binding blocked。
6. **No live success path**：upstream全綠也沒有 permit issuer接 manual API/runner；系統只能持續證明自己會拒絕。
7. **Heartbeat anti-equilibrium churn**：規則要求每輪產生位移，導致 artifacts/docs頻繁改寫，但不一定增加產品能力。
8. **Performance/freshness feedback**：重建太慢→artifact stale→API fallback→probe失敗→heartbeat重建更多。

## 6. 必須保留的 hard safety gates

以下不能因「gating過重」而刪除，只能集中 owner並改善可解釋性：

- kill switch、daily loss、failure halt；
- exact deployed model/schema/config checksum；
- explicit symbol allowlist與order qty/notional cap；
- stale quote/max age；
- atomic idempotency/duplicate prevention；
- signed short-lived single-use permit；
- venue min qty/tick/notional normalization；
- order ack/fill/partial/cancel/reject/reconciliation；
- live credentials/runtime capability proof；
- per-run/per-strategy position attribution與exposure cap。

現況中 stale quote、atomic idempotency、per-bot ledger尚未形成完整 enforcement；BDD會標為 known gaps。

## 7. 可簡化或降級的 accidental gates

- 固定 support row threshold若已被 owner release定義為 advisory，不應在不同層又變成 execution blocker；
- historical docs中的 accuracy/IC literals不應參與 release；
- q15/q35特例應轉成版本化 policy table或移出 runtime核心；
- generated artifact freshness只應控制「可否採信該 evidence」，不能直接代替live order safety；
- PM 72h/forced-execution屬delivery governance，不是交易許可；
- UI copy/humanization test不能作 readiness proof；
- heartbeat每輪必須改 code/docs的anti-equilibrium規則應改成「有material delta才發布」。

## 8. To-be gate result schema（草案）

```json
{
  "gate_id": "runtime_bundle_binding",
  "category": "deployment",
  "status": "blocked",
  "blocking": true,
  "enforced_at": "execution_authorizer",
  "subject": {"strategy_release_id": "...", "bundle_sha256": "..."},
  "inputs": [{"source": "bundle_registry", "version": "...", "as_of": "..."}],
  "reason_code": "artifact_sha_mismatch",
  "release_condition": "load the approved immutable bundle",
  "observed_at": "...",
  "generation_id": "..."
}
```

所有 projection只能顯示此結果，不得再自行推導 blocking。
