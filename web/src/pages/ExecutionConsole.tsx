import { useState } from "react";
import { fetchApi, useApi } from "../hooks/useApi";

type SurfaceInfo = {
  route?: string;
  label?: string;
  role?: string;
  status?: string;
  message?: string;
  upgrade_prerequisite?: string;
};

type SleeveRoutingItem = {
  key?: string;
  label?: string;
  why?: string;
};

type SleeveRoutingState = {
  current_regime?: string | null;
  current_regime_gate?: string | null;
  current_structure_bucket?: string | null;
  active_ratio_text?: string | null;
  summary?: string | null;
  active_sleeves?: SleeveRoutingItem[] | null;
  inactive_sleeves?: SleeveRoutingItem[] | null;
};

type LiveRuntimeTruth = {
  runtime_closure_state?: string | null;
  runtime_closure_summary?: string | null;
  regime_label?: string | null;
  regime_gate?: string | null;
  structure_bucket?: string | null;
  allowed_layers?: number | null;
  allowed_layers_raw?: number | null;
  allowed_layers_reason?: string | null;
  allowed_layers_raw_reason?: string | null;
  deployment_blocker?: string | null;
  deployment_blocker_reason?: string | null;
  execution_guardrail_reason?: string | null;
  support_alignment_status?: string | null;
  support_alignment_summary?: string | null;
  support_rows_text?: string | null;
  runtime_exact_support_rows?: number | null;
  calibration_exact_lane_rows?: number | null;
  sleeve_routing?: SleeveRoutingState | null;
};

type ExecutionConsoleRuntimeStatusResponse = {
  symbol?: string;
  timestamp?: string;
  automation?: boolean;
  dry_run?: boolean;
  execution_surface_contract?: {
    canonical_execution_route?: string;
    canonical_surface_label?: string;
    operations_surface?: SurfaceInfo | null;
    diagnostics_surface?: SurfaceInfo | null;
    shortcut_surface?: SurfaceInfo | null;
    readiness_scope?: string;
    live_ready?: boolean;
    live_ready_blockers?: string[];
    operator_message?: string;
    live_runtime_truth?: LiveRuntimeTruth | null;
  } | null;
  execution?: {
    venue?: string;
    mode?: string;
    live_enabled?: boolean;
    kill_switch?: boolean;
    health?: {
      connected?: boolean;
      credentials_configured?: boolean;
      error?: string;
    } | null;
    live_runtime_truth?: LiveRuntimeTruth | null;
    guardrails?: {
      kill_switch?: boolean;
      daily_loss_halt?: boolean;
      failure_halt?: boolean;
      consecutive_failures?: number;
      last_reject?: {
        code?: string;
        message?: string;
        timestamp?: string;
      } | null;
      last_failure?: {
        message?: string;
        timestamp?: string;
      } | null;
      last_order?: {
        venue?: string;
        symbol?: string;
        side?: string;
        qty?: number;
        price?: number | null;
        status?: string;
        order_id?: string | null;
        client_order_id?: string | null;
      } | null;
    } | null;
  } | null;
  account?: {
    captured_at?: string | null;
    degraded?: boolean;
    operator_message?: string | null;
    recovery_hint?: string | null;
    requested_symbol?: string | null;
    normalized_symbol?: string | null;
    position_count?: number;
    open_order_count?: number;
    balance?: {
      free?: number;
      total?: number;
      currency?: string;
    } | null;
    positions?: Array<Record<string, unknown>>;
    open_orders?: Array<Record<string, unknown>>;
  } | null;
  execution_reconciliation?: {
    status?: string;
    summary?: string;
    checked_at?: string;
    issues?: string[];
    recovery_state?: {
      operator_action?: string;
      status?: string;
    } | null;
    lifecycle_audit?: {
      stage?: string;
      runtime_state?: string;
      trade_history_state?: string;
      restart_replay_required?: boolean;
      operator_action?: string;
    } | null;
    lifecycle_contract?: {
      summary?: string;
      replay_verdict?: string;
      artifact_coverage?: string;
      baseline_contract_status?: string;
      venue_lanes_summary?: string;
      venue_lanes?: Array<{
        venue?: string;
        summary?: string;
        operator_action_summary?: string;
        remediation_focus?: string;
        remediation_priority?: string;
        restart_replay_status?: string;
      }>;
    } | null;
  } | null;
  execution_metadata_smoke?: {
    generated_at?: string;
    freshness?: {
      status?: string;
      label?: string;
      age_minutes?: number | null;
    } | null;
    governance?: {
      status?: string;
      operator_message?: string;
      escalation_message?: string | null;
    } | null;
    venues?: Array<{
      venue?: string;
      ok?: boolean;
      enabled_in_config?: boolean;
      credentials_configured?: boolean;
      error?: string | null;
      contract?: {
        step_size?: string | number | null;
        tick_size?: string | number | null;
        min_qty?: number | null;
        min_cost?: number | null;
      } | null;
    }>;
  } | null;
};

type ExecutionStrategyBinding = {
  status?: string | null;
  strategy_name?: string | null;
  strategy_slug?: string | null;
  strategy_source?: string | null;
  strategy_hash?: string | null;
  schema_version?: string | null;
  updated_at?: string | null;
  created_at?: string | null;
  run_count?: number | null;
  primary_sleeve_key?: string | null;
  primary_sleeve_label?: string | null;
  strategy_type?: string | null;
  model_name?: string | null;
  title?: string | null;
  description?: string | null;
  sleeve_summary?: string | null;
  decision_quality_label?: string | null;
  avg_decision_quality_score?: number | null;
  avg_expected_win_rate?: number | null;
  roi?: number | null;
  profit_factor?: number | null;
  total_trades?: number | null;
  summary?: string | null;
  operator_action?: string | null;
};

type ExecutionOverviewProfileCard = {
  key?: string;
  profile_id?: string;
  label?: string;
  summary?: string;
  activation_status?: string;
  lifecycle_status?: string;
  routing_reason?: string;
  planned_budget_amount?: number | null;
  planned_budget_ratio_of_balance?: number | null;
  next_operator_action?: string | null;
  symbol_scoped_position_count?: number;
  symbol_scoped_open_order_count?: number;
  current_run_state?: string | null;
  current_run?: ExecutionRunRecord | null;
  strategy_binding?: ExecutionStrategyBinding | null;
  control_contract?: {
    mode?: string;
    start_status?: string;
    start_reason?: string;
    pause_status?: string;
    stop_status?: string;
    latest_event_type?: string | null;
    latest_event_message?: string | null;
    upgrade_prerequisite?: string;
  } | null;
};

