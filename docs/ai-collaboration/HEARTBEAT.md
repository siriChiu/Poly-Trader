# docs/ai-collaboration/HEARTBEAT.md — Poly-Trader 心跳流程

> 本文件是 heartbeat 執行規範，不是單輪更新 log。每輪產出的 `data/heartbeat_*` summary/progress/report 預設為 generated artifact，不應提交到 git；current state 只落在 `ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md` 與 machine-readable artifacts。

---

## 1. 目標

Heartbeat 的目的不是「回報狀態」，而是讓專案閉環前進：

1. 收集最新事實。
2. 找出 current P0/P1 blocker。
3. 做最小但高價值的 patch。
4. 驗證 patch。
5. overwrite sync current-state docs。
6. 留下下一輪 gate。

若一輪只有 summary、沒有 patch/verify/current-state sync，視為不完整。

若同一 semantic signature / blocker 連續兩輪沒有 customer-value delta，heartbeat 不得再產出 observation-only status refresh；必須選擇 Map/Signal redesign、customer-safe paper/shadow proof、venue lifecycle proof、或明確 hard no-go，並把選擇同步到 `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`。

### 1.1 Harness engineering / 一問一答擴充

Heartbeat 也要符合 repo-native harness engineering：不是靠單次 prompt 記憶，而是靠可導航文件、可機械驗證的 Q&A gate、agent-readable artifacts 與回饋迴圈推進。

- 入口地圖：`docs/ai-collaboration/harness/README.md`
- 每輪問答 gate：`docs/ai-collaboration/harness/heartbeat-qa.md`
- machine-readable 契約：`docs/ai-collaboration/harness/heartbeat-harness-contract.json`
- 結構檢查：`python scripts/heartbeat_harness_check.py --format text`

若 heartbeat 卡在同一 blocker 超過兩輪，下一輪必須先回答：缺的是 Map / Tool / Signal / Constraint / Review 哪一種 harness 能力，而不是只重寫敘事。

### 1.2 anti-equilibrium execution governor / 反平衡強制執行

反平衡不是口號，而是 heartbeat completion gate。任何 run 符合下列任一條件，都必須觸發 `HQ9_anti_equilibrium_execution`：

- `support_progress.delta_vs_previous=0` 且 `regression_basis=same_identity_same_semantic_signature`。
- 同一 current-live bucket / blocker 連續兩輪以上沒有 artifact movement。
- PM 或使用者指出「又趨近平衡 / 反反覆覆 / 太久」。
- safe lane 仍存在但沒有新增 customer-value delta。

觸發後，本輪輸出不得只是 status sync；必須留下至少一個可驗證位移：

1. **Map/Signal redesign**：改 current-live bucket/support identity 或 signal map，並產出重跑 artifact。
2. **Customer-safe shadow proof**：把 Top-K / Strategy Lab 候選轉成 paper/shadow 24h outcome 或 falsification artifact。
3. **Venue lifecycle proof**：推進 OKX credential boolean、ack/cancel/fill/reconciliation proof；secret 只可顯示 `[REDACTED]` 或 boolean。
4. **Bounded live-canary hard gate**：若要準備真實買入 / 加倉，必須走 `execution.live_canary.enabled=true + allowed_symbols + max_base_qty_by_symbol`，否則在 adapter 前拒單。
5. **Hard no-go**：如果仍不能前進，必須寫明唯一失敗 gate 與下一個能解除該 gate 的 artifact；禁止再產出模糊「繼續觀察」。

### 1.3 外部 governor 與反自我認證

每輪在 Agent 開始分析前，先執行：

```bash
python scripts/heartbeat_governor.py --format text
```

`scripts/heartbeat_governor.py` 是外部、可重跑的 machine gate，不接受 Agent 自己判定「這輪做得很好」作為證據。它會從 current artifacts 計算 semantic signature、support delta、runtime freshness、連續重複次數與唯一 forced branch，並寫入：

