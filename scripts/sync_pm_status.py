#!/usr/bin/env python3
"""Synchronize docs/pm/pm-status.md from current runtime artifacts.

The engineering heartbeat refreshes live artifacts before the next PM heartbeat
runs.  This helper keeps the PM status document aligned with those artifacts so
`scripts/pm_heartbeat_check.py` catches real drift instead of stale literals.
It is stdlib-only and secret-safe: it never emits DB URLs or credential values.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = PROJECT_ROOT / "docs" / "pm" / "pm-status.md"


def _load_json(rel_path: str) -> dict[str, Any]:
    path = PROJECT_ROOT / rel_path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"__missing__": rel_path}
    except json.JSONDecodeError as exc:
        return {"__error__": f"{rel_path}: {exc}"}
    return payload if isinstance(payload, dict) else {"__error__": f"{rel_path}: root is not an object"}


def _first_present(*values: Any, default: Any = "—") -> Any:
    for value in values:
        if value is not None:
            return value
    return default


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _support_ready(rows: Any, minimum: Any, gap: Any, support_route: Any) -> bool:
    rows_int = _as_int(rows)
    minimum_int = _as_int(minimum)
    gap_int = _as_int(gap)
    return bool(
        support_route == "exact_bucket_supported"
        or (
            rows_int is not None
            and minimum_int is not None
            and rows_int >= minimum_int
            and (gap_int is None or gap_int <= 0)
        )
    )


def _support_clause(*, rows: Any, minimum: Any, gap: Any, support_route: Any, support_ready: bool) -> str:
    if support_ready:
        return (
            f"current exact support 已達 `{rows}/{minimum}`（gap `{gap}`、route `{support_route}`），"
            "但這只是 support gate，不是 deployment closure"
        )
    return (
        f"current exact support 仍是 `{rows}/{minimum}`、gap `{gap}`，"
        "尚未建立同一 support identity 的精準樣本"
    )


def _support_handoff_clause(*, rows: Any, minimum: Any, gap: Any, support_ready: bool) -> str:
    if support_ready:
        return f"承認 current-live exact support 已達 `{rows}/{minimum}`（gap `{gap}`），但 live gate 仍由 breaker / Top-K / venue runtime proof 共同約束"
    return "維持 current-live exact-support blocker"


def _governance_route_interpretation(governance_route: Any, *, support_ready: bool) -> str:
    route_text = str(governance_route or "")
    if support_ready:
        return "是 exact-support evidence；仍不是部署閉環，必須等 breaker、Top-K、venue/runtime gates 一起通過"
    if "proxy" in route_text:
        return "只能當治理 / proxy reference，不是部署閉環"
    return "只能當 support-governance signal，不是部署閉環"


def _bool_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "—"
    return str(value)


def _num_text(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return _bool_text(value)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.{digits}f}"


def _pct_text(value: Any, digits: int = 1) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return str(value)


def _support_progress(probe: dict[str, Any]) -> dict[str, Any]:
    details = probe.get("deployment_blocker_details")
    if not isinstance(details, dict):
        details = {}
    progress = probe.get("support_progress") or details.get("support_progress") or {}
    return progress if isinstance(progress, dict) else {}


def _runtime_blocked_rows(topk: dict[str, Any]) -> list[dict[str, Any]]:
    rows = topk.get("rows") if isinstance(topk.get("rows"), list) else []
    return [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("deployment_candidate_tier") == "runtime_blocked_oos_pass"
    ]


def _best_topk_candidate(topk: dict[str, Any]) -> dict[str, Any]:
    for key in ("nearest_deployable_candidate", "best_not_deployable", "highest_roi_not_deployable"):
        value = topk.get(key)
        if isinstance(value, dict) and value:
            return value
    rows = _runtime_blocked_rows(topk)
    return rows[0] if rows else {}


def _drift_primary(drift: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    primary = drift.get("primary_window") or drift.get("blocking_window") or {}
    if isinstance(primary, dict):
        window = str(primary.get("window") or "—")
        summary = primary.get("summary") if isinstance(primary.get("summary"), dict) else primary
        return window, summary if isinstance(summary, dict) else {}
    windows = drift.get("windows") if isinstance(drift.get("windows"), dict) else {}
    if windows:
        window, payload = next(iter(windows.items()))
        summary = payload.get("summary") if isinstance(payload, dict) and isinstance(payload.get("summary"), dict) else payload
        return str(window), summary if isinstance(summary, dict) else {}
    return "—", {}


def _safe_join(values: Any) -> str:
    if isinstance(values, list):
        return ", ".join(str(item) for item in values) or "—"
    if values in (None, ""):
        return "—"
    return str(values)


def _redact(text: str) -> str:
    text = re.sub(r"\b[A-Z][A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD)\b", "[REDACTED]", text)
    text = re.sub(r"\b[a-zA-Z0-9]+[._-](?:api[_-]?key|token|secret|password)\b", "[REDACTED]", text)
    text = re.sub(r"sqlite:////?[^\s`]+", "[REDACTED]", text)
    return text


def build_pm_status_markdown(now: datetime | None = None) -> str:
    probe = _load_json("data/live_predict_probe.json")
    drilldown = _load_json("data/live_decision_quality_drilldown.json")
    breaker = _load_json("data/circuit_breaker_audit.json")
    topk = _load_json("data/high_conviction_topk_oos_matrix.json")
    execution = _load_json("data/execution_metadata_smoke.json")
    drift = _load_json("data/recent_drift_report.json")
    fill = _load_json("data/q15_support_fill_feasibility.json")
    alt = _load_json("data/customer_safe_alternative_proof.json")

    local_now = now or datetime.now().astimezone()
    updated_at = local_now.strftime("%Y-%m-%d %H:%M %Z")

    details = probe.get("deployment_blocker_details") if isinstance(probe.get("deployment_blocker_details"), dict) else {}
    progress = _support_progress(probe)
    release = breaker.get("release_condition") if isinstance(breaker.get("release_condition"), dict) else {}
    fill_verdict = fill.get("verdict") if isinstance(fill.get("verdict"), dict) else {}
    fill_identity = fill.get("support_identity") if isinstance(fill.get("support_identity"), dict) else {}
    alt_gate = alt.get("live_deployment_gate") if isinstance(alt.get("live_deployment_gate"), dict) else {}
    alt_support = alt.get("current_live_support") if isinstance(alt.get("current_live_support"), dict) else {}
    alt_topk = alt.get("topk_shadow_candidate_context") if isinstance(alt.get("topk_shadow_candidate_context"), dict) else {}
    alt_venue = alt.get("venue_runtime_proof") if isinstance(alt.get("venue_runtime_proof"), dict) else {}

    current_bucket = _first_present(
        probe.get("current_live_structure_bucket"),
        details.get("current_live_structure_bucket"),
        alt_support.get("structure_bucket"),
    )
    rows = _first_present(probe.get("current_live_structure_bucket_rows"), details.get("current_live_structure_bucket_rows"), alt_support.get("current_rows"))
    minimum = _first_present(probe.get("minimum_support_rows"), details.get("minimum_support_rows"), alt_support.get("minimum_support_rows"))
    gap = _first_present(
        probe.get("current_live_structure_bucket_gap_to_minimum"),
        details.get("current_live_structure_bucket_gap_to_minimum"),
        alt_support.get("gap_to_minimum"),
    )
    support_route = _first_present(probe.get("support_route_verdict"), details.get("support_route_verdict"), alt_support.get("support_route_verdict"))
    governance_route = _first_present(probe.get("support_governance_route"), details.get("support_governance_route"), alt_support.get("support_governance_route"))
    support_ready = _support_ready(rows, minimum, gap, support_route)
    support_clause = _support_clause(
        rows=rows,
        minimum=minimum,
        gap=gap,
        support_route=support_route,
        support_ready=support_ready,
    )
    support_handoff_clause = _support_handoff_clause(
        rows=rows,
        minimum=minimum,
        gap=gap,
        support_ready=support_ready,
    )
    governance_route_interpretation = _governance_route_interpretation(
        governance_route,
        support_ready=support_ready,
    )
    release_ready = release.get("release_ready")
    breaker_active = (
        probe.get("deployment_blocker") == "circuit_breaker_active"
        or probe.get("runtime_closure_state") == "circuit_breaker_active"
        or breaker.get("verdict") == "canonical_breaker_active"
        or release_ready is False
    )
    release_wins = release.get("current_recent_window_wins", "—")
    release_window = release.get("recent_window", "—")
    release_required = release.get("required_recent_window_wins", "—")
    release_needed = release.get("additional_recent_window_wins_needed", "—")
    if breaker_active:
        breaker_verdict_line = (
            f"熔斷仍 active（recent `{release_wins}/{release_window}`，"
            f"需要 `{release_required}/{release_window}`，還差 `{release_needed}` 勝），"
            f"且 {support_clause}，"
            "所以 live buy/add 仍 fail-closed"
        )
        breaker_interpretation = (
            "PM interpretation: breaker is currently active; even after it clears, support evidence, Top-K deployability, "
            "and venue runtime proof must all remain verified before live exposure."
        )
    else:
        breaker_verdict_line = (
            f"熔斷已解除，但 {support_clause}，"
            "所以 live buy/add 仍 fail-closed"
        )
        breaker_interpretation = (
            "PM interpretation: breaker math is clear, but any remaining support, Top-K deployability, and venue runtime proof gates still block live exposure."
        )

    matrix_rows = topk.get("rows") if isinstance(topk.get("rows"), list) else []
    runtime_blocked = _runtime_blocked_rows(topk)
    candidate = _best_topk_candidate(topk)
    primary_window, primary_summary = _drift_primary(drift)
    venue_rows = execution.get("venues") if isinstance(execution.get("venues"), list) else []
    venue_lines = []
    for venue in venue_rows:
        if not isinstance(venue, dict):
            continue
        venue_lines.append(
            f"- {venue.get('venue', 'unknown')}: adapter_supported={_bool_text(venue.get('adapter_supported'))}, "
            f"enabled_in_config={_bool_text(venue.get('enabled_in_config'))}, "
            f"credentials_configured={_bool_text(venue.get('credentials_configured'))}, "
            f"proof_state={venue.get('proof_state', '—')}, runtime_ready={_bool_text(venue.get('runtime_ready'))}, "
            f"blockers={_safe_join(venue.get('blockers'))}。"
        )
    if not venue_lines:
        venue_lines.append("- 尚無 venue row；視為 runtime_ready=false。")

    text = f"""# PM Status — Poly-Trader Current Delivery State Only