type ExecutionOverviewResponse = {
  controls_mode?: string;
  operator_message?: string;
  upgrade_prerequisite?: string;
  summary?: {
    total_profiles?: number;
    active_profiles?: number;
    blocked_profiles?: number;
    standby_profiles?: number;
    monitoring_profiles?: number;
    running_runs?: number;
    paused_runs?: number;
    stopped_runs?: number;
    total_runs?: number;
    allocation_rule?: string;
    operator_message?: string;
  } | null;
  capital_plan?: {
    deployable_capital?: number | null;
    per_active_profile_budget?: number | null;
    allocation_rule?: string;
    operator_message?: string;
    max_position_ratio?: number | null;
    confidence?: number | null;
  } | null;
  strategy_source_summary?: {
    route?: string | null;
    strategy_count?: number | null;
    covered_sleeves?: number | null;
    total_sleeves?: number | null;
    missing_sleeves?: string[] | null;
    operator_message?: string | null;
  } | null;
  profile_cards?: ExecutionOverviewProfileCard[] | null;
};

type ExecutionRunEvent = {
  event_id?: number;
  run_id?: string;
  profile_id?: string;
  event_type?: string;
  level?: string;
  message?: string;
  created_at?: string;
};

type ExecutionRunBindingContract = {
  status?: string | null;
  scope?: string | null;
  summary?: string | null;
  operator_action?: string | null;
  ownership_boundary?: {
    ledger_scope?: string | null;
    capital_attribution?: string | null;
    position_attribution?: string | null;
    open_order_attribution?: string | null;
    pnl_attribution?: string | null;
    summary?: string | null;
  } | null;
};

type ExecutionRunPreviewRecord = Record<string, unknown>;

type ExecutionRunLedgerPreview = {
  scope?: string | null;
  ownership_status?: string | null;
  summary?: string | null;
  budget_alignment_status?: string | null;
  budget_alignment_summary?: string | null;
  pricing_complete?: boolean | null;
  position_count?: number | null;
  open_order_count?: number | null;
  position_priced_count?: number | null;
  open_order_priced_count?: number | null;
  gross_position_notional?: number | null;
  net_position_notional?: number | null;
  open_order_notional?: number | null;
  total_known_commitment?: number | null;
  unrealized_pnl?: number | null;
  capital_in_use?: number | null;
  budget_amount?: number | null;
  budget_gap?: number | null;
  commitment_vs_budget_ratio?: number | null;
  currency?: string | null;
};

type ExecutionRunBindingSnapshot = {
  account_snapshot?: {
    captured_at?: string | null;
    position_count?: number | null;
    open_order_count?: number | null;
  } | null;
  capital_preview?: {
    allocation_scope?: string | null;
    ownership_status?: string | null;
    budget_amount?: number | null;
    budget_ratio?: number | null;
    balance_total?: number | null;
    balance_free?: number | null;
    currency?: string | null;
    summary?: string | null;
  } | null;
  shared_symbol_preview?: {
    scope?: string | null;
    ownership_status?: string | null;
    ownership_summary?: string | null;
    captured_at?: string | null;
    positions_total_count?: number | null;
    open_orders_total_count?: number | null;
    balance?: {
      total?: number | null;
      free?: number | null;
      currency?: string | null;
    } | null;
    positions?: ExecutionRunPreviewRecord[] | null;
    open_orders?: ExecutionRunPreviewRecord[] | null;
  } | null;
  shared_symbol_ledger_preview?: ExecutionRunLedgerPreview | null;
  reconciliation?: {
    status?: string | null;
    summary?: string | null;
  } | null;
  guardrails?: {
    last_order?: {
      order_id?: string | null;
      status?: string | null;
    } | null;
  } | null;
};

type ExecutionRunRecord = {
  run_id?: string;
  profile_id?: string;
  label?: string;
  state?: string;
  state_label?: string;
  mode?: string;
  control_mode?: string;
  runtime_binding_status?: string;
  budget_amount?: number | null;
  budget_ratio?: number | null;
  capital_currency?: string | null;
  start_time?: string | null;
  stop_time?: string | null;
  stop_reason?: string | null;
  last_event_type?: string | null;
  last_event_message?: string | null;
  last_event_at?: string | null;
  latest_event?: ExecutionRunEvent | null;
  recent_events?: ExecutionRunEvent[] | null;
  strategy_binding?: ExecutionStrategyBinding | null;
  runtime_binding_contract?: ExecutionRunBindingContract | null;
  runtime_binding_snapshot?: ExecutionRunBindingSnapshot | null;
  action_contract?: {
    can_pause?: boolean;
    can_resume?: boolean;
    can_stop?: boolean;
    upgrade_prerequisite?: string;
  } | null;
};

type ExecutionRunsResponse = {
  controls_mode?: string;
  operator_message?: string;
  upgrade_prerequisite?: string;
  summary?: {
    total_profiles?: number;
    active_profiles?: number;
    blocked_profiles?: number;
    standby_profiles?: number;
    running_runs?: number;
    paused_runs?: number;
    stopped_runs?: number;
    total_runs?: number;
  } | null;
  runs?: ExecutionRunRecord[] | null;
};

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function formatPercent(value: number | null | undefined, digits = 1): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