- `data/heartbeat_governor_state.json`
- `data/heartbeat_governor_brief.json`

每輪都必須遵守：

- `ANTI_SELF_CERTIFICATION=ACTIVE`；agent may not self-certify。
- checker `PASS` 只代表機械規則通過，不代表產品 blocker 已解除。
- 沒有新 artifact、獨立 verifier 或可重現 customer-value delta，不得宣稱 progress / resolved / live-ready。
- `forced_execution_required=true` 時，不得只做 observation-only status refresh；必須執行 brief 指定的 forced branch，或輸出唯一 hard no-go gate。
- live buy/add 的 fail-closed 邊界永遠優先於 heartbeat 的「完成」敘事。

若 governor 與 Agent 敘事衝突，以 governor、machine artifacts、獨立驗證結果為準；Agent 必須降低信心，不得替自己補證。

---

## 2. 固定順序

1. **Preflight**
   - `git status --short --branch`
   - `python scripts/heartbeat_harness_check.py --format text`（確認 harness map / Q&A gate / doc references 未腐爛）
   - 確認是否已有未提交變更，避免覆蓋使用者工作。
   - 讀取上一輪 PM heartbeat 結論與決定（cron `context_from` 注入或 PM current-state docs），並在本輪明確寫出要承接的 PM handoff；工程 heartbeat 的 P0/P1 選擇必須先對齊這個 PM handoff。
   - 讀取 `ISSUES.md`、`ROADMAP.md`、`ORID_DECISIONS.md` 與最新 machine artifacts。

2. **Facts collection**
   - `--no-collect` heartbeat 仍必須檢查 `/api/strategy_data_sync` freshness；raw/features/labels/strategy 任一 lane 已 stale，或距 stale 門檻剩餘 ≤10 分鐘時，先執行本機 bounded strategy data sync maintenance，再進入 diagnostics。
   - raw/features/labels counts
   - live predictor / runtime closure
   - recent drift / circuit breaker
   - leaderboard / strategy state
   - venue readiness / execution metadata

3. **Decision framing**
   - P0/P1 blocker-first。
   - 先說明「上一輪 PM heartbeat 要求 / 決定」如何影響本輪工程取捨；若 PM 決定與 runtime 事實衝突，先用 artifacts/tests/browser/API 驗證後再裁決。
   - 先分清 current-live blocker、venue blocker、research blocker。
   - 不把 reference-only patch 寫成 deployment closure。
   - 若同一 blocker/support signature 沒有位移，先執行反平衡分支；不得直接進入下一段 status narrative。

3.5. **六色帽 + ORID**
   - **白帽**：只列 machine-readable facts、freshness、失敗命令與 dirty boundary。
   - **紅帽**：列出使用者 / 客戶目前的痛點、焦慮與不可接受的體驗，不把情緒當成證據。
   - **黑帽**：列出最可能的 failure mode、回歸風險、錯誤自我肯定與安全邊界。
   - **黃帽**：列出本輪能交付的 customer-safe value 與實際效益前提。
   - **綠帽**：至少提出一個不同於上一輪的替代路徑；同一 blocker 重複時不得只換措辭。
   - **藍帽**：選出唯一 P0/P1 action、owner、artifact、verifier、成功 gate 與失敗 fallback。
   - 接著用 ORID 收斂：`O=客觀事實`、`R=反應與風險感受`、`I=根因與意義`、`D=決定與下一步`。
   - 若六帽與 ORID 沒有產出可執行的 artifact / verifier，該輪視為 incomplete。

4. **Patch**
   - 優先修會影響 operator truth 或 live safety 的問題。
   - 保持小步、可測、可回滾。
   - 真實交易入口必須 fail-closed。

5. **Verify**
   - targeted pytest
   - frontend contract tests
   - `npm run build`
   - 必要時 browser QA