_最後更新：{updated_at}_

> Current-state PM interpretation. Do not append hourly history here; this file is generated from current runtime artifacts by `scripts/sync_pm_status.py` so PM checks fail on real drift, not stale literals.

---

## 1. PM decision

**State：`ORANGE_framework_capture_risk` governance overlay；safe lane remains `YELLOW_shadow_or_paper_usable`；`ORANGE_alternative_solution_required` remains active.**

PM 結論：客戶成功仍是北極星，但 live buy/add safety gate 不可被 customer urgency 推翻。承接上一輪 PM handoff：{support_handoff_clause}、交付 paper/shadow / dry-run / falsification / support-fill proof，且不可降低 live gate。fresh runtime truth 顯示 current-live bucket 是 `{current_bucket}`；PM 決策不變：current exact support 是 `{rows}/{minimum}`、`gap={gap}`、`support_route_verdict={support_route}`，`support_governance_route={governance_route}` {governance_route_interpretation}。

安全答案：`signal={probe.get('signal', '—')}` / `should_trade={_bool_text(probe.get('should_trade'))}` / `deployment_blocker={probe.get('deployment_blocker', '—')}` / `runtime_closure_state={probe.get('runtime_closure_state', '—')}` / `allowed_layers_raw={probe.get('allowed_layers_raw')}` / `allowed_layers={probe.get('allowed_layers')}` / `allowed_layers_reason={probe.get('allowed_layers_reason', '—')}` / `execution_guardrail_reason={probe.get('execution_guardrail_reason', '—')}` / `api_trade_guardrail_active={_bool_text(probe.get('api_trade_guardrail_active'))}` / `api_trade_buy_guardrail={probe.get('api_trade_buy_guardrail', '—')}`。客戶可以使用 Dashboard、Strategy Lab、Execution Console、paper/shadow decision-support、Shadow Trade Ledger、venue readiness checklist、range-chop playbook 與 canary rehearsal；**真實買入 / 加倉 / live buy/add / 自動送單 / 小額 live canary 仍不可放行**，除非 bounded live-canary policy、current-live gate、support/breaker gate 與 venue lifecycle proof 全部通過。