function formatSignedNumber(value: number | null | undefined, digits = 2): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(digits)}`;
}

function formatTime(value?: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("zh-TW");
}

function toMaybeNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function pickPreviewText(record: ExecutionRunPreviewRecord, keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key];
    if (value === null || value === undefined) continue;
    const text = String(value).trim();
    if (text) return text;
  }
  return null;
}

function summarizePreviewRecord(record: ExecutionRunPreviewRecord): string {
  const symbol = pickPreviewText(record, ["symbol", "instId", "market", "pair"]) || "unknown";
  const side = pickPreviewText(record, ["side", "positionSide"]);
  const qty = toMaybeNumber(record.size ?? record.qty ?? record.amount ?? record.contracts ?? record.positionAmt);
  const price = toMaybeNumber(record.price ?? record.entryPrice ?? record.avgPrice ?? record.markPrice);
  const status = pickPreviewText(record, ["status", "state"]);
  return [
    symbol,
    side,
    qty !== null ? `qty ${formatNumber(qty, 4)}` : null,
    price !== null ? `price ${formatNumber(price, 2)}` : null,
    status,
  ].filter(Boolean).join(" · ");
}

function summarizePreviewRecords(records?: ExecutionRunPreviewRecord[] | null): string {
  if (!Array.isArray(records) || records.length === 0) return "none";
  return records.map((record) => summarizePreviewRecord(record)).join(" ｜ ");
}

function getStatusTone(status?: string | null): string {
  const normalized = String(status || "").toLowerCase();
  if (["ok", "healthy", "aligned", "fresh", "running", "connected"].some((item) => normalized.includes(item))) {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
  }
  if (["stale", "warning", "degraded", "attention", "beta", "operator", "replay"].some((item) => normalized.includes(item))) {
    return "border-amber-500/30 bg-amber-500/10 text-amber-100";
  }
  if (["fail", "error", "blocked", "halt", "missing", "not"].some((item) => normalized.includes(item))) {
    return "border-rose-500/30 bg-rose-500/10 text-rose-100";
  }
  return "border-cyan-500/30 bg-cyan-500/10 text-cyan-100";
}

function humanizeExecutionReason(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "尚未提供 blocker 摘要。";
  const lower = normalized.toLowerCase();
  const mappings: Array<[string, string]> = [
    ["live exchange credential", "交易所憑證尚未驗證。"],
    ["order ack lifecycle", "委託確認流程尚未驗證。"],
    ["fill lifecycle", "成交回補流程尚未驗證。"],
    ["unsupported_exact_live_structure_bucket", "目前結構 bucket 尚未通過可部署條件。"],
    ["decision_quality_below_trade_floor", "目前決策品質不足，暫不建議進場。"],
    ["circuit_breaker_active", "目前觸發保護機制，暫停部署。"],
    ["patch_inactive_or_blocked", "目前 q15 patch 尚未啟用，或仍被其他條件阻擋。"],
    ["unsupported", "目前條件尚未通過可部署檢查。"],
  ];
  for (const [token, message] of mappings) {
    if (lower.includes(token)) return message;
  }
  return normalized.replace(/[_|]+/g, " ").trim();
}

function readRecordString(record: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function readRecordNumber(record: Record<string, unknown>, keys: string[]): number | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return null;
}

function getValueTone(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value) || value === 0) return "text-white";
  return value > 0 ? "text-emerald-300" : "text-rose-300";
}

export default function ExecutionConsole() {
  const { data: runtimeStatus, loading, error, refresh: refreshRuntimeStatus } = useApi<ExecutionConsoleRuntimeStatusResponse>("/api/status", 60000);
  const { data: executionOverview, loading: overviewLoading, error: overviewError, refresh: refreshExecutionOverview } = useApi<ExecutionOverviewResponse>("/api/execution/overview", 60000);
  const { data: executionRuns, loading: runsLoading, error: runsError, refresh: refreshExecutionRuns } = useApi<ExecutionRunsResponse>("/api/execution/runs", 60000);
  const [runActionState, setRunActionState] = useState<{ tone: "idle" | "pending" | "success" | "error"; message: string }>({
    tone: "idle",
    message: "",
  });
  const [operatorActionState, setOperatorActionState] = useState<{ tone: "idle" | "pending" | "success" | "error"; message: string }>({
    tone: "idle",
    message: "",
  });

  const handleRunAction = async (endpoint: string, pendingLabel: string, successLabel: string) => {
    setRunActionState({ tone: "pending", message: pendingLabel });
    try {
      const resp = await fetchApi<{ operator_message?: string }>(endpoint, { method: "POST" });
      await Promise.all([refreshExecutionRuns(), refreshExecutionOverview(), refreshRuntimeStatus()]);
      setRunActionState({ tone: "success", message: resp.operator_message || successLabel });
    } catch (err: any) {
      setRunActionState({ tone: "error", message: err?.message || "execution run 操作失敗" });
    }
  };

  const executionSurfaceContract = runtimeStatus?.execution_surface_contract ?? null;
  const operationsSurface = executionSurfaceContract?.operations_surface ?? null;
  const diagnosticsSurface = executionSurfaceContract?.diagnostics_surface ?? null;
  const liveRuntimeTruth = runtimeStatus?.execution?.live_runtime_truth ?? executionSurfaceContract?.live_runtime_truth ?? null;
  const liveRouting = liveRuntimeTruth?.sleeve_routing ?? null;
  const liveActiveSleeves = Array.isArray(liveRouting?.active_sleeves) ? liveRouting.active_sleeves : [];
  const liveInactiveSleeves = Array.isArray(liveRouting?.inactive_sleeves) ? liveRouting.inactive_sleeves : [];
  const executionSummary = runtimeStatus?.execution ?? null;
  const guardrails = executionSummary?.guardrails ?? null;
  const accountSummary = runtimeStatus?.account ?? null;
  const executionReconciliation = runtimeStatus?.execution_reconciliation ?? null;
  const lifecycleAudit = executionReconciliation?.lifecycle_audit ?? null;
  const lifecycleContract = executionReconciliation?.lifecycle_contract ?? null;
  const venueLanes = Array.isArray(lifecycleContract?.venue_lanes) ? lifecycleContract.venue_lanes : [];
  const metadataSmoke = runtimeStatus?.execution_metadata_smoke ?? null;
  const metadataSmokeFreshness = metadataSmoke?.freshness ?? null;
  const metadataSmokeGovernance = metadataSmoke?.governance ?? null;

  const positions = Array.isArray(accountSummary?.positions) ? accountSummary.positions : [];
  const openOrders = Array.isArray(accountSummary?.open_orders) ? accountSummary.open_orders : [];
  const balanceCurrency = accountSummary?.balance?.currency || "USDT";
  const balanceFree = typeof accountSummary?.balance?.free === "number" ? accountSummary.balance.free : null;
  const balanceTotal = typeof accountSummary?.balance?.total === "number" ? accountSummary.balance.total : null;
  const allocatedCapital = balanceTotal != null && balanceFree != null ? Math.max(balanceTotal - balanceFree, 0) : null;
  const lastOrder = guardrails?.last_order ?? null;
  const lastReject = guardrails?.last_reject ?? null;
  const lastFailure = guardrails?.last_failure ?? null;
  const liveReadyBlockers = Array.isArray(executionSurfaceContract?.live_ready_blockers) ? executionSurfaceContract.live_ready_blockers : [];
  const venueChecks = Array.isArray(metadataSmoke?.venues) ? metadataSmoke.venues : [];
  const executionOverviewSummary = executionOverview?.summary ?? null;
  const executionCapitalPlan = executionOverview?.capital_plan ?? null;
  const executionStrategySummary = executionOverview?.strategy_source_summary ?? null;
  const executionProfileCards = Array.isArray(executionOverview?.profile_cards) ? executionOverview.profile_cards : [];
  const executionRunsSummary = executionRuns?.summary ?? null;
  const executionRunRecords = Array.isArray(executionRuns?.runs) ? executionRuns.runs : [];
  const runsByProfileId = new Map(executionRunRecords.map((run) => [run.profile_id || "", run]));
  const runLedgerPreviews = executionRunRecords
    .map((run) => run.runtime_binding_snapshot?.shared_symbol_ledger_preview ?? null)
    .filter((item): item is ExecutionRunLedgerPreview => Boolean(item));
  const totalUnrealizedPnl = runLedgerPreviews.reduce((sum, item) => sum + (typeof item.unrealized_pnl === "number" ? item.unrealized_pnl : 0), 0);
  const totalCapitalInUse = runLedgerPreviews.reduce((sum, item) => sum + (typeof item.capital_in_use === "number" ? item.capital_in_use : 0), 0);
  const profitableRuns = executionRunRecords.filter((run) => (run.runtime_binding_snapshot?.shared_symbol_ledger_preview?.unrealized_pnl ?? 0) > 0).length;
  const deployableCapital = executionCapitalPlan?.deployable_capital ?? balanceFree;
  const hasBlockedState = !executionSurfaceContract?.live_ready;
  const rawPrimaryBlockedReason = liveRuntimeTruth?.deployment_blocker_reason
    || liveRuntimeTruth?.deployment_blocker
    || liveRuntimeTruth?.execution_guardrail_reason
    || liveReadyBlockers[0]
    || executionSurfaceContract?.operator_message
    || null;
  const primaryBlockedReason = humanizeExecutionReason(rawPrimaryBlockedReason);
  const blockedReasonSummary = Array.from(new Set([
    rawPrimaryBlockedReason,
    ...liveReadyBlockers,
  ]
    .map((item) => humanizeExecutionReason(item))
    .filter((item) => item && item !== "尚未提供 blocker 摘要。")))
    .join(" · ") || primaryBlockedReason;
  const deploymentStatusLabel = executionSurfaceContract?.live_ready ? "Ready" : "Blocked";
  const deploymentStatusDetail = executionSurfaceContract?.live_ready
    ? (liveRuntimeTruth?.runtime_closure_summary || executionSurfaceContract?.operator_message || "目前已滿足主要部署條件。")
    : (liveRuntimeTruth?.runtime_closure_summary || liveRuntimeTruth?.deployment_blocker_reason || primaryBlockedReason);
  const automationEnabled = Boolean(runtimeStatus?.automation);
  const dryRunEnabled = Boolean(runtimeStatus?.dry_run);
  const executionSymbol = runtimeStatus?.symbol || "BTCUSDT";
  const executionModeLabel = executionSummary?.mode || (dryRunEnabled ? "dry_run" : "paper");
  const executionVenueLabel = executionSummary?.venue || "unknown";
  const runActionTone = runActionState.tone === "success"
    ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-100"
    : runActionState.tone === "error"
      ? "border-rose-500/20 bg-rose-500/10 text-rose-100"
      : "border-cyan-500/20 bg-cyan-500/10 text-cyan-100";
  const operatorActionTone = operatorActionState.tone === "success"
    ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-100"
    : operatorActionState.tone === "error"
      ? "border-rose-500/20 bg-rose-500/10 text-rose-100"
      : "border-cyan-500/20 bg-cyan-500/10 text-cyan-100";

  const handleOperatorTrade = async (side: "buy" | "reduce") => {
    const label = side === "buy" ? "買入" : "減碼";
    setOperatorActionState({
      tone: "pending",
      message: `${label} 指令送出中… ${executionSymbol} 會送到 /api/trade，完成後自動刷新 runtime。`,
    });
    try {
      const resp = await fetchApi<any>("/api/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ side, symbol: executionSymbol, qty: 0.001 }),
      });
      await refreshRuntimeStatus();
      const order = resp?.order ?? null;
      const normalization = resp?.normalization ?? null;
      const normalizedQty = typeof normalization?.normalized?.qty === "number" ? normalization.normalized.qty : (typeof order?.qty === "number" ? order.qty : null);
      const normalizedPrice = typeof normalization?.normalized?.price === "number" ? normalization.normalized.price : null;
      const stepSize = normalization?.contract?.step_size;
      const tickSize = normalization?.contract?.tick_size;
      const contractSummary = [
        stepSize != null ? `step ${formatNumber(Number(stepSize), 6)}` : null,
        tickSize != null ? `tick ${formatNumber(Number(tickSize), 6)}` : null,
      ].filter(Boolean).join(" · ");
      setOperatorActionState({
        tone: "success",
        message: `${label} 已提交：模式 ${order?.mode || (resp?.dry_run ? "dry_run" : executionModeLabel)} · venue ${resp?.venue || executionVenueLabel}${normalizedQty != null ? ` · normalized qty ${formatNumber(normalizedQty, 6)}` : ""}${normalizedPrice != null ? ` · normalized price ${formatNumber(normalizedPrice, 2)}` : ""}${contractSummary ? ` · contract ${contractSummary}` : ""}`,
      });
    } catch (err: any) {
      await refreshRuntimeStatus();
      setOperatorActionState({
        tone: "error",
        message: `${label} 指令失敗：${err?.message || "未知錯誤"}`,
      });
    }
  };

  const handleAutomationToggle = async (enabled: boolean) => {
    setOperatorActionState({
      tone: "pending",
      message: `${enabled ? "切換至自動" : "切換至手動"}模式中…`,
    });
    try {
      const resp = await fetchApi<{ automation?: boolean; message?: string }>("/api/automation/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      await refreshRuntimeStatus();
      setOperatorActionState({
        tone: "success",
        message: resp.message || `目前已是${resp.automation ? "自動" : "手動"}模式`,
      });
    } catch (err: any) {
      await refreshRuntimeStatus();
      setOperatorActionState({
        tone: "error",
        message: `automation 切換失敗：${err?.message || "未知錯誤"}`,
      });
    }
  };

  return (
    <div className="app-page-shell text-white">
      <section className="app-page-header exchange-panel">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div className="inline-flex items-center rounded-full border border-[#7132f5]/30 bg-[#7132f5]/15 px-3 py-1 text-[11px] font-semibold tracking-[0.2em] text-[#d6c9ff]">
              Bot 營運 / Live Ops
            </div>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">先看我的 Bot、資金使用與盈虧預覽</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
              主頁只放營運關鍵：Bot 狀態、資金、盈虧；診斷與恢復集中到「執行狀態」。
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-300">
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">{executionModeLabel.toUpperCase()}</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">{executionVenueLabel}</span>
              <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(automationEnabled ? "ok" : "warning")}`}>
                automation {automationEnabled ? "ON" : "OFF"}
              </span>
              <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(executionSurfaceContract?.live_ready ? "ok" : "blocked")}`}>
                {executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞"}
              </span>
              <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(metadataSmokeFreshness?.status)}`}>
                freshness {metadataSmokeFreshness?.label || metadataSmokeFreshness?.status || "unavailable"}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-sm">
            <button
              type="button"
              onClick={() => Promise.all([refreshRuntimeStatus(), refreshExecutionOverview(), refreshExecutionRuns()])}
              className="rounded-xl border border-[#7132f5]/35 bg-[#7132f5] px-4 py-2 font-medium text-white transition hover:bg-[#5f28d8]"
            >
              重新整理
            </button>
            <a href="/lab" className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 font-medium text-slate-100 transition hover:border-[#7132f5]/35 hover:text-white">
              選策略
            </a>
            <a href="/execution/status" className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 font-medium text-slate-100 transition hover:border-[#7132f5]/35 hover:text-white">
              執行狀態
            </a>
          </div>
        </div>
        {executionSurfaceContract?.operator_message && !hasBlockedState && (
          <div className="mt-4 rounded-2xl border border-white/8 bg-white/5 px-4 py-3 text-sm text-slate-200">
            {executionSurfaceContract.operator_message}
          </div>
        )}
        {(loading || error) && (
          <div className="mt-4 rounded-2xl border border-white/8 bg-[#0d1324] px-4 py-3 text-sm text-slate-300">
            {loading ? "/api/status 載入中…" : `載入失敗：${error}`}
          </div>
        )}
        {runActionState.tone !== "idle" && runActionState.message && (
          <div className={`mt-4 rounded-2xl border px-4 py-3 text-sm ${runActionTone}`}>
            {runActionState.message}
          </div>
        )}
        {hasBlockedState && (
          <div className="mt-4 rounded-[24px] border border-amber-400/30 bg-[linear-gradient(135deg,rgba(245,158,11,0.18),rgba(113,50,245,0.14))] p-4 shadow-[0_18px_40px_rgba(245,158,11,0.12)]">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-200/80">blocked</div>
                <div className="mt-2 text-lg font-semibold text-amber-50">先解除 blocker，再做操作</div>
                <div className="mt-1 text-sm text-amber-100/90">{primaryBlockedReason}</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <a href="/execution/status" className="rounded-xl bg-amber-300 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-amber-200">
                  查看阻塞原因
                </a>
                <button
                  type="button"
                  onClick={() => Promise.all([refreshRuntimeStatus(), refreshExecutionOverview(), refreshExecutionRuns()])}
                  className="rounded-xl border border-white/15 bg-white/8 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/12"
                >
                  重新整理
                </button>
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <div className="rounded-[20px] border border-white/6 bg-[#151b31] p-4">
          <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">資產總覽</div>
          <div className="mt-2 text-3xl font-semibold text-white">{formatNumber(balanceTotal)} {balanceCurrency}</div>
          <div className="mt-2 text-sm text-slate-400">可用 {formatNumber(balanceFree)} · 已分配 {formatNumber(allocatedCapital)}</div>
        </div>
        <div className="rounded-[20px] border border-white/6 bg-[#151b31] p-4">
          <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">共享盈虧預覽</div>
          <div className={`mt-2 text-3xl font-semibold ${totalUnrealizedPnl > 0 ? "text-emerald-300" : totalUnrealizedPnl < 0 ? "text-rose-300" : "text-white"}`}>
            {formatSignedNumber(runLedgerPreviews.length > 0 ? totalUnrealizedPnl : null)} {balanceCurrency}
          </div>
          <div className="mt-2 text-sm text-slate-400">{runLedgerPreviews.length > 0 ? `共享帳戶預覽 · ${executionRunRecords.length} 個 run` : "尚未取得共享盈虧預覽"}</div>
        </div>
        <div className="rounded-[20px] border border-white/6 bg-[#151b31] p-4">
          <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">資金使用中</div>
          <div className="mt-2 text-3xl font-semibold text-white">{formatNumber(runLedgerPreviews.length > 0 ? totalCapitalInUse : allocatedCapital)} {balanceCurrency}</div>
          <div className="mt-2 text-sm text-slate-400">{runLedgerPreviews.length > 0 ? "依目前 run ledger preview 匯總" : "暫以帳戶已分配資金表示"}</div>
        </div>
        <div className="rounded-[20px] border border-white/6 bg-[#151b31] p-4">
          <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">可部署資金</div>
          <div className="mt-2 text-3xl font-semibold text-white">{formatNumber(deployableCapital)} {balanceCurrency}</div>
          <div className="mt-2 text-sm text-slate-400">allocation {executionCapitalPlan?.allocation_rule || executionOverviewSummary?.allocation_rule || "equal_split_active_sleeves"}</div>
        </div>
        <div className="rounded-[20px] border border-white/6 bg-[#151b31] p-4">
          <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">運行中 Bot</div>
          <div className="mt-2 text-3xl font-semibold text-white">{executionRunsSummary?.running_runs ?? 0}</div>
          <div className="mt-2 text-sm text-slate-400">獲利中 {profitableRuns} · paused {executionRunsSummary?.paused_runs ?? 0} · total {executionRunsSummary?.total_runs ?? executionRunRecords.length}</div>
        </div>
        <div className="rounded-[20px] border border-white/6 bg-[#151b31] p-4">
          <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">部署狀態</div>
          <div className="mt-2 text-3xl font-semibold text-white">{deploymentStatusLabel}</div>
          <div className="mt-2 text-sm text-slate-400">{deploymentStatusDetail}</div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.55fr_0.95fr]">
        <div className="space-y-4">
          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">我的 Bot</div>
                <div className="mt-1 text-sm text-slate-400">
                  已建立 Bot 的盈利能力與共享帳戶預覽。
                </div>
              </div>
              <div className="text-right text-xs text-slate-400">
                <div>策略來源 {executionStrategySummary?.strategy_count ?? 0}</div>
                <div>資金規則 {executionCapitalPlan?.allocation_rule || executionOverviewSummary?.allocation_rule || "equal_split_active_sleeves"}</div>
              </div>
            </div>
            {(overviewLoading || overviewError) && (
              <div className="mt-3 rounded-2xl border border-white/8 bg-[#0d1324] px-4 py-3 text-sm text-slate-300">
                {overviewLoading ? "/api/execution/overview 載入中…" : `execution overview 載入失敗：${overviewError}`}
              </div>
            )}
            {executionOverview?.operator_message && (
              <div className="mt-3 text-sm text-slate-300">{executionOverview.operator_message}</div>
            )}
            <div className="mt-2 text-xs text-slate-400">
              saved strategies {executionStrategySummary?.strategy_count ?? 0} · covered sleeves {executionStrategySummary?.covered_sleeves ?? 0}/{executionStrategySummary?.total_sleeves ?? 0} · missing {(executionStrategySummary?.missing_sleeves || []).join(" / ") || "none"}
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {executionProfileCards.length > 0 ? executionProfileCards.map((card) => {
                const profileId = card.profile_id || card.key || "";
                const linkedRun = runsByProfileId.get(profileId) || card.current_run || null;
                const profileStrategyBinding = card.strategy_binding ?? null;
                const ledgerPreview = linkedRun?.runtime_binding_snapshot?.shared_symbol_ledger_preview ?? null;
                const canStart = Boolean(profileId) && ["ready_control_plane", "resume_available"].includes(card.control_contract?.start_status || "");
                const canPause = Boolean(linkedRun?.action_contract?.can_pause && linkedRun?.run_id);
                const canStop = Boolean(linkedRun?.action_contract?.can_stop && linkedRun?.run_id);
                return (
                  <div key={card.key || card.label} className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-base font-semibold text-white">{card.label || card.key || "unknown sleeve"}</div>
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                          <span className="rounded-full border border-[#7132f5]/25 bg-[#7132f5]/12 px-2.5 py-1 text-[#d8cbff]">
                            {profileStrategyBinding?.primary_sleeve_label || card.strategy_binding?.title || "未分類"}
                          </span>
                          <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(linkedRun?.state || card.lifecycle_status || card.activation_status)}`}>
                            {linkedRun?.state_label || linkedRun?.state || card.lifecycle_status || card.activation_status || "unknown"}
                          </span>
                          {ledgerPreview && (
                            <span className="rounded-full border border-cyan-500/25 bg-cyan-500/10 px-2.5 py-1 text-cyan-100">
                              共享預覽
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-right text-[11px] text-slate-500">
                        <div>{card.profile_id || card.key || "—"}</div>
                        <div>{linkedRun?.last_event_type || card.control_contract?.latest_event_type || "no event"}</div>
                      </div>
                    </div>

                    <div className="mt-3 text-sm text-slate-300">{card.summary || profileStrategyBinding?.summary || card.routing_reason || "尚未提供策略摘要"}</div>

                    <div className="mt-4 grid grid-cols-2 gap-2 xl:grid-cols-3">
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">策略 ROI</div>
                        <div className={`mt-1 text-sm font-semibold ${((profileStrategyBinding?.roi ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300")}`}>
                          {formatPercent(profileStrategyBinding?.roi, 1)}
                        </div>
                        <div className="text-[11px] text-slate-400">PF {formatNumber(profileStrategyBinding?.profit_factor, 2)}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">共享盈虧預覽</div>
                        <div className={`mt-1 text-sm font-semibold ${(ledgerPreview?.unrealized_pnl ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                          {formatSignedNumber(ledgerPreview?.unrealized_pnl)} {ledgerPreview?.currency || balanceCurrency}
                        </div>
                        <div className="text-[11px] text-slate-400">資金使用中 {formatNumber(ledgerPreview?.capital_in_use)} {ledgerPreview?.currency || balanceCurrency}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">預算 / 勝率</div>
                        <div className="mt-1 text-sm font-semibold text-white">{formatNumber(card.planned_budget_amount)} {balanceCurrency}</div>
                        <div className="text-[11px] text-slate-400">win {formatPercent(profileStrategyBinding?.avg_expected_win_rate, 1)}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">DQ</div>
                        <div className="mt-1 text-sm font-semibold text-white">{formatNumber(profileStrategyBinding?.avg_decision_quality_score, 3)}</div>
                        <div className="text-[11px] text-slate-400">trades {profileStrategyBinding?.total_trades ?? "—"}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">倉位 / 掛單</div>
                        <div className="mt-1 text-sm font-semibold text-white">{card.symbol_scoped_position_count ?? 0} / {card.symbol_scoped_open_order_count ?? 0}</div>
                        <div className="text-[11px] text-slate-400">{linkedRun?.state_label || linkedRun?.state || "not-started"}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">下一步</div>
                        <div className="mt-1 text-sm font-semibold text-white">{card.control_contract?.start_status || "—"}</div>
                        <div className="text-[11px] text-slate-400">{linkedRun?.latest_event?.event_type || linkedRun?.last_event_type || "waiting"}</div>
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-slate-400">
                      <span>routing {card.routing_reason || "—"}</span>
                      <span>start {card.control_contract?.start_reason || "—"}</span>
                      <span>預覽 {ledgerPreview?.budget_alignment_status || ledgerPreview?.ownership_status || "unavailable"}</span>
                      <span>event {linkedRun?.latest_event?.message || linkedRun?.last_event_message || card.control_contract?.latest_event_message || "尚未建立 run event"}</span>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2 text-sm">
                      <button
                        type="button"
                        disabled={!canStart || runActionState.tone === "pending"}
                        onClick={() => handleRunAction(`/api/execution/runs/${profileId}/start`, "建立 run 中…", card.control_contract?.start_status === "resume_available" ? "已恢復 execution run。" : "已建立 execution run。")}
                        className="rounded-xl border border-emerald-500/30 bg-emerald-500/12 px-3 py-2 font-medium text-emerald-100 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        啟動 / 恢復
                      </button>
                      <button
                        type="button"
                        disabled={!canPause || runActionState.tone === "pending"}
                        onClick={() => linkedRun?.run_id && handleRunAction(`/api/execution/runs/${linkedRun.run_id}/pause`, "暫停 run 中…", "已暫停 execution run。")}
                        className="rounded-xl border border-amber-500/30 bg-amber-500/12 px-3 py-2 font-medium text-amber-100 transition hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        暫停
                      </button>
                      <button
                        type="button"
                        disabled={!canStop || runActionState.tone === "pending"}
                        onClick={() => linkedRun?.run_id && handleRunAction(`/api/execution/runs/${linkedRun.run_id}/stop`, "停止 run 中…", "已停止 execution run。")}
                        className="rounded-xl border border-rose-500/30 bg-rose-500/12 px-3 py-2 font-medium text-rose-100 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        停止
                      </button>
                    </div>
                  </div>
                );
              }) : (
                <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-5 text-sm text-slate-300">
                  尚未取得 bot profile cards；先確認 /api/execution/overview 是否可用。
                </div>
              )}
            </div>
          </section>

          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">運行中</div>
                <div className="mt-1 text-sm text-slate-400">
                  running {executionRunsSummary?.running_runs ?? 0} · paused {executionRunsSummary?.paused_runs ?? 0} · stopped {executionRunsSummary?.stopped_runs ?? 0} · total {executionRunsSummary?.total_runs ?? executionRunRecords.length}
                </div>
              </div>
              <div className="text-xs text-slate-400">run control beta</div>
            </div>
            {(runsLoading || runsError) && (
              <div className="mt-3 rounded-2xl border border-white/8 bg-[#0d1324] px-4 py-3 text-sm text-slate-300">
                {runsLoading ? "/api/execution/runs 載入中…" : `execution runs 載入失敗：${runsError}`}
              </div>
            )}
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {executionRunRecords.length > 0 ? executionRunRecords.slice(0, 6).map((run) => {
                const runStrategyBinding = run.strategy_binding ?? null;
                const latestMessage = run.latest_event?.message || run.last_event_message || "尚未取得 run event";
                const ledgerPreview = run.runtime_binding_snapshot?.shared_symbol_ledger_preview ?? null;
                return (
                  <div key={run.run_id || `${run.profile_id}-${run.start_time}`} className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-base font-semibold text-white">{run.label || run.profile_id || "unknown run"}</div>
                        <div className="mt-1 text-[12px] text-slate-400">profile {run.profile_id || "—"} · {run.mode || "paper"}</div>
                      </div>
                      <div className={`rounded-full border px-2.5 py-1 text-[11px] ${getStatusTone(run.state || "unknown")}`}>
                        {run.state_label || run.state || "unknown"}
                      </div>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-[12px] xl:grid-cols-4">
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">預算</div>
                        <div className="mt-1 font-semibold text-white">{formatNumber(run.budget_amount)} {run.capital_currency || balanceCurrency}</div>
                        <div className="text-slate-400">ratio {formatNumber(run.budget_ratio, 3)}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">共享盈虧預覽</div>
                        <div className={`mt-1 font-semibold ${(ledgerPreview?.unrealized_pnl ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{formatSignedNumber(ledgerPreview?.unrealized_pnl)} {ledgerPreview?.currency || balanceCurrency}</div>
                        <div className="text-slate-400">資金使用中 {formatNumber(ledgerPreview?.capital_in_use)} {ledgerPreview?.currency || balanceCurrency}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">策略能力</div>
                        <div className={`mt-1 font-semibold ${(runStrategyBinding?.roi ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{formatPercent(runStrategyBinding?.roi, 1)}</div>
                        <div className="text-slate-400">PF {formatNumber(runStrategyBinding?.profit_factor, 2)} · win {formatPercent(runStrategyBinding?.avg_expected_win_rate, 1)}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">最近事件</div>
                        <div className="mt-1 font-semibold text-white">{run.latest_event?.event_type || run.last_event_type || "—"}</div>
                        <div className="text-slate-400">{formatTime(run.last_event_at)}</div>
                      </div>
                    </div>
                    <div className="mt-3 text-sm text-slate-300">{runStrategyBinding?.summary || latestMessage}</div>
                    <div className="mt-2 text-[12px] text-slate-400">共享預覽 {ledgerPreview?.budget_alignment_summary || ledgerPreview?.summary || "尚未提供共享帳戶預覽。"}</div>
                    <div className="mt-3 flex flex-wrap gap-2 text-sm">
                      <button
                        type="button"
                        disabled={!run.action_contract?.can_resume || !run.profile_id || runActionState.tone === "pending"}
                        onClick={() => run.profile_id && handleRunAction(`/api/execution/runs/${run.profile_id}/start`, "恢復 run 中…", "已恢復 execution run。")}
                        className="rounded-xl border border-emerald-500/30 bg-emerald-500/12 px-3 py-2 font-medium text-emerald-100 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        恢復
                      </button>
                      <button
                        type="button"
                        disabled={!run.action_contract?.can_pause || !run.run_id || runActionState.tone === "pending"}
                        onClick={() => run.run_id && handleRunAction(`/api/execution/runs/${run.run_id}/pause`, "暫停 run 中…", "已暫停 execution run。")}
                        className="rounded-xl border border-amber-500/30 bg-amber-500/12 px-3 py-2 font-medium text-amber-100 transition hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        暫停
                      </button>
                      <button
                        type="button"
                        disabled={!run.action_contract?.can_stop || !run.run_id || runActionState.tone === "pending"}
                        onClick={() => run.run_id && handleRunAction(`/api/execution/runs/${run.run_id}/stop`, "停止 run 中…", "已停止 execution run。")}
                        className="rounded-xl border border-rose-500/30 bg-rose-500/12 px-3 py-2 font-medium text-rose-100 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        停止
                      </button>
                    </div>
                  </div>
                );
              }) : (
                <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-5 text-sm text-slate-300">
                  尚未建立 stateful run；先在上方 Bot 卡啟動，這裡才會出現事件與狀態。
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="space-y-4">
          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">應急手動操作</div>
                <div className="mt-1 text-sm text-slate-400">{executionSymbol} · {executionModeLabel} · {executionVenueLabel}</div>
              </div>
              <div className={`rounded-full border px-2.5 py-1 text-[11px] ${getStatusTone(automationEnabled ? "ok" : "warning")}`}>
                automation {automationEnabled ? "ON" : "OFF"}
              </div>
            </div>
            <div className="mt-2 text-[12px] text-slate-400">僅供人工介入，不是 Bot 營運的主流程。</div>
            <div className="mt-4 grid gap-2 sm:grid-cols-3">
              <button
                type="button"
                disabled={operatorActionState.tone === "pending"}
                onClick={() => handleOperatorTrade("buy")}
                className="rounded-xl border border-emerald-500/30 bg-emerald-500/12 px-3 py-3 text-sm font-medium text-emerald-100 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-40"
              >
                買入 0.001 BTC
              </button>
              <button
                type="button"
                disabled={operatorActionState.tone === "pending"}
                onClick={() => handleOperatorTrade("reduce")}
                className="rounded-xl border border-amber-500/30 bg-amber-500/12 px-3 py-3 text-sm font-medium text-amber-100 transition hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-40"
              >
                減碼 0.001 BTC
              </button>
              <button
                type="button"
                disabled={operatorActionState.tone === "pending"}
                onClick={() => handleAutomationToggle(!automationEnabled)}
                className="rounded-xl border border-[#7132f5]/35 bg-[#7132f5]/15 px-3 py-3 text-sm font-medium text-[#e4dbff] transition hover:bg-[#7132f5]/25 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {automationEnabled ? "切到手動模式" : "切到自動模式"}
              </button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-300">
              <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(guardrails?.kill_switch ? "blocked" : "ok")}`}>kill switch {guardrails?.kill_switch ? "ON" : "off"}</span>
              <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(guardrails?.failure_halt ? "warning" : "ok")}`}>failure halt {guardrails?.failure_halt ? "ON" : "off"}</span>
              <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(guardrails?.daily_loss_halt ? "warning" : "ok")}`}>daily halt {guardrails?.daily_loss_halt ? "ON" : "off"}</span>
            </div>
            {operatorActionState.tone !== "idle" && operatorActionState.message && (
              <div className={`mt-3 rounded-2xl border px-3 py-2 text-sm ${operatorActionTone}`}>
                {operatorActionState.message}
              </div>
            )}
          </section>

          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">部署狀態</div>
                <div className="mt-1 text-sm text-slate-400">{liveRouting?.current_regime || liveRuntimeTruth?.regime_label || "—"} · gate {liveRouting?.current_regime_gate || liveRuntimeTruth?.regime_gate || "—"} · bucket {liveRouting?.current_structure_bucket || liveRuntimeTruth?.structure_bucket || "—"}</div>
              </div>
              <div className={`rounded-full border px-2.5 py-1 text-[11px] ${getStatusTone(executionSurfaceContract?.live_ready ? "ok" : "blocked")}`}>
                {executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞"}
              </div>
            </div>
            <div className="mt-3 text-sm text-slate-300">{deploymentStatusDetail}</div>
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">Layers</div>
                <div className="mt-1 font-semibold text-white">{liveRuntimeTruth?.allowed_layers_raw ?? "—"} → {liveRuntimeTruth?.allowed_layers ?? "—"}</div>
                <div className="text-[11px] text-slate-400">{liveRuntimeTruth?.allowed_layers_reason || liveRuntimeTruth?.allowed_layers_raw_reason || "—"}</div>
              </div>
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">Support</div>
                <div className="mt-1 font-semibold text-white">{liveRuntimeTruth?.support_rows_text || `${liveRuntimeTruth?.runtime_exact_support_rows ?? "—"} / ${liveRuntimeTruth?.calibration_exact_lane_rows ?? "—"}`}</div>
                <div className="text-[11px] text-slate-400">{liveRuntimeTruth?.support_alignment_status || "unavailable"}</div>
              </div>
            </div>
            {liveReadyBlockers.length > 0 && (
              <div className="mt-3 rounded-2xl border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
                {blockedReasonSummary}
              </div>
            )}
            <div className="mt-4 space-y-3">
              <div>
                <div className="text-[11px] uppercase tracking-wide text-slate-500">Active sleeves</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {liveActiveSleeves.length > 0 ? liveActiveSleeves.map((item) => (
                    <span key={item.key || item.label} title={item.why || undefined} className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1 text-[11px] text-emerald-100">
                      {item.label || item.key}
                    </span>
                  )) : <span className="text-sm text-slate-400">目前沒有 active sleeves</span>}
                </div>
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-wide text-slate-500">Inactive sleeves</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {liveInactiveSleeves.length > 0 ? liveInactiveSleeves.map((item) => (
                    <span key={item.key || item.label} title={item.why || undefined} className="rounded-full border border-rose-500/25 bg-rose-500/10 px-2.5 py-1 text-[11px] text-rose-100">
                      {item.label || item.key}
                    </span>
                  )) : <span className="text-sm text-slate-400">目前沒有 inactive sleeves</span>}
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">帳戶與成交</div>
                <div className="mt-1 text-sm text-slate-400">captured {formatTime(accountSummary?.captured_at)}</div>
              </div>
              <div className="text-xs text-slate-400">{accountSummary?.requested_symbol || "—"} → {accountSummary?.normalized_symbol || "—"}</div>
            </div>
            {(accountSummary?.operator_message || accountSummary?.recovery_hint || accountSummary?.degraded) && (
              <div className="mt-3 rounded-2xl border border-white/8 bg-white/5 px-3 py-2 text-sm text-slate-300">
                {accountSummary?.operator_message || accountSummary?.recovery_hint || (accountSummary?.degraded ? "account snapshot degraded" : "")}
              </div>
            )}
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">持倉</div>
                <div className="mt-1 font-semibold text-white">{accountSummary?.position_count ?? positions.length}</div>
                <div className="text-[11px] text-slate-400">{summarizePreviewRecords(positions.slice(0, 2) as ExecutionRunPreviewRecord[])}</div>
              </div>
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">掛單</div>
                <div className="mt-1 font-semibold text-white">{accountSummary?.open_order_count ?? openOrders.length}</div>
                <div className="text-[11px] text-slate-400">{summarizePreviewRecords(openOrders.slice(0, 2) as ExecutionRunPreviewRecord[])}</div>
              </div>
            </div>
            <div className="mt-4 grid gap-2 md:grid-cols-3 text-sm">
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">最近委託</div>
                <div className="mt-1 font-semibold text-white">{lastOrder?.side || "—"} · {lastOrder?.status || "—"}</div>
                <div className="text-[11px] text-slate-400">qty {formatNumber(lastOrder?.qty)} · price {formatNumber(lastOrder?.price)}</div>
              </div>
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">最近拒單</div>
                <div className="mt-1 font-semibold text-white">{lastReject?.code || "none"}</div>
                <div className="text-[11px] text-slate-400">{lastReject?.message || "尚無最近 reject"}</div>
              </div>
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">最近失敗</div>
                <div className="mt-1 font-semibold text-white">{lastFailure?.message || "none"}</div>
                <div className="text-[11px] text-slate-400">{formatTime(lastFailure?.timestamp)}</div>
              </div>
            </div>
          </section>
        </div>
      </section>

      <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="text-lg font-semibold text-white">執行狀態</div>
            <div className="mt-1 text-sm leading-6 text-slate-300">
              blocked 原因、metadata freshness、reconciliation / recovery 已移到獨立頁；這裡只保留營運摘要與入口。
            </div>
          </div>
          <a href="/execution/status" className="inline-flex rounded-xl border border-cyan-400/35 bg-cyan-500/10 px-4 py-2 text-sm font-medium text-cyan-100 transition hover:bg-cyan-500/20">
            前往執行狀態 →
          </a>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm text-slate-300">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">Live readiness</div>
            <div className="mt-2 text-base font-semibold text-white">{executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞"}</div>
            <div className="mt-2">{liveRuntimeTruth?.deployment_blocker || liveRuntimeTruth?.execution_guardrail_reason || executionSurfaceContract?.operator_message || "尚未提供 readiness 訊息。"}</div>
          </div>
          <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm text-slate-300">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">Metadata freshness</div>
            <div className="mt-2 text-base font-semibold text-white">{metadataSmokeFreshness?.label || metadataSmokeFreshness?.status || "unavailable"}</div>
            <div className="mt-2">generated {formatTime(metadataSmoke?.generated_at)} · age {metadataSmokeFreshness?.age_minutes != null ? `${metadataSmokeFreshness.age_minutes.toFixed(1)} 分鐘` : "—"}</div>
          </div>
          <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm text-slate-300">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">Reconciliation / recovery</div>
            <div className="mt-2 text-base font-semibold text-white">{executionReconciliation?.status || "unavailable"}</div>
            <div className="mt-2">{executionReconciliation?.summary || lifecycleContract?.summary || "尚未取得 reconciliation 摘要。"}</div>
          </div>
        </div>
      </section>
    </div>
  );
}