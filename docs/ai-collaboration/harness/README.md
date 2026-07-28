# Poly-Trader Heartbeat Harness Engineering

> 參考 OpenAI〈Harness 工程：在智慧體優先的世界中善用 Codex〉：人的工作是掌舵、設定目標、設計環境與回饋迴圈；代理負責執行、驗證、修正。Poly-Trader 的 heartbeat 不應只是 prompt 或報告，而要成為一套可被代理讀取、操作、驗證、持續改良的 harness。

---

## 1. 這份 harness 解決什麼

原本 heartbeat 已經能閉環做 facts → blocker → patch → verify → docs sync。Harness engineering 的下一步，是把這個閉環變成：

1. **可導航**：代理不需要讀完整 repo，先讀入口地圖，再漸進式展開。
2. **可問答**：每輪心跳都用固定問題逼自己輸出 evidence，而不是只寫敘事。
3. **可機械驗證**：關鍵規則不只寫在 Markdown，也由 script / pytest 檢查。
4. **可觀測**：runtime truth、artifacts、UI/API surfaces 都要能被代理直接讀取。
5. **可演進**：當同一 blocker 反覆出現時，修 harness 能力，而不是只換一段 prompt。
6. **反平衡**：同一 semantic signature / support delta=0 重複時，heartbeat 必須切到 structural pivot、shadow proof、venue proof、bounded live-canary hard gate 或 hard no-go。

---

## 2. 入口地圖

| 檔案 / 指令 | 角色 |
|---|---|
| `AGENTS.md` | 最短 repo 入口地圖；只放導航，不放百科全書 |
| `docs/ai-collaboration/AI_AGENT_ROLE.md` | 代理身份、硬邊界、自主執行紀律 |
| `docs/ai-collaboration/HEARTBEAT.md` | heartbeat 操作流程規範；不是 run log |
| `docs/ai-collaboration/harness/heartbeat-qa.md` | 每輪 heartbeat 的一問一答 gate |
| `docs/ai-collaboration/harness/heartbeat-harness-contract.json` | machine-readable harness 契約 |
| `scripts/heartbeat_harness_check.py` | 機械檢查：檔案、連結、Q&A gate、doc references |
| `scripts/active_backend_health_probe.py` | 驗證 active `/health` 是 current-head、startup continuity 可用；stale backend 要先重啟，不能拿舊 API payload 當 operator truth |
| `scripts/high_conviction_topk_api_consistency_probe.py` | 驗證 `/api/models/leaderboard.high_conviction_topk` 與 `data/high_conviction_topk_oos_matrix.json` 的 counts、nearest candidate、support rows、breaker release math、fail-closed gate、secret-safe 欄位同源 |
| `scripts/venue_dry_run_api_consistency_probe.py` | 驗證 `data/venue_dry_run_proof.json`、`/api/status`、`/api/execution/overview` 的 venue proof 同源、fail-closed、secret-safe；status compact probe 另需保留 `live_canary_policy_gate` |
| `scripts/paper_shadow_outcome_reconciliation.py` | 重算並持久化 `data/paper_shadow_outcome_reconciliation.json`；schema v2 提供 top-level / `quick_read` pending、ETA、resolved、label-replay 與 fail-closed flags；pending 期間禁止重複 worker poll，24h 後轉 resolved 或 label replay，且 strict gate 保持 fail-closed |
| `scripts/paper_shadow_outcome_api_consistency_probe.py` | 驗證 `/api/execution/overview.paper_shadow_outcome_reconciliation` 與 `data/paper_shadow_outcome_reconciliation.json` 的 schema-v2 quick-read、pending guard、fail-closed flags、secret-safe 欄位同源 |
| `scripts/customer_safe_alternative_api_consistency_probe.py` | 驗證 `/api/execution/overview.customer_safe_alternative_proof` 與 `data/customer_safe_alternative_proof.json` 的 alternative aliases、counts、summary mirror、fail-closed flags、secret-safe 欄位同源 |
| `docs/README.md` / `scripts/doc_topology_check.py` | 文件分類與 root/docs/data 邊界檢查；Markdown report companion 放 `docs/analysis/`，machine truth 留 `data/*.json` |
| `scripts/repo_cleanroom_audit.py` | 盤點 / 清理 repo 本地 generated noise；只刪 root scratch scripts、per-run heartbeat logs、runtime logs、generated scan scratch、cache、frontend build output 與 CatBoost scratch，保留 venv、DB、model、current-state artifacts，並列出大型 protected artifacts 供人工決策 |
| `scripts/auto_propose_fixes.py` | blocker 自動提出 / 更新 / resolve |
| `scripts/heartbeat_governor.py` | 外部 anti-self-certification governor；計算 semantic signature、repeat count、support stagnation 與 forced branch，不接受 Agent 自評 |
| `ISSUES.md` / `ROADMAP.md` / `ORID_DECISIONS.md` | current-state only，由 heartbeat overwrite sync |
| `scripts/hb_parallel_runner.py` | heartbeat runner 主入口；序列 lane 會先跑 active backend health strict probe，失敗會進 summary / final status |