---

## 2. Artifact truth accepted by PM

### Current-live blocker

- `data/live_predict_probe.json` generated at `{probe.get('generated_at', '—')}`；canonical target is `{probe.get('target_col', 'simulated_pyramid_win')}`。
- Runtime signal: `signal={probe.get('signal', '—')}` / `should_trade={_bool_text(probe.get('should_trade'))}` / confidence `{_num_text(probe.get('confidence'), 6)}`；`regime_label={probe.get('regime_label', '—')}` / `regime_gate={probe.get('regime_gate', '—')}` / `entry_quality_label={probe.get('entry_quality_label', '—')}` / decision quality score `{_num_text(drilldown.get('decision_quality_score') or drilldown.get('score'))}`。
- Primary blocker: `deployment_blocker={probe.get('deployment_blocker', '—')}` / `runtime_closure_state={probe.get('runtime_closure_state', '—')}`。
- Guardrail truth: `allowed_layers_raw={probe.get('allowed_layers_raw')}` but `allowed_layers={probe.get('allowed_layers')}`；`allowed_layers_reason={probe.get('allowed_layers_reason', '—')}`；`execution_guardrail_reason={probe.get('execution_guardrail_reason', '—')}`。
- Current-live support: `current_live_structure_bucket={current_bucket}`, `support_route_verdict={support_route}`, `support_governance_route={governance_route}`, rows `{rows}/{minimum}`, `gap={gap}`。
- Support progress: `support_progress_status={progress.get('status', '—')}` / `regression_basis={progress.get('regression_basis', '—')}` / `previous_rows={progress.get('previous_rows', '—')}` / `delta_vs_previous={progress.get('delta_vs_previous', '—')}` / `stagnant_run_count={progress.get('stagnant_run_count', '—')}` / legacy reference is reference-only because support identity does not close current deployment.
- Direct action truth: `api_trade_guardrail_active={_bool_text(probe.get('api_trade_guardrail_active'))}`; `api_trade_buy_guardrail={probe.get('api_trade_buy_guardrail', '—')}`; risk-off sides remain `{_safe_join(probe.get('api_trade_allowed_risk_off_sides'))}` only。

**PM verdict：接受「{breaker_verdict_line}」。不可把 legacy rows、exact-live-lane proxy rows、Top-K OOS pass、或單一 support/governance gate 包裝成 deployable。**

### Circuit breaker

- Latest artifact `data/circuit_breaker_audit.json` generated at `{breaker.get('generated_at', '—')}`；verdict `{breaker.get('verdict', '—')}`。
- Release context: `release_ready={_bool_text(release.get('release_ready'))}`, recent-window wins `{release.get('current_recent_window_wins', '—')}/{release.get('recent_window', '—')}`, required wins `{release.get('required_recent_window_wins', '—')}/{release.get('recent_window', '—')}`, `additional_recent_window_wins_needed={release.get('additional_recent_window_wins_needed', '—')}`。
- {breaker_interpretation}

### Research-to-delivery candidates / Top-K

- `data/high_conviction_topk_oos_matrix.json` generated at `{topk.get('generated_at', '—')}`；`artifact_freshness_status={topk.get('artifact_freshness_status', '—')}`, `artifact_deployment_blocking={_bool_text(topk.get('artifact_deployment_blocking'))}`, `samples={topk.get('samples', '—')}`, `row_count={len(matrix_rows)}`, `runtime_blocked_candidate_rows={len(runtime_blocked)}`。
- Matrix payload: `deployable_rows={topk.get('deployable_rows', '—')}`, `risk_qualified_rows={topk.get('risk_qualified_rows', alt_topk.get('risk_qualified_rows', '—'))}`, `support_route={topk.get('support_route_verdict', support_route)}`, `deployment_blocker={topk.get('deployment_blocker', probe.get('deployment_blocker', '—'))}`, `current_live_structure_bucket={topk.get('current_live_structure_bucket', current_bucket)}`, bucket rows `{topk.get('current_live_structure_bucket_rows', rows)}/{topk.get('minimum_support_rows', minimum)}`, `gap={topk.get('current_live_structure_bucket_gap_to_minimum', gap)}`。
- Nearest research candidate: `model={candidate.get('model', '—')}`, `feature_profile={candidate.get('feature_profile', '—')}`, `top_k={candidate.get('top_k', '—')}`, `oos_roi={_num_text(candidate.get('oos_roi'))}`, `win_rate={_num_text(candidate.get('win_rate'))}`, `profit_factor={_num_text(candidate.get('profit_factor'))}`, `max_drawdown={_num_text(candidate.get('max_drawdown'))}`, `worst_fold={_num_text(candidate.get('worst_fold'))}`, `trade_count={candidate.get('trade_count', '—')}`, `deployment_candidate_tier={candidate.get('deployment_candidate_tier', '—')}`, `deployable_verdict={candidate.get('deployable_verdict', '—')}`。

**PM verdict：Top-K remains fresh research / paper-shadow evidence. Strategy Lab 可優先顯示 nearest-deployable research rows，但 `deployable_rows=0` means no risk-on live action.**

### Venue readiness

- `data/execution_metadata_smoke.json` generated at `{execution.get('generated_at', alt_venue.get('generated_at', '—'))}`。
- Summary: `runtime_ready={_bool_text(execution.get('runtime_ready'))}`, `runtime_ready_count={execution.get('runtime_ready_count', '—')}`, `venues_checked={execution.get('venues_checked', '—')}`, `ok_count={execution.get('ok_count', '—')}`, `readiness_state={execution.get('readiness_state', '—')}`。
{chr(10).join(venue_lines)}
- Credential-like values stay secret-safe；PM status accepts only boolean/proof-state language and redacts source credentials as `[REDACTED]`。

### Recent market/model risk

- `data/recent_drift_report.json` generated at `{drift.get('generated_at', '—')}`。
- Full sample rows `{((drift.get('full_sample') or {}).get('rows') if isinstance(drift.get('full_sample'), dict) else '—')}`。
- Recent canonical window `{primary_window}`: win_rate `{_pct_text(primary_summary.get('win_rate'))}`, dominant regime `{primary_summary.get('dominant_regime', '—')}({_pct_text(primary_summary.get('dominant_regime_share'))})`, alerts `{_safe_join(primary_summary.get('alerts') or primary_summary.get('alert_flags'))}`。

**PM verdict：recent drift reinforces paper/shadow-only research and root-cause work. It cannot be packaged as a live deployment patch.**

### Support-fill feasibility / alternative-solution pressure

- `data/q15_support_fill_feasibility.json` generated at `{fill.get('generated_at', '—')}`；scanned current support identity bucket is `{fill_identity.get('current_live_structure_bucket', current_bucket)}`。
- Verdict: `classification={fill_verdict.get('classification', '—')}`, current calibration window `{fill_verdict.get('current_calibration_window', fill_identity.get('calibration_window', '—'))}`, current exact bucket rows `{fill_verdict.get('current_exact_bucket_rows', rows)}/{fill_verdict.get('minimum_support_rows', minimum)}`, identity rows before bucket filter `{fill_verdict.get('current_exact_identity_rows', '—')}`, non-current-bucket identity rows `{fill_verdict.get('current_exact_identity_non_bucket_rows', '—')}`, `gap={fill_verdict.get('gap_to_minimum', gap)}`, `time_to_evidence_bucket={fill_verdict.get('time_to_evidence_bucket', '—')}`, `missing_capability_class={fill_verdict.get('missing_capability_class', '—')}`, `alternative_solution_required={_bool_text(fill_verdict.get('alternative_solution_required'))}`。
- Reference-only evidence: `best_reference_window={fill_verdict.get('best_reference_window', '—')}`, `best_reference_exact_bucket_rows={fill_verdict.get('best_reference_exact_bucket_rows', '—')}`, `best_reference_evidence_role={fill_verdict.get('best_reference_evidence_role', '—')}`；reference rows cannot be counted as deployable support unless support identity is deliberately rebaselined and fully reverified.
- Selected next safe artifact: `{fill_verdict.get('selected_next_alternative_artifact', 'data/customer_safe_alternative_proof.json')}`。

### Customer-safe alternative proof

- `data/customer_safe_alternative_proof.json` generated at `{alt.get('generated_at', '—')}`。
- Live gate: `canary_ready={_bool_text(alt_gate.get('canary_ready'))}`, `live_exposure_allowed={_bool_text(alt_gate.get('live_exposure_allowed'))}`, `order_submission_enabled={_bool_text(alt_gate.get('order_submission_enabled'))}`, `risk_on_order_enabled={_bool_text(alt_gate.get('risk_on_order_enabled'))}`, `support_ready={_bool_text(alt_gate.get('support_ready'))}`, `topk_deployable={_bool_text(alt_gate.get('topk_deployable'))}`, `venue_runtime_ready={_bool_text(alt_gate.get('venue_runtime_ready'))}`。
- Allowed today: paper/shadow decision-support, Shadow Trade Ledger, venue dry-run checklist, reduce-only / wait modes. Not allowed: buy/add live exposure, automatic order submission, canary live order without exact support and runtime venue proof.