6. **Docs sync**
   - overwrite `ISSUES.md / ROADMAP.md / ORID_DECISIONS.md`。
   - `ARCHITECTURE.md` 只更新穩定契約，不寫每輪流水帳。
   - run logs 留在 ignored `data/heartbeat_*`。

7. **Git hygiene**
   - `git diff --check`
   - secret scan
   - commit with concise heartbeat/change summary
   - push

---

## 3. Current-state docs contract

| File | Contract |
|---|---|
| `ISSUES.md` | 只保留目前有效 blocker 與驗證入口 |
| `ROADMAP.md` | 只保留目前計畫、完成項與下一步 |
| `ORID_DECISIONS.md` | 只保留當前 ORID 判斷 |
| `ARCHITECTURE.md` | 只保留穩定架構與操作契約 |
| `docs/ai-collaboration/HEARTBEAT.md` | 只保留本流程規範 |

禁止把每輪 heartbeat summary 持續 append 到這些文件。若需要歷史，使用 git history 或本機 ignored artifacts。

---

## 4. Generated artifact policy

預設 ignored / 不提交：

- `data/heartbeat_*_summary.json`
- `data/heartbeat_*_progress.json`
- `data/heartbeat_*_summary.md`
- `data/heartbeat_*_report.md`
- `data/heartbeat_*_report.txt`
- `HEARTBEAT_*_SUMMARY.md`
- `HEARTBEAT_SUMMARY*.md`

可以提交但要有理由與驗證：

- current-state machine artifacts used by API/UI contracts
- docs/analysis 中可重跑且仍被 UI/docs 引用的摘要
- model artifacts only when needed for runtime behavior and no secret/data leakage

---

## 5. Live execution safety contract

在 current-live blocker、initial sync、runtime proof 缺失或 venue proof 缺失時：

- buy/add exposure：fail-closed。
- automation enable：fail-closed。
- high-conviction Top-K 候選若已通過離線 / 風控 gate、但 current-live support / venue proof 尚未解除，只能進入 `paper_shadow` 影子觀察；control plane payload 必須保留 `risk_on_order_enabled=false` 與 `runtime_binding_status=paper_shadow_runtime_blocked`，不得送單或加倉。
- 任何 live buy/add pilot 必須先通過 bounded live-canary policy：`execution.mode=live`、`enable_live_trading=true`、`execution.live_canary.enabled=true`、explicit `allowed_symbols`、symbol-specific `max_base_qty_by_symbol`；缺 policy 或超過 cap 必須在 adapter 前拒單。
- reduce/de-risk、manual mode、diagnostics、refresh：保持可用。
- `/api/trade` 必須用 structured 409 告訴前端 blocked side/reason。

此契約優先於任何 UI 便利性或 leaderboard 建議。

---

## 6. 最低驗證組合

```bash
source venv/bin/activate
python scripts/heartbeat_harness_check.py --format text
python scripts/pm_heartbeat_check.py --format text
python scripts/repo_cleanroom_audit.py --format text
python scripts/active_backend_health_probe.py --base-url http://127.0.0.1:8000 --timeout 10 --strict
python -m pytest tests/test_heartbeat_harness_contract.py -q
python -m pytest tests/test_repo_hygiene.py -q
python -m pytest tests/test_server_startup.py -k 'api_trade or current_live_trade_blocker' -q
python -m pytest tests/test_execution_run_control.py -q
python -m pytest tests/test_execution_service.py -k live_canary -q
python -m pytest tests/test_frontend_decision_contract.py -q
cd web && npm run build
```

若修改 heartbeat runner，再加：

```bash
source venv/bin/activate
python -m pytest tests/test_hb_parallel_runner.py -q
```

---

## 7. 失敗處理

- 測試失敗：先修 root cause，不要只改測試文案。
- docs stale：修 overwrite sync 或 artifact source，不追加人工補丁。
- artifact stale：重建或明確標為 stale/reference-only。
- live safety 不明：預設 fail-closed buy/add exposure，保留 reduce/de-risk。