> 原則：`AGENTS.md` 是地圖，不是手冊；詳細規則放到 `docs/ai-collaboration/HEARTBEAT.md`、`docs/ai-collaboration/harness/*` 與可測腳本。

---

## 3. Harness engineering 對應到 Poly-Trader

| OpenAI harness principle | Poly-Trader 落地 |
|---|---|
| Human steers, agents execute | 使用者定方向；heartbeat 代理負責收集、patch、驗證、同步 docs、push |
| Maps over manuals | `AGENTS.md` 只導向 `docs/ai-collaboration/HEARTBEAT.md` / `docs/ai-collaboration/harness/*` / graphify |
| Agent-readable app signals | `data/*.json`、`issues.json`、API payload、frontend contract tests、browser QA |
| First-class docs / plans | current-state docs overwrite；`docs/plans/` 與 `docs/analysis/` 保持可追溯 |
| Mechanical constraints | pytest、repo hygiene、harness checker、API/frontend contract tests |
| Observability loops | live probe、drift report、metadata smoke、execution readiness、leaderboard freshness |
| Review loops | heartbeat Q&A gate + targeted tests + `git diff --check` + commit/push |
| Doc gardening | checker 驗證入口文件和 Q&A gate 沒有腐爛；stale docs 要修來源同步 |

---

## 4. 每輪 heartbeat 的預設 Q&A 流

完整問題見 [`heartbeat-qa.md`](heartbeat-qa.md)。最短版本：

1. **我現在在哪裡？** → repo / branch / dirty files / graphify 狀態。
2. **上一輪 PM heartbeat 決定了什麼？我要解哪個 P0/P1？** → 先承接 PM handoff，再從 `ISSUES.md`、artifacts、runtime truth 選一個 blocker。
3. **這是產品 blocker、研究 blocker、還是 harness blocker？** → 不混淆部署閉合與參考 patch。
4. **缺的是能力、證據、還是文件地圖？** → 若代理無法自驗，先補 harness。
5. **最小 patch 是什麼？** → 小步、可測、可回滾，真實交易 fail-closed。
6. **我如何證明它有效？** → script / pytest / build / browser / artifact freshness。
7. **current-state docs 是否覆寫同步？** → 不 append 歷史流水帳。
8. **是否又趨向穩定？** → 若是，強制選 anti-equilibrium branch，不允許 observation-only。
9. **下一輪 gate 是什麼？** → 成功條件與 fallback 必須 machine-readable。

---

## 5. 機械檢查

```bash
source venv/bin/activate  # 若 venv 可用；此 checker 僅用 Python stdlib
python scripts/heartbeat_harness_check.py --format text
python scripts/repo_cleanroom_audit.py --format text
python -m pytest tests/test_heartbeat_harness_contract.py -q
```

`heartbeat_harness_check.py` 只檢查 harness 結構，不會修改任何 runtime artifact。若它失敗，優先修入口地圖、Q&A gate 或 contract，而不是繞過檢查。
`repo_cleanroom_audit.py --clean` 只清本地 generated noise（runtime logs / generated scan scratch / caches 等）；不要用 `git clean -fdX` 取代它，因為後者會刪 venv / DB / model / current-state artifacts。

---

## 6. 維護規則

1. 新增 heartbeat 能力時，同步更新 `heartbeat-harness-contract.json` 與 `heartbeat-qa.md`。
2. 不把 per-run summary 追加進 `docs/ai-collaboration/HEARTBEAT.md` 或 `docs/ai-collaboration/harness/*`；歷史交給 git history / ignored artifacts。
3. 若代理連續兩輪只能回報同一問題，下一輪必須問：**缺少哪個 harness 能力讓我無法前進？**
4. 若 `support_progress.delta_vs_previous=0` 且 same semantic signature 重複，下一輪必須執行 `HQ9_anti_equilibrium_execution`，並更新 current-state docs 的 forced branch。
5. 若 UI/API/runtime truth 不能被腳本或 browser QA 讀到，就不是完整 harness。
6. 若文件與 machine artifact 衝突，修同步來源；不要在 Markdown 手補相反敘事。