### Forced-execution / bounded live-canary structural pivot

- `forced-execution` trigger is active when same semantic signature repeats, support `delta_vs_previous=0`, `stagnant_run_count` rises, or the customer flags equilibrium/repetition.
- Forced lanes: **Venue lifecycle proof**, **Model shadow to decision**, **Strategy micro-canary readiness**, **Map-Signal redesign**, or **hard no-go single failed gate**；observation-only status refresh is not accepted.
- Structural pivot reference: `docs/plans/2026-05-23-live-canary-structural-pivot.md` and `data/live_canary_structural_pivot.json`；implementation guard is `execution.live_canary` in `execution/execution_service.py` with tests `tests/test_execution_service.py -k live_canary`.
- bounded live-canary policy is required for any live buy/add pilot: `execution.mode=live`, `enable_live_trading=true`, `execution.live_canary.enabled=true`, explicit `allowed_symbols`, symbol-specific `max_base_qty_by_symbol`, and adapter-pre cap enforcement. Missing policy is `live_canary_policy_required`; over-cap is `live_canary_qty_cap_exceeded`.
- **72h decision clock:** either verify a bounded micro-canary under policy after all live gates pass, or name the single failed gate and next artifact. “Continue observing” is forbidden as fallback.

---

## 3. Customer expectation vs PM answer

客戶想「現在就能用產品」，而不是每小時只收到「等」。PM 把這個需求視為產品風險，但不把它等同於 unsafe live trading。

Customer-usable lanes now:
1. **Dashboard**：看 current-live blocker、breaker release context、4H context、decision quality、feature/source blockers；主阻塞是 `{probe.get('deployment_blocker', '—')}`，support 邊界是 `{current_bucket}` `{rows}/{minimum} gap={gap}`。
2. **Strategy Lab**：看 Top-K / leaderboard 研究候選、OOS ROI、win rate、drawdown、profit factor、worst fold 與 runtime-blocked 原因；`deployable_rows={topk.get('deployable_rows', '—')}` 時只能作 research / paper-shadow evidence。
3. **Execution Console**：使用 paper/shadow selective sleeve、Shadow Trade Ledger、dry-run readiness、等待 / 觀望、減風險；不可做真實買入 / 加倉。
4. **Venue readiness checklist**：追 OKX/Binance 還差哪些 proof；credential 只顯示布林 / proof-state，不洩漏 secret。

---

## 4. framework-capture / alternative-solution / anti-equilibrium guard

本輪維持 **`ORANGE_framework_capture_risk` governance overlay** 與 **`ORANGE_alternative_solution_required`**，不是因為安全 gate 可被推翻，而是避免 PM 被工程 blocker 敘事捕獲。`customer-value delta`：PM status 已承認最新 bucket `{current_bucket}`、exact support `{rows}/{minimum} gap={gap}`、breaker `release_ready={_bool_text(release.get('release_ready'))}` / `{release.get('current_recent_window_wins', '—')}/{release.get('recent_window', '—')}`、Top-K `artifact_freshness_status={topk.get('artifact_freshness_status', '—')}` / `samples={topk.get('samples', '—')}`，並保留 Execution Console / Strategy Lab 的 paper-shadow lane；但 no live exposure。

**time-to-evidence：** `{fill_verdict.get('time_to_evidence_bucket', '—')}` for exact support movement；`same_day` for venue dry-run metadata proof if credentials/config are supplied；`within_week_or_unknown` for true venue lifecycle proof without credentials。PM 不把「治理參考」包裝成 deploy-ready；下輪必須產出 exact-row accumulation proof、missing-capability proof、recent-tail no-new-risk artifact、venue dry-run proof，或一個可驗證的 alternative-solution artifact。

