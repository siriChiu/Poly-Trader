# ORID_DECISIONS.md — Current ORID Only

_最後更新：2026-05-15 04:08:07 CST_

---

## 心跳 #1232 + 本輪產品化 ORID

### O｜客觀事實
- fast heartbeat #1232 完成 collect + diagnostics refresh：`Raw=33231 / Features=24418 / Labels=66426`，本輪 collect pipeline `+2 raw / +2 features / +2 labels`，runner `2/2 passed`，`elapsed=13.1s`。
- current live blocker：`deployment_blocker=under_minimum_exact_live_structure_bucket`，`signal=HOLD`，`allowed_layers=0`，`execution_guardrail_reason=under_minimum_exact_live_structure_bucket`。
- current live bucket：`CAUTION|base_caution_regime_or_bias|q35`；exact support `28/50`，`gap=22`；`support_route_verdict=exact_bucket_present_but_below_minimum`；`support_governance_route=exact_live_bucket_present_but_below_minimum`。
- support progress：`status=stalled_under_minimum`；`delta_vs_previous=0`；`previous_rows=28`；`stagnant_run_count=5`；`stalled_support_accumulation=True`；`escalate_to_blocker=True`。
- high-conviction Top-K OOS matrix：`rows=24`，`deployable_rows=0`，`risk_qualified_rows=6`，`runtime_blocked_candidate_rows=6`；nearest candidate `logistic_regression/current_full/all/top_2pct` 離線 OOS/risk gate 通過，但被 live support blocker 擋下。
- 本輪產品化 patch：Dashboard `ConfidenceIndicator` 新增 support-stall blocker 卡；`runtimeCopy` 將 support stall 中文化為「連續停滯 N 輪」；Dashboard 型別接收完整 `support_progress`；frontend contract tests 鎖定停滯欄位與 q35 score-only 警示。
- 驗證：frontend contract `76 passed`；server/probe/runner suite `207 passed`；web build succeeded；heartbeat harness `RESULT: PASS`；fresh `hb_predict_probe.py` confirms q35 `28/50`、`allowed_layers=0`、support stall escalated。

### R｜感受直覺
- 最大風險不是沒有候選，而是 operator 把 `28/50`、`delta=0`、或 q35 score-only redesign 誤讀成「差不多可以部署」。
- UI 必須把停滯狀態說清楚：這不是中性等待，而是已升級為部署阻塞的 support accumulation failure。

### I｜意義洞察
1. **Support stall 是產品 blocker，不只是分析欄位**：`stagnant_run_count=5` 且 `escalate_to_blocker=True`，必須直接顯示在 Dashboard，而不能藏在 JSON artifact。
2. **Score floor cross 不等於 deployment closure**：q35 redesign 即使改善 entry quality，也仍受 exact-support minimum 與 execution guardrail 約束。
3. **OOS-pass candidate 仍需 live gate**：Top-K OOS 最近候選可進入影子驗證敘事，但 `support_route_not_deployable` 與 `deployment_blocker_active` 未解除前不能部署。
4. **文件與 UI 需同步保護同一 truth**：current-state docs、probe、Dashboard、Strategy Lab、Execution surfaces 必須都以 `under_minimum_exact_live_structure_bucket` 為唯一 current-live blocker。

### D｜決策行動
- **本輪決策**：優先產品化 support-stall visibility，而不是新增模型或弱化 guardrail。
- **已執行 patch**：`ConfidenceIndicator` 顯示 support-stall 卡與 q35 operator action；`runtimeCopy` 顯示連續停滯輪數；Dashboard typed contract 完整化；frontend regression tests 加鎖。
- **驗證通過**：`tests/test_frontend_decision_contract.py`、`tests/test_server_startup.py`、`tests/test_hb_predict_probe.py`、`tests/test_hb_parallel_runner.py`、web build、harness check、fresh probe。
- **下一輪 gate**：若 q35 exact support 仍 `28/50` 且 stagnation 增加，沿資料累積 / support identity 路徑追根因；若 UI/doc 任一 surface 不再顯示停滯 blocker，升級為 productization regression。
