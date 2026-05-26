# Structural live-readiness analysis — equilibrium deadlock escape

Generated: `2026-05-26T06:55:24Z`

## Executive verdict

**這是結構性問題，不是單純資料不足。** 目前已經不應再把主迴圈寫成「反覆蒐集與驗證同一個 exact bucket」。

- current support: `7/50`，gap `43`
- support delta: `0`，stagnant runs `5`
- semantic delta: `0`，semantic stagnant `5`
- deadlock: `True` / `closed_loop_support_identity_starvation_under_static_gate`
- execution stance: signal `HOLD`, allowed_layers `0`, order_submission_enabled `False`
- single failed gate: `current_live_support_gate`

**Practical target:** 小資本實戰是終局目標；但下一步必須是 structural redesign + bounded venue/control-plane proof，而不是直接 live buy/add，也不是再把相同 under-minimum 狀態跑一輪。

## Why the current loop is theatrical / non-productive

目前迴圈的問題不是「還沒等夠久」，而是：

1. **Support identity combinatorial sparsity** — target/horizon/bucket/regime/gate/entry-quality/calibration 被綁成 exact key，市場狀態一切換就把 evidence 切碎。
2. **Closed-loop gate starvation** — under-minimum → 要求蒐集 exact rows → current state 無法產生可部署 rows → 下一輪仍 under-minimum。
3. **Aggregate quality and current actionability are mixed** — breaker 或 Top-K 可以 green，但 current live support 還是 red；這只能證明 strategy family 有價值，不能證明現在這一筆可下。
4. **Execution control plane 尚未證明** — 小資本也需要 venue lifecycle、symbol cap、max qty、ack/cancel/fill/reconcile；否則不是小資本實戰，而是未受控風險。

## Structural root causes

| Root cause | Evidence | Practical implication |
|---|---|---|
| support identity 過度 exact 化 | `7/50`, gap `43`, semantic 連續 `5` 輪 delta=0 | 必須定義 exact fields vs semantic family fields |
| gate starvation | `equilibrium_deadlock_confirmed=true` | 下一輪 artifact 必須是結構性 proof，不可只重述 blocked |
| strategy validity/actionability 混在一起 | release/breaker 可改善但 `single_failed_gate=current_live_support_gate` | aggregate green 只能進 paper-shadow，不可覆蓋 current red |
| venue/control-plane 未完成 | `micro_canary_ready=false`, `order_submission_enabled=false` | 先建 bounded canary control plane，再談實戰買入 |

## Anti-treadmill rule

Stop doing:

- 以「再蒐集 rows」作為主要回答。
- 重跑 observation-only heartbeat，只更新 timestamp。
- 把 breaker/release green 說成 deploy-ready。
- 把 proxy/neighbor/legacy reference rows 當 current exact support。

Must do instead:

- support identity compression/redesign proof。
- drift-aware rebaseline go/no-go。
- bounded live-canary control-plane proof。
- shadow trade ledger：記錄如果小資本實戰會怎麼做、結果如何，但先不冒真錢風險。

## Target architecture: Structural Live Readiness Architecture v1

1. **L0 Execution Safety Kernel**
   kill switch、live/dry-run mode、venue credentials、ack/cancel/fill/reconcile、symbol allowlist、max qty cap。未知或缺失一律 fail-closed。

2. **L1 Strategy Validity Proof**
   walk-forward/OOS/ROI/drawdown/high-conviction validation。它回答「策略族是否值得」，不直接回答「現在這一筆可不可下」。

3. **L2 Live-context Adapter**
   把 current bucket 映射到 deployable support family；明確列出哪些欄位必須 exact，哪些可以是 semantic/calibration context。這是目前最核心的結構性缺口。

4. **L3 Bounded Micro-canary Policy**
   只有在 L0-L2 通過後，才允許極小 cap live pilot：symbol allowlist、max_base_qty、per-run max loss、cooldown、manual kill。

## Next non-repetitive work packages

### WP1 — support identity compression proof

Owner lane: `D_map_signal_redesign_for_current_bucket`

Goal: 判定 `entry_quality_label` / `regime_label` / `calibration_window` 哪些能壓縮成 semantic family，哪些必須 exact。

Success condition: 新 identity 不是降門檻，而是在 recent/OOS/replay 下保留 ROI/drawdown 優勢，且 current bucket 能被合理映射。

### WP2 — drift rebaseline go/no-go

Goal: 用 fresh window / walk-forward 檢查 q15 current bucket 是否 stale。

Success condition: 若 stale，直接 retire current bucket，不再繼續收集同一 dead bucket。

### WP3 — bounded venue canary control plane

Goal: 完成 venue lifecycle proof 與 explicit small-cap policy。

Required proof:

- symbol allowlist
- max_base_qty cap
- buy/add missing policy 在 adapter.place_order 前 reject
- wait/hold no-order OK
- reduce/sell risk-off path 在安全時保留
- ack/cancel/fill/reconcile 可稽核

### WP4 — shadow trade ledger

Goal: 把 hypothetical buy/add/reduce/wait 寫入 ledger，追蹤「如果小資本實戰會發生什麼」。

This is the bridge from research to real trading without pretending the current gate has passed.


## WP1 support identity compression result

Source: `data/q15_support_fill_feasibility.json`

- decision: **candidate_found_not_deployable**
- selected_candidate_id: `rebaseline_calibration_window_only`
- selected_candidate_rows: **2651**
- selected metrics: `{"rows": 2651, "win_rate": 0.6616, "target_counts": {"1": 1754, "0": 897}, "avg_pnl": 0.0056, "avg_quality": 0.2904, "avg_drawdown_penalty": 0.1588, "avg_time_underwater": 0.4556}`
- live_exposure_allowed: **False**

Interpretation: 已找到 `calibration_window` rebaseline 候選，可用來打破 exact-key 蒐集死循環；但它不是部署清關。下一步必須用 compressed identity 重跑 replay/OOS/Top-K/support audit 與 API guardrail，buy/add 仍 fail-closed。

## Decision boundaries

Allowed now:

- paper/shadow decisions
- venue lifecycle drill without buy/add exposure
- wait/hold no-order checks
- risk-off reduce/sell checks when account state makes it safe

Not allowed now:

- automated live buy/add
- lowering support minimum
- using proxy/reference rows as exact deployable support
- calling breaker green live-ready

If Kazuha manually trades outside the system, record it as `external/manual experiment`; Poly-Trader must not label it as system-approved live signal.

## Machine-readable artifact

`data/structural_live_readiness_analysis.json`