**anti-equilibrium guard：** `anti-repeat` 結果是不能再只重複 support gap；若 same semantic signature + support `delta_vs_previous=0` 再出現，PM 必須轉入 `forced-execution`：Venue lifecycle proof、Model shadow to decision、Strategy micro-canary readiness、Map-Signal redesign、或 hard no-go single failed gate。`cost-of-delay` 是客戶信心、策略可用性與工程焦點繼續被單一路徑消耗；`hypothesis inversion` 是若 exact support 無法累積，最快會由 support stagnation counter、recent drift no-new-risk replay、與 venue dry-run proof 暴露；`option portfolio`：60% 主路徑追 exact support + source/data proof，20% 鄰近安全交付推 paper/shadow decision-support，20% 真替代評估縮小策略/市場範圍、外部資料/工具、manual workflow、替代模型/架構或 stop/pivot；`red-team PM` 挑戰：若下輪沒有客戶可見位移，就要求替代解法 artifact 或 bounded live-canary 72h hard gate，而不是改寫等待文案。

---

## 5. PM challenge to engineering heartbeat

工程 heartbeat 下次不得只輸出「等待更多資料 / gate 未過」。PM 站在客戶側，要求至少交付或驗證下列其中一項：

1. **Exact current support lane**：刷新 live probe / support audit / support-fill feasibility，直接顯示 current exact bucket rows 是否從 `{rows}/{minimum}` 開始 movement，並同時列出 identity rows / non-current-bucket rows，避免把 near-lane/proxy/reference rows 誤包成 deployable；若 `delta_vs_previous=0` 或 `stagnant_run_count` 持續增加，必須說明缺的是 Map / Tool / Signal / Constraint / Review 哪一類能力。
2. **Recent tail root-cause lane**：針對 recent canonical pocket（window `{primary_window}` win_rate `{_pct_text(primary_summary.get('win_rate'))}`）交付一個 no-new-risk / shadow-only falsification artifact；不可把 shadow-only artifact 誤寫成 release patch。
3. **Top-K freshness lane**：維持 `data/high_conviction_topk_oos_matrix.json` 在 freshness target 內，或讓 `/api/models/leaderboard` / Strategy Lab 明確標示 stale/reference-only。
4. **Customer-usable lane**：用 route/API/test/browser proof 證明 `/execution` paper/shadow selective sleeve、Shadow Trade Ledger、range-chop playbook 或 dry-run readiness 可操作。
5. **Venue proof lane**：產出 OKX sandbox/dry-run 或 metadata-to-runtime proof checklist；credential present 只可顯示布林，不可洩漏 secret。
6. **PM drift harness lane**：維持 `scripts/pm_heartbeat_check.py` 以 current runtime artifacts 驗證 `docs/pm/pm-status.md`，避免 stale literals 誤通過。
7. **alternative-solution lane**：至少列三個 alternative-solution，並選一個可於下輪驗證的 artifact；安全 gate 不可放鬆，但產品路線不可被單一路徑綁死。
8. **forced-execution lane**：若 same semantic signature / support delta=0 再重複，必須選 Venue lifecycle proof、Model shadow to decision、Strategy micro-canary readiness、Map-Signal redesign 或 hard no-go single failed gate；任何 live buy/add 都必須先通過 bounded live-canary policy 與 adapter-pre cap enforcement。

---

## 6. Next-hour gate

**Next-hour gate / Success gate：** 下次 PM heartbeat 應能回答：客戶此刻可以打開哪個頁面或模式、做什麼安全操作、看到什麼證據。最低可接受證據是：current exact support rows 從目前 `{rows}/{minimum}` 開始 movement 或明確證明 stagnation 的 missing capability；recent drift no-new-risk / shadow-only falsification artifact clearly labels `deployable=false`；Top-K matrix 保持 fresh；`/execution` paper/shadow 或 dry-run readiness 可操作 proof；venue dry-run proof；或 forced-execution lane 的 72h bounded live-canary / single failed gate artifact。除此之外，PM 必須交付 time-to-evidence bucket 與 `alternative-solution` 候選。

**Fallback：** 若下次仍只有「wait」且沒有 safe deliverable，PM 維持 `ORANGE_framework_capture_risk` 並升級 `ORANGE_alternative_solution_required`；若 same semantic signature + support delta=0 重複卻沒有 forced-execution lane，升級 `RED_forced_execution_required`；若連續三次沒有 artifact movement、safe product proof 或替代解法驗證，升級為 `RED_delivery_deadlock`。
"""
    return _redact(text).rstrip() + "\n"


def sync_pm_status() -> Path:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(build_pm_status_markdown(), encoding="utf-8")
    return STATUS_PATH


def main() -> int:
    path = sync_pm_status()
    print(f"PM status synced: {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
