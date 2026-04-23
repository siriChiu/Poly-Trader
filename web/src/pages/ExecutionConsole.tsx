import { useState } from "react";
import { fetchApi, useApi } from "../hooks/useApi";
import { ExecutionHero, ExecutionMetricCard, ExecutionPill, ExecutionSectionCard } from "../components/execution/ExecutionSurface";
import {
  humanizeExecutionOperatorLabel,
  humanizeExecutionReason,
  humanizeExecutionReconciliationStatusLabel,
  humanizeRuntimeClosureStateLabel,
  humanizeRuntimeDetailText,
  humanizeStructureBucketLabel,
  humanizeSupportGovernanceRouteLabel,
  humanizeSupportProgressStatusLabel,
  humanizeSupportRouteLabel,
  isExecutionReconciliationLimitedEvidence,
} from "../utils/runtimeCopy";

const EXECUTION_MODE_LABELS: Record<string, string> = {
  paper: "模擬倉",
  dry_run: "模擬委託",
  live: "實盤",
};

const EXECUTION_VENUE_LABELS: Record<string, string> = {
  binance: "Binance",
  okx: "OKX",
  unknown: "未提供",
};

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
  support_route_verdict?: string | null;
  support_governance_route?: string | null;
  support_progress?: {
    status?: string | null;
    current_rows?: number | null;
    minimum_support_rows?: number | null;
    gap_to_minimum?: number | null;
    delta_vs_previous?: number | null;
  } | null;
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
    health?: {
      connected?: boolean;
      credentials_configured?: boolean;
      error?: string;
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

function humanizeExecutionModeLabel(value?: string | null): string {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized || normalized === "unknown") return "未提供";
  return EXECUTION_MODE_LABELS[normalized] || String(value).trim();
}

function humanizeExecutionVenueLabel(value?: string | null): string {
  const normalized = String(value || "").trim();
  if (!normalized) return "未提供";
  const lower = normalized.toLowerCase();
  return EXECUTION_VENUE_LABELS[lower] || normalized;
}

function humanizeMetadataFreshnessLabel(value?: string | null): string {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized || normalized === "unavailable") return "未提供";
  if (normalized === "fresh") return "新鮮";
  if (normalized === "stale") return "已過期";
  return humanizeRuntimeDetailText(value);
}

function humanizeTradeSideLabel(value?: string | null): string {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) return "—";
  if (["buy", "bid", "long"].includes(normalized)) return "買入";
  if (["sell", "ask", "short"].includes(normalized)) return "賣出";
  if (["reduce", "close"].includes(normalized)) return "減碼";
  return humanizeRuntimeDetailText(value);
}

function summarizePreviewRecord(record: ExecutionRunPreviewRecord): string {
  const symbol = pickPreviewText(record, ["symbol", "instId", "market", "pair"]) || "未提供";
  const side = humanizeTradeSideLabel(pickPreviewText(record, ["side", "positionSide"]));
  const qty = toMaybeNumber(record.size ?? record.qty ?? record.amount ?? record.contracts ?? record.positionAmt);
  const price = toMaybeNumber(record.price ?? record.entryPrice ?? record.avgPrice ?? record.markPrice);
  const status = humanizeRuntimeDetailText(pickPreviewText(record, ["status", "state"]));
  return [
    symbol,
    side,
    qty !== null ? `數量 ${formatNumber(qty, 4)}` : null,
    price !== null ? `價格 ${formatNumber(price, 2)}` : null,
    status,
  ].filter(Boolean).join(" · ");
}

function summarizePreviewRecords(records?: ExecutionRunPreviewRecord[] | null): string {
  if (!Array.isArray(records) || records.length === 0) return "無";
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
  const [naturalCommand, setNaturalCommand] = useState("");

  const refreshExecutionWorkspace = async () => {
    await Promise.all([refreshRuntimeStatus(), refreshExecutionOverview(), refreshExecutionRuns()]);
  };

  const handleRunAction = async (endpoint: string, pendingLabel: string, successLabel: string) => {
    setRunActionState({ tone: "pending", message: pendingLabel });
    try {
      const resp = await fetchApi<{ operator_message?: string }>(endpoint, { method: "POST" });
      await refreshExecutionWorkspace();
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
  const runtimeStatusPending = loading && !runtimeStatus && !error;
  const overviewPending = overviewLoading && !executionOverview && !overviewError;
  const runsPending = runsLoading && !executionRuns && !runsError;
  const executionConsoleInitialSyncPending = runtimeStatusPending || overviewPending || runsPending;
  const metadataSmokeFreshnessLabel = runtimeStatusPending
    ? "同步中"
    : humanizeMetadataFreshnessLabel(metadataSmokeFreshness?.label || metadataSmokeFreshness?.status || null);
  const reconciliationCoverageLimited = isExecutionReconciliationLimitedEvidence(
    executionReconciliation?.status,
    lifecycleAudit?.stage,
    lifecycleContract?.artifact_coverage,
  );
  const reconciliationStatusLabel = runtimeStatusPending
    ? "同步中"
    : humanizeExecutionReconciliationStatusLabel(
      executionReconciliation?.status,
      lifecycleAudit?.stage,
      lifecycleContract?.artifact_coverage,
    );
  const reconciliationSummaryLabel = runtimeStatusPending
    ? "正在向 /api/status 取得對帳 / 恢復摘要。"
    : reconciliationCoverageLimited
      ? `${humanizeRuntimeDetailText(executionReconciliation?.summary || lifecycleContract?.summary || "尚未取得對帳摘要。")} · 尚未有執行期委託，因此目前只能確認「沒有發現明顯對帳落差」，不可視為完整實單驗證。`
      : humanizeRuntimeDetailText(executionReconciliation?.summary || lifecycleContract?.summary || "尚未取得對帳摘要。");
  const supportAlignmentLabel = runtimeStatusPending ? "同步中" : (liveRuntimeTruth?.support_alignment_status || "unavailable");
  const runtimeClosureStateLabel = runtimeStatusPending
    ? "同步中"
    : humanizeRuntimeClosureStateLabel(
      liveRuntimeTruth?.runtime_closure_state,
      liveRuntimeTruth?.runtime_closure_summary,
    );
  const supportRowsLabel = runtimeStatusPending
    ? "同步中"
    : (liveRuntimeTruth?.support_rows_text || "—");
  const supportProgressStatusLabel = runtimeStatusPending
    ? "同步中"
    : humanizeSupportProgressStatusLabel(liveRuntimeTruth?.support_progress?.status || null);
  const supportDeltaLabel = runtimeStatusPending
    ? "同步中"
    : (typeof liveRuntimeTruth?.support_progress?.delta_vs_previous === "number"
      ? `${liveRuntimeTruth.support_progress.delta_vs_previous > 0 ? "+" : ""}${formatNumber(liveRuntimeTruth.support_progress.delta_vs_previous, 0)}`
      : "—");
  const supportRouteVerdictLabel = runtimeStatusPending
    ? "同步中"
    : humanizeSupportRouteLabel(liveRuntimeTruth?.support_route_verdict || null);
  const supportGovernanceRouteLabel = runtimeStatusPending
    ? "同步中"
    : humanizeSupportGovernanceRouteLabel(liveRuntimeTruth?.support_governance_route || null);
  const supportAlignmentCountsLabel = runtimeStatusPending
    ? "執行期 / 校準 同步中"
    : `執行期 / 校準 ${liveRuntimeTruth?.runtime_exact_support_rows ?? "—"} / ${liveRuntimeTruth?.calibration_exact_lane_rows ?? "—"}`;
  const supportAlignmentSummaryLabel = runtimeStatusPending
    ? "正在同步執行期 / 校準樣本對齊。"
    : humanizeRuntimeDetailText(liveRuntimeTruth?.support_alignment_summary || supportAlignmentLabel || "—");
  const rawAllowedLayersReasonLabel = runtimeStatusPending
    ? "同步中"
    : humanizeRuntimeDetailText(liveRuntimeTruth?.allowed_layers_raw_reason || null);
  const finalAllowedLayersReasonLabel = runtimeStatusPending
    ? "同步中"
    : humanizeRuntimeDetailText(liveRuntimeTruth?.allowed_layers_reason || null);

  const positions = Array.isArray(accountSummary?.positions) ? accountSummary.positions : [];
  const openOrders = Array.isArray(accountSummary?.open_orders) ? accountSummary.open_orders : [];
  const balanceCurrency = accountSummary?.balance?.currency || "USDT";
  const balanceFree = typeof accountSummary?.balance?.free === "number" ? accountSummary.balance.free : null;
  const balanceTotal = typeof accountSummary?.balance?.total === "number" ? accountSummary.balance.total : null;
  const accountCredentialsConfigured = Boolean(accountSummary?.health?.credentials_configured ?? executionSummary?.health?.credentials_configured);
  const accountSnapshotUnavailableLabel = !accountCredentialsConfigured
    ? "僅元資料快照"
    : "餘額暫不可用";
  const accountSnapshotUnavailableReason = !accountCredentialsConfigured
    ? "僅同步公開元資料；私有餘額待交易所憑證。"
    : "最新帳戶快照暫無餘額資料。";
  const accountBalanceUnavailableLabel = !accountCredentialsConfigured
    ? "待私有餘額"
    : "餘額暫不可用";
  const accountBalanceUnavailableReason = !accountCredentialsConfigured
    ? "需私有餘額後才能計算 Bot 預算與可部署資金。"
    : "最新 execution snapshot 暫無餘額資料。";
  const sharedLedgerUnavailableLabel = !accountCredentialsConfigured
    ? "尚無 run ledger"
    : "共享 ledger 暫不可用";
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
  const hasBlockedState = !runtimeStatusPending && !executionSurfaceContract?.live_ready;
  const rawPrimaryBlockedReason = liveRuntimeTruth?.deployment_blocker_reason
    || liveRuntimeTruth?.deployment_blocker
    || liveRuntimeTruth?.execution_guardrail_reason
    || liveReadyBlockers[0]
    || executionSurfaceContract?.operator_message
    || null;
  const primaryBlockedReason = runtimeStatusPending ? "正在同步 /api/status" : humanizeExecutionReason(rawPrimaryBlockedReason);
  const blockedReasonSummary = runtimeStatusPending
    ? "正在同步 /api/status"
    : (Array.from(new Set([
      rawPrimaryBlockedReason,
      ...liveReadyBlockers,
    ]
      .map((item) => humanizeExecutionReason(item))
      .filter((item) => item && item !== "尚未提供 blocker 摘要。")))
      .join(" · ") || primaryBlockedReason);
  const manualBuyBlocked = hasBlockedState && Boolean(rawPrimaryBlockedReason);
  const manualBuyBlockedMessage = manualBuyBlocked
    ? "目前阻塞點啟動中：買入指令暫停；減碼 / 模式切換 / 查看阻塞原因仍可使用。"
    : null;
  const deploymentStatusLabel = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");
  const deploymentStatusDetail = runtimeStatusPending
    ? "正在向 /api/status 取得目前阻塞點 / 部署閉環摘要。"
    : humanizeRuntimeDetailText(
      executionSurfaceContract?.live_ready
        ? (liveRuntimeTruth?.runtime_closure_summary || executionSurfaceContract?.operator_message || "目前已滿足主要部署條件。")
        : (liveRuntimeTruth?.runtime_closure_summary || liveRuntimeTruth?.deployment_blocker_reason || primaryBlockedReason)
    );
  const automationEnabled = Boolean(runtimeStatus?.automation);
  const dryRunEnabled = Boolean(runtimeStatus?.dry_run);
  const executionSymbol = runtimeStatus?.symbol || "BTCUSDT";
  const executionModeRaw = executionSummary?.mode || (dryRunEnabled ? "dry_run" : "paper");
  const executionModeLabel = runtimeStatusPending ? "同步中" : humanizeExecutionModeLabel(executionModeRaw);
  const executionVenueLabel = runtimeStatusPending ? "同步中" : humanizeExecutionVenueLabel(executionSummary?.venue || "unknown");
  const automationStatusLabel = runtimeStatusPending ? "自動交易同步中" : `自動交易 ${automationEnabled ? "開啟" : "關閉"}`;
  const operatorQuickCommands = [
    { label: "買入 0.001 BTC", disabled: operatorActionState.tone === "pending" || manualBuyBlocked },
    { label: "減碼 0.001 BTC", disabled: operatorActionState.tone === "pending" },
    { label: automationEnabled ? "切到手動模式" : "切到自動模式", disabled: operatorActionState.tone === "pending" },
    { label: "查看阻塞原因", disabled: operatorActionState.tone === "pending" },
    { label: "重新整理", disabled: operatorActionState.tone === "pending" },
  ];
  const liveReadyStatusLabel = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");
  const balanceTotalLabel = runtimeStatusPending
    ? "同步中"
    : (balanceTotal !== null ? `${formatNumber(balanceTotal)} ${balanceCurrency}` : accountSnapshotUnavailableLabel);
  const balanceBreakdownLabel = runtimeStatusPending
    ? "正在向 /api/status 取得帳戶快照。"
    : (balanceFree !== null && allocatedCapital !== null
      ? `可用 ${formatNumber(balanceFree)} · 已分配 ${formatNumber(allocatedCapital)}`
      : accountSnapshotUnavailableReason);
  const sharedPnlLabel = runsPending
    ? `同步中 ${balanceCurrency}`
    : (runLedgerPreviews.length > 0 ? `${formatSignedNumber(totalUnrealizedPnl)} ${balanceCurrency}` : sharedLedgerUnavailableLabel);
  const sharedPnlSummaryLabel = runsPending
    ? "正在向 /api/execution/runs 取得共享盈虧預覽。"
    : (runLedgerPreviews.length > 0 ? `共享帳戶預覽 · ${executionRunRecords.length} 條運行` : "先啟動運行才會顯示共享盈虧預覽");
  const capitalInUseLabel = executionConsoleInitialSyncPending
    ? `同步中 ${balanceCurrency}`
    : (runLedgerPreviews.length > 0
      ? `${formatNumber(totalCapitalInUse)} ${balanceCurrency}`
      : (allocatedCapital !== null ? `${formatNumber(allocatedCapital)} ${balanceCurrency}` : sharedLedgerUnavailableLabel));
  const capitalInUseSummaryLabel = executionConsoleInitialSyncPending
    ? "正在同步共享帳戶預覽 / 預算。"
      : (runLedgerPreviews.length > 0
      ? "依目前共享帳戶預覽匯總"
      : (allocatedCapital !== null ? "暫以帳戶已分配資金表示" : "先啟動運行；若要顯示共享資金占用仍需私有餘額。"));
  const deployableCapitalLabel = overviewPending || runtimeStatusPending
    ? `同步中 ${balanceCurrency}`
    : (deployableCapital !== null ? `${formatNumber(deployableCapital)} ${balanceCurrency}` : accountBalanceUnavailableLabel);
  const allocationRuleLabel = humanizeExecutionOperatorLabel(
    executionCapitalPlan?.allocation_rule || executionOverviewSummary?.allocation_rule,
    "allocation_rule",
  ) || "啟用倉位腿均分";
  const deployableCapitalSummaryLabel = overviewPending || runtimeStatusPending
    ? "正在向 /api/status 與 /api/execution/overview 取得可部署資金。"
    : (deployableCapital !== null
      ? `資金分配 ${allocationRuleLabel}`
      : `${accountBalanceUnavailableReason}${hasBlockedState ? " blocker 解除後才會得到真正可部署資金。" : ""}`);
  const configuredSleeveCount = executionStrategySummary?.total_sleeves ?? executionOverviewSummary?.total_profiles ?? executionProfileCards.length;
  const sleeveLabelById = new Map<string, string>();
  executionProfileCards.forEach((card) => {
    const label = String(card.label || card.key || card.profile_id || "").trim();
    if (!label) return;
    if (card.profile_id) sleeveLabelById.set(card.profile_id, label);
    if (card.key) sleeveLabelById.set(card.key, label);
  });
  const missingSleeveLabels = (executionStrategySummary?.missing_sleeves || [])
    .map((value) => sleeveLabelById.get(value) || humanizeRuntimeDetailText(value) || value)
    .filter((value): value is string => Boolean(value));
  const runningRunsLabel = runsPending ? "同步中" : String(executionRunsSummary?.running_runs ?? 0);
  const runningRunsSummaryLabel = runsPending
    ? "正在向 /api/execution/runs 取得 run 控制 / 事件。"
    : `運行中 ${executionRunsSummary?.running_runs ?? 0} · 獲利中 ${profitableRuns} · 總計 ${executionRunsSummary?.total_runs ?? executionRunRecords.length} · 已配置倉位腿 ${configuredSleeveCount}`;
  const executionStrategySummaryLabel = overviewPending
    ? "正在向 /api/execution/overview 取得策略 / 倉位腿覆蓋。"
    : `已儲存策略 ${executionStrategySummary?.strategy_count ?? 0} · 已覆蓋倉位腿 ${executionStrategySummary?.covered_sleeves ?? 0}/${executionStrategySummary?.total_sleeves ?? 0} · 缺 ${missingSleeveLabels.join(" / ") || "無"}`;
  const executionProfileCardsEmptyState = overviewPending
    ? "正在向 /api/execution/overview 取得 Bot 卡片。"
    : "尚未取得 Bot 卡片；先確認 /api/execution/overview 是否可用。";
  const executionRunsEmptyState = runsPending
    ? "正在向 /api/execution/runs 取得 run 控制 / 事件。"
    : "尚未建立可持久化運行；先在上方 Bot 卡啟動，這裡才會出現事件與狀態。";
  const liveReadinessSummary = runtimeStatusPending
    ? "正在向 /api/status 取得部署狀態。"
    : humanizeExecutionReason(
      liveRuntimeTruth?.deployment_blocker_reason
      || liveRuntimeTruth?.deployment_blocker
      || liveRuntimeTruth?.execution_guardrail_reason
      || executionSurfaceContract?.operator_message
      || "尚未提供部署狀態訊息。"
    );
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

  const handleOperatorTrade = async (side: "buy" | "reduce", qty = 0.001) => {
    const label = side === "buy" ? "買入" : "減碼";
    if (side === "buy" && manualBuyBlocked) {
      setOperatorActionState({
        tone: "error",
        message: manualBuyBlockedMessage || "目前阻塞點啟動中：買入指令暫停；請先查看阻塞原因。",
      });
      return;
    }
    const normalizedQty = Number.isFinite(qty) && qty > 0 ? qty : 0.001;
    setOperatorActionState({
      tone: "pending",
      message: `${label} 指令送出中… ${executionSymbol} 會送到 /api/trade，數量 ${formatNumber(normalizedQty, 6)}，完成後自動刷新 runtime。`,
    });
    try {
      const resp = await fetchApi<any>("/api/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ side, symbol: executionSymbol, qty: normalizedQty }),
      });
      await refreshRuntimeStatus();
      const order = resp?.order ?? null;
      const normalization = resp?.normalization ?? null;
      const normalizedQtyFromContract = typeof normalization?.normalized?.qty === "number" ? normalization.normalized.qty : (typeof order?.qty === "number" ? order.qty : null);
      const normalizedPrice = typeof normalization?.normalized?.price === "number" ? normalization.normalized.price : null;
      const stepSize = normalization?.contract?.step_size;
      const tickSize = normalization?.contract?.tick_size;
      const contractSummary = [
        stepSize != null ? `數量步進 ${formatNumber(Number(stepSize), 6)}` : null,
        tickSize != null ? `價格刻度 ${formatNumber(Number(tickSize), 6)}` : null,
      ].filter(Boolean).join(" · ");
      const orderModeLabel = humanizeExecutionModeLabel(order?.mode || (resp?.dry_run ? "dry_run" : executionModeRaw));
      const orderVenueLabel = humanizeExecutionVenueLabel(resp?.venue || executionSummary?.venue || executionVenueLabel);
      setOperatorActionState({
        tone: "success",
        message: `${label} 已提交：模式 ${orderModeLabel} · 場館 ${orderVenueLabel}${normalizedQtyFromContract != null ? ` · 校準後數量 ${formatNumber(normalizedQtyFromContract, 6)}` : ""}${normalizedPrice != null ? ` · 校準後價格 ${formatNumber(normalizedPrice, 2)}` : ""}${contractSummary ? ` · 規則 ${contractSummary}` : ""}`,
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
        message: `模式切換失敗：${err?.message || "未知錯誤"}`,
      });
    }
  };

  const handleNaturalLanguageAction = async (rawCommand?: string) => {
    const command = String(rawCommand ?? naturalCommand).trim();
    if (!command) {
      setOperatorActionState({
        tone: "error",
        message: "請直接輸入自然語句，例如：買 0.001 BTC、減碼 0.001、切到自動、查看阻塞原因。",
      });
      return;
    }

    setNaturalCommand("");

    if (/(查看|前往).*(阻塞|診斷|狀態)|execution\s*status|blocker/i.test(command)) {
      setOperatorActionState({
        tone: "success",
        message: "已導向執行狀態頁，請先看 blocker / freshness / recovery。",
      });
      window.location.href = "/execution/status";
      return;
    }

    if (/(策略|實驗室|lab)/i.test(command) && /(前往|打開|開|去)/i.test(command)) {
      setOperatorActionState({
        tone: "success",
        message: "已導向策略實驗室。",
      });
      window.location.href = "/lab";
      return;
    }

    if (/(刷新|重新整理|同步|reload|refresh)/i.test(command)) {
      setOperatorActionState({
        tone: "pending",
        message: "正在同步 Bot 營運頁面…",
      });
      try {
        await refreshExecutionWorkspace();
        setOperatorActionState({
          tone: "success",
          message: "已重新整理 Bot 營運、run 控制與執行狀態。",
        });
      } catch (err: any) {
        setOperatorActionState({
          tone: "error",
          message: `重新整理失敗：${err?.message || "未知錯誤"}`,
        });
      }
      return;
    }

    if (/(切|開|改).*(自動)|自動模式|automation\s*on/i.test(command)) {
      await handleAutomationToggle(true);
      return;
    }

    if (/(切|關|改).*(手動)|關自動|手動模式|automation\s*off/i.test(command)) {
      await handleAutomationToggle(false);
      return;
    }

    const qtyMatch = command.match(/([0-9]+(?:\.[0-9]+)?)/);
    const qty = qtyMatch ? Number(qtyMatch[1]) : 0.001;

    if (/(減碼|賣|平倉|reduce|sell)/i.test(command)) {
      await handleOperatorTrade("reduce", qty);
      return;
    }

    if (/(買入|買|加碼|buy)/i.test(command)) {
      await handleOperatorTrade("buy", qty);
      return;
    }

    setOperatorActionState({
      tone: "error",
      message: "暫時只支援：買入 / 減碼 / 切到自動 / 切到手動 / 查看阻塞原因 / 前往策略實驗室 / 重新整理。",
    });
  };

  return (
    <div className="execution-shell app-page-shell text-white">
      <ExecutionHero
        className="app-page-header"
        eyebrow="Bot 營運 / 執行工作台"
        title="先看我的 Bot、資金使用與盈虧預覽"
        subtitle="主頁只放營運關鍵：Bot 狀態、資金、盈虧；診斷與恢復集中到「執行狀態」。"
        statusPills={(
          <>
            <ExecutionPill>{executionModeLabel}</ExecutionPill>
            <ExecutionPill>{executionVenueLabel}</ExecutionPill>
            <ExecutionPill className={getStatusTone(runtimeStatusPending ? "pending" : (automationEnabled ? "ok" : "warning"))}>
              {automationStatusLabel}
            </ExecutionPill>
            <ExecutionPill className={getStatusTone(runtimeStatusPending ? "pending" : (executionSurfaceContract?.live_ready ? "ok" : "blocked"))}>
              {liveReadyStatusLabel}
            </ExecutionPill>
            <ExecutionPill className={getStatusTone(metadataSmokeFreshness?.status)}>
              新鮮度 {metadataSmokeFreshnessLabel}
            </ExecutionPill>
          </>
        )}
        actions={(
          <>
            <button
              type="button"
              onClick={() => refreshExecutionWorkspace()}
              className="app-button-primary"
            >
              重新整理
            </button>
            <a href="/lab" className="app-button-secondary">
              選策略
            </a>
            <a href="/execution/status" className="app-button-secondary">
              執行狀態
            </a>
          </>
        )}
      >
        {executionSurfaceContract?.operator_message && !hasBlockedState && (
          <div className="rounded-2xl border border-white/8 bg-white/5 px-4 py-3 text-sm text-slate-200">
            {executionSurfaceContract.operator_message}
          </div>
        )}
        {(loading || error) && (
          <div className="rounded-2xl border border-white/8 bg-[#0d1324] px-4 py-3 text-sm text-slate-300">
            {loading ? "/api/status 載入中…" : `載入失敗：${error}`}
          </div>
        )}
        {runActionState.tone !== "idle" && runActionState.message && (
          <div className={`rounded-2xl border px-4 py-3 text-sm ${runActionTone}`}>
            {runActionState.message}
          </div>
        )}
        {hasBlockedState && (
          <div className="rounded-[24px] border border-amber-400/30 bg-[linear-gradient(135deg,rgba(245,158,11,0.18),rgba(113,50,245,0.14))] p-4 shadow-[0_18px_40px_rgba(245,158,11,0.12)]">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-200/80">阻塞中</div>
                <div className="mt-2 text-lg font-semibold text-amber-50">先解除 blocker，再做操作</div>
                <div className="mt-1 text-sm text-amber-100/90">{primaryBlockedReason}</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <a href="/execution/status" className="rounded-xl bg-amber-300 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-amber-200">
                  查看阻塞原因
                </a>
                <button
                  type="button"
                  onClick={() => refreshExecutionWorkspace()}
                  className="app-button-secondary"
                >
                  重新整理
                </button>
              </div>
            </div>
          </div>
        )}
      </ExecutionHero>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <ExecutionMetricCard
          title="資產總覽"
          value={balanceTotalLabel}
          detail={balanceBreakdownLabel}
        />
        <ExecutionMetricCard
          title="共享盈虧預覽"
          value={sharedPnlLabel}
          detail={sharedPnlSummaryLabel}
          toneClass={totalUnrealizedPnl > 0 ? "text-emerald-300" : totalUnrealizedPnl < 0 ? "text-rose-300" : "text-white"}
        />
        <ExecutionMetricCard
          title="資金使用中"
          value={capitalInUseLabel}
          detail={capitalInUseSummaryLabel}
        />
        <ExecutionMetricCard
          title="可部署資金"
          value={deployableCapitalLabel}
          detail={deployableCapitalSummaryLabel}
        />
        <ExecutionMetricCard
          title="運行中 Run"
          value={runningRunsLabel}
          detail={runningRunsSummaryLabel}
        />
        <ExecutionMetricCard
          title="部署狀態"
          value={deploymentStatusLabel}
          detail={deploymentStatusDetail}
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.55fr_0.95fr]">
        <div className="space-y-4">
          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">我的 Bot</div>
                <div className="mt-1 text-sm text-slate-400">
                  已配置 sleeve 策略與共享帳戶預覽；是否真的運行請看「運行中 Run」。
                </div>
              </div>
              <div className="text-right text-xs text-slate-400">
                <div>策略來源 {overviewPending ? "同步中" : (executionStrategySummary?.strategy_count ?? 0)}</div>
                <div>資金規則 {overviewPending ? "同步中" : allocationRuleLabel}</div>
              </div>
            </div>
            {(overviewLoading || overviewError) && (
              <div className="mt-3 rounded-2xl border border-white/8 bg-[#0d1324] px-4 py-3 text-sm text-slate-300">
                {overviewLoading ? "/api/execution/overview 載入中…" : `Bot 營運摘要載入失敗：${overviewError}`}
              </div>
            )}
            {executionOverview?.operator_message && (
              <div className="mt-3 text-sm text-slate-300">{executionOverview.operator_message}</div>
            )}
            <div className="mt-2 text-xs text-slate-400">
              {executionStrategySummaryLabel}
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {executionProfileCards.length > 0 ? executionProfileCards.map((card) => {
                const profileId = card.profile_id || card.key || "";
                const linkedRun = runsByProfileId.get(profileId) || card.current_run || null;
                const profileStrategyBinding = card.strategy_binding ?? null;
                const ledgerPreview = linkedRun?.runtime_binding_snapshot?.shared_symbol_ledger_preview ?? null;
                const profileSharedPreviewValue = typeof ledgerPreview?.unrealized_pnl === "number"
                  ? `${formatSignedNumber(ledgerPreview.unrealized_pnl)} ${ledgerPreview?.currency || balanceCurrency}`
                  : (linkedRun ? "尚無共享預覽" : "未啟動 run");
                const profileSharedPreviewDetail = typeof ledgerPreview?.capital_in_use === "number"
                  ? `資金使用中 ${formatNumber(ledgerPreview.capital_in_use)} ${ledgerPreview?.currency || balanceCurrency}`
                  : (linkedRun ? "run 已建立，但尚未鏡像共享資金占用" : "先啟動 run 才會建立共享帳戶預覽");
                const profileBudgetValue = typeof card.planned_budget_amount === "number"
                  ? `${formatNumber(card.planned_budget_amount)} ${balanceCurrency}`
                  : accountBalanceUnavailableLabel;
                const profileBudgetDetail = typeof card.planned_budget_amount === "number"
                  ? `勝率 ${formatPercent(profileStrategyBinding?.avg_expected_win_rate, 1)}`
                  : `${accountBalanceUnavailableReason} · 勝率 ${formatPercent(profileStrategyBinding?.avg_expected_win_rate, 1)}`;
                const profileLifecycleLabel = humanizeExecutionOperatorLabel(
                  linkedRun?.state_label || linkedRun?.state || card.lifecycle_status || card.activation_status,
                  "status",
                );
                const profileLatestEventLabel = humanizeExecutionOperatorLabel(
                  linkedRun?.last_event_type || card.control_contract?.latest_event_type,
                  "event",
                );
                const profilePositionStatusLabel = humanizeExecutionOperatorLabel(linkedRun?.state_label || linkedRun?.state, "status");
                const profileNextActionLabel = humanizeExecutionOperatorLabel(card.control_contract?.start_status, "start_status");
                const profileNextActionEventLabel = humanizeExecutionOperatorLabel(
                  linkedRun?.latest_event?.event_type || linkedRun?.last_event_type || "waiting",
                  "event",
                );
                const profilePreviewStatusLabel = humanizeExecutionOperatorLabel(
                  ledgerPreview?.budget_alignment_status || ledgerPreview?.ownership_status,
                  "preview",
                );
                const profileRoutingReasonLabel = humanizeRuntimeDetailText(card.routing_reason || null);
                const profileStartReasonLabel = humanizeRuntimeDetailText(card.control_contract?.start_reason || null);
                const profileLatestEventMessageLabel = humanizeRuntimeDetailText(
                  linkedRun?.latest_event?.message || linkedRun?.last_event_message || card.control_contract?.latest_event_message || null,
                );
                const profileSummaryLabel = card.summary || profileStrategyBinding?.summary || profileRoutingReasonLabel || "尚未提供策略摘要";
                const primarySleeveLabel = String(
                  profileStrategyBinding?.primary_sleeve_label || card.strategy_binding?.primary_sleeve_label || "",
                ).trim();
                const cardLabel = String(card.label || card.key || "unknown sleeve").trim();
                const shouldShowPrimarySleeveBadge = Boolean(primarySleeveLabel) && primarySleeveLabel !== cardLabel;
                const strategyBindingStatus = String(profileStrategyBinding?.status || card.strategy_binding?.status || "").trim();
                const strategyBindingTitle = String(
                  profileStrategyBinding?.title || card.strategy_binding?.title || profileStrategyBinding?.strategy_name || "",
                ).trim();
                const strategyBindingBadgeLabel = strategyBindingStatus === "missing_saved_strategy"
                  ? "待儲存策略快照"
                  : (strategyBindingTitle ? `策略：${strategyBindingTitle}` : "已綁定策略快照");
                const strategyBindingBadgeTone = strategyBindingStatus === "missing_saved_strategy"
                  ? "border-amber-500/30 bg-amber-500/10 text-amber-100"
                  : "border-emerald-500/25 bg-emerald-500/10 text-emerald-100";
                const canStart = Boolean(profileId) && ["ready_control_plane", "resume_available"].includes(card.control_contract?.start_status || "");
                const canPause = Boolean(linkedRun?.action_contract?.can_pause && linkedRun?.run_id);
                const canStop = Boolean(linkedRun?.action_contract?.can_stop && linkedRun?.run_id);
                return (
                  <div key={card.key || card.label} className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-base font-semibold text-white">{cardLabel}</div>
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                          {shouldShowPrimarySleeveBadge && (
                            <span className="rounded-full border border-[#7132f5]/25 bg-[#7132f5]/12 px-2.5 py-1 text-[#d8cbff]">
                              {primarySleeveLabel}
                            </span>
                          )}
                          {strategyBindingStatus && (
                            <span className={`rounded-full border px-2.5 py-1 ${strategyBindingBadgeTone}`}>
                              {strategyBindingBadgeLabel}
                            </span>
                          )}
                          <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(linkedRun?.state || card.lifecycle_status || card.activation_status)}`}>
                            {profileLifecycleLabel}
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
                        <div>{profileLatestEventLabel}</div>
                      </div>
                    </div>

                    <div className="mt-3 text-sm text-slate-300">{profileSummaryLabel}</div>

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
                        <div className={`mt-1 text-sm font-semibold ${typeof ledgerPreview?.unrealized_pnl === "number" ? ((ledgerPreview.unrealized_pnl ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300") : "text-white"}`}>
                          {profileSharedPreviewValue}
                        </div>
                        <div className="text-[11px] text-slate-400">{profileSharedPreviewDetail}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">預算 / 勝率</div>
                        <div className="mt-1 text-sm font-semibold text-white">{profileBudgetValue}</div>
                        <div className="text-[11px] text-slate-400">{profileBudgetDetail}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">DQ</div>
                        <div className="mt-1 text-sm font-semibold text-white">{formatNumber(profileStrategyBinding?.avg_decision_quality_score, 3)}</div>
                        <div className="text-[11px] text-slate-400">交易數 {profileStrategyBinding?.total_trades ?? "—"}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">倉位 / 掛單</div>
                        <div className="mt-1 text-sm font-semibold text-white">{card.symbol_scoped_position_count ?? 0} / {card.symbol_scoped_open_order_count ?? 0}</div>
                        <div className="text-[11px] text-slate-400">{profilePositionStatusLabel}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">下一步</div>
                        <div className="mt-1 text-sm font-semibold text-white">{profileNextActionLabel}</div>
                        <div className="text-[11px] text-slate-400">{profileNextActionEventLabel}</div>
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-slate-400">
                      <span>路由 {profileRoutingReasonLabel || "—"}</span>
                      <span>啟動條件 {profileStartReasonLabel || "—"}</span>
                      <span>預覽 {profilePreviewStatusLabel}</span>
                      <span>最新事件 {profileLatestEventMessageLabel || "尚未建立 Bot 事件"}</span>
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
                  {executionProfileCardsEmptyState}
                </div>
              )}
            </div>
          </section>

          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">運行中</div>
                <div className="mt-1 text-sm text-slate-400">
                  {runsPending
                    ? "正在向 /api/execution/runs 取得 run 控制 / 事件。"
                    : `進行中 ${executionRunsSummary?.running_runs ?? 0} · 暫停 ${executionRunsSummary?.paused_runs ?? 0} · 已停止 ${executionRunsSummary?.stopped_runs ?? 0} · 總計 ${executionRunsSummary?.total_runs ?? executionRunRecords.length}`}
                </div>
              </div>
              <div className="text-xs text-slate-400">運行控制（測試版）</div>
            </div>
            {(runsLoading || runsError) && (
              <div className="mt-3 rounded-2xl border border-white/8 bg-[#0d1324] px-4 py-3 text-sm text-slate-300">
                {runsLoading ? "/api/execution/runs 載入中…" : `運行列表載入失敗：${runsError}`}
              </div>
            )}
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {executionRunRecords.length > 0 ? executionRunRecords.slice(0, 6).map((run) => {
                const runStrategyBinding = run.strategy_binding ?? null;
                const latestMessage = run.latest_event?.message || run.last_event_message || "尚未取得 run event";
                const ledgerPreview = run.runtime_binding_snapshot?.shared_symbol_ledger_preview ?? null;
                const runBudgetValue = typeof run.budget_amount === "number"
                  ? `${formatNumber(run.budget_amount)} ${run.capital_currency || balanceCurrency}`
                  : accountBalanceUnavailableLabel;
                const runBudgetDetail = typeof run.budget_amount === "number"
                  ? `ratio ${formatNumber(run.budget_ratio, 3)}`
                  : accountBalanceUnavailableReason;
                const runSharedPreviewValue = typeof ledgerPreview?.unrealized_pnl === "number"
                  ? `${formatSignedNumber(ledgerPreview.unrealized_pnl)} ${ledgerPreview?.currency || balanceCurrency}`
                  : "尚無共享預覽";
                const runSharedPreviewDetail = typeof ledgerPreview?.capital_in_use === "number"
                  ? `資金使用中 ${formatNumber(ledgerPreview.capital_in_use)} ${ledgerPreview?.currency || balanceCurrency}`
                  : "run 已建立，但尚未鏡像共享資金占用";
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
                        <div className="mt-1 font-semibold text-white">{runBudgetValue}</div>
                        <div className="text-slate-400">{runBudgetDetail}</div>
                      </div>
                      <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                        <div className="text-[10px] uppercase tracking-wide text-slate-500">共享盈虧預覽</div>
                        <div className={`mt-1 font-semibold ${typeof ledgerPreview?.unrealized_pnl === "number" ? ((ledgerPreview.unrealized_pnl ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300") : "text-white"}`}>{runSharedPreviewValue}</div>
                        <div className="text-slate-400">{runSharedPreviewDetail}</div>
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
                  {executionRunsEmptyState}
                </div>
              )}
            </div>
          </section>
        </div>

        <div className="space-y-4">
          <ExecutionSectionCard
            title="自然語句操作"
            subtitle={runtimeStatusPending ? "正在向 /api/status 取得 symbol / mode / venue。" : `${executionSymbol} · ${executionModeLabel} · ${executionVenueLabel} · 舊的「應急手動操作」已整併到這裡`}
            aside={(
              <div className={`rounded-full border px-2.5 py-1 text-[11px] ${getStatusTone(runtimeStatusPending ? "pending" : (automationEnabled ? "ok" : "warning"))}`}>
                {automationStatusLabel}
              </div>
            )}
          >
            <div className="text-sm text-slate-300">自然語句會優先幫你判斷是交易、模式切換還是前往診斷；不需要先找對按鈕。</div>
            {manualBuyBlockedMessage && (
              <div className="mt-3 rounded-2xl border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
                {manualBuyBlockedMessage}
              </div>
            )}
            <div className="mt-3 flex flex-col gap-3">
              <input
                value={naturalCommand}
                onChange={(event) => setNaturalCommand(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    void handleNaturalLanguageAction();
                  }
                }}
                className="execution-command-input"
                placeholder="例如：買 0.001 BTC / 減碼 0.001 / 切到自動 / 查看阻塞原因"
              />
              <div className="flex flex-wrap gap-2">
                {operatorQuickCommands.map((command) => (
                  <button
                    key={command.label}
                    type="button"
                    disabled={command.disabled}
                    onClick={() => void handleNaturalLanguageAction(command.label)}
                    className="app-button-secondary"
                  >
                    {command.label}
                  </button>
                ))}
                <button
                  type="button"
                  disabled={operatorActionState.tone === "pending"}
                  onClick={() => void handleNaturalLanguageAction()}
                  className="app-button-primary"
                >
                  執行語句
                </button>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-300">
              <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(guardrails?.kill_switch ? "blocked" : "ok")}`}>停機開關 {guardrails?.kill_switch ? "啟用" : "關閉"}</span>
              <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(guardrails?.failure_halt ? "warning" : "ok")}`}>失敗暫停 {guardrails?.failure_halt ? "啟用" : "關閉"}</span>
              <span className={`rounded-full border px-2.5 py-1 ${getStatusTone(guardrails?.daily_loss_halt ? "warning" : "ok")}`}>日損暫停 {guardrails?.daily_loss_halt ? "啟用" : "關閉"}</span>
            </div>
            {operatorActionState.tone !== "idle" && operatorActionState.message && (
              <div className={`mt-3 rounded-2xl border px-3 py-2 text-sm ${operatorActionTone}`}>
                {operatorActionState.message}
              </div>
            )}
          </ExecutionSectionCard>

          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">部署狀態</div>
                <div className="mt-1 text-sm text-slate-400">{runtimeStatusPending ? "正在向 /api/status 取得市場狀態 / 閘門 / bucket。" : `${humanizeStructureBucketLabel(liveRouting?.current_regime || liveRuntimeTruth?.regime_label || "—")} · 閘門 ${humanizeStructureBucketLabel(liveRouting?.current_regime_gate || liveRuntimeTruth?.regime_gate || "—")} · 當前 bucket ${humanizeStructureBucketLabel(liveRouting?.current_structure_bucket || liveRuntimeTruth?.structure_bucket || "—")}`}</div>
              </div>
              <div className={`rounded-full border px-2.5 py-1 text-[11px] ${getStatusTone(runtimeStatusPending ? "pending" : (executionSurfaceContract?.live_ready ? "ok" : "blocked"))}`}>
                {liveReadyStatusLabel}
              </div>
            </div>
            <div className="mt-3 text-sm text-slate-300">{deploymentStatusDetail}</div>
            <div className="mt-2 text-xs text-slate-400">部署閉環 {runtimeClosureStateLabel}</div>
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">層數</div>
                <div className="mt-1 font-semibold text-white">{liveRuntimeTruth?.allowed_layers_raw ?? "—"} → {liveRuntimeTruth?.allowed_layers ?? "—"}</div>
                <div className="text-[11px] text-slate-400">{finalAllowedLayersReasonLabel !== "—" ? finalAllowedLayersReasonLabel : rawAllowedLayersReasonLabel}</div>
              </div>
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">支持樣本</div>
                <div className="mt-1 font-semibold text-white">{supportRowsLabel}</div>
                <div className="text-[11px] text-slate-400">支持狀態 {supportProgressStatusLabel}</div>
                <div className="text-[11px] text-slate-400">樣本變化 {supportDeltaLabel}</div>
                <div className="text-[11px] text-slate-400">支持路徑 {supportRouteVerdictLabel}</div>
                <div className="text-[11px] text-slate-400">治理路徑 {supportGovernanceRouteLabel}</div>
                <div className="text-[11px] text-slate-400">{supportAlignmentCountsLabel}</div>
                <div className="text-[11px] text-slate-400">{supportAlignmentSummaryLabel}</div>
              </div>
            </div>
            {(runtimeStatusPending || liveReadyBlockers.length > 0) && (
              <div className="mt-3 rounded-2xl border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
                {blockedReasonSummary}
              </div>
            )}
            <div className="mt-4 space-y-3">
              <div>
                <div className="text-[11px] uppercase tracking-wide text-slate-500">啟用倉位腿</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {liveActiveSleeves.length > 0 ? liveActiveSleeves.map((item) => (
                    <span key={item.key || item.label} title={item.why || undefined} className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1 text-[11px] text-emerald-100">
                      {item.label || item.key}
                    </span>
                  )) : <span className="text-sm text-slate-400">目前沒有啟用倉位腿</span>}
                </div>
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-wide text-slate-500">待命倉位腿</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {liveInactiveSleeves.length > 0 ? liveInactiveSleeves.map((item) => (
                    <span key={item.key || item.label} title={item.why || undefined} className="rounded-full border border-rose-500/25 bg-rose-500/10 px-2.5 py-1 text-[11px] text-rose-100">
                      {item.label || item.key}
                    </span>
                  )) : <span className="text-sm text-slate-400">目前沒有待命倉位腿</span>}
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-[24px] border border-white/6 bg-[#151b31] p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">帳戶與成交</div>
                <div className="mt-1 text-sm text-slate-400">擷取時間 {formatTime(accountSummary?.captured_at)}</div>
              </div>
              <div className="text-xs text-slate-400">{accountSummary?.requested_symbol || "—"} → {accountSummary?.normalized_symbol || "—"}</div>
            </div>
            {(accountSummary?.operator_message || accountSummary?.recovery_hint || accountSummary?.degraded) && (
              <div className="mt-3 rounded-2xl border border-white/8 bg-white/5 px-3 py-2 text-sm text-slate-300">
                {humanizeRuntimeDetailText(accountSummary?.operator_message || accountSummary?.recovery_hint || (accountSummary?.degraded ? "account snapshot degraded" : ""))}
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
                <div className="mt-1 font-semibold text-white">{humanizeTradeSideLabel(lastOrder?.side || null)} · {humanizeRuntimeDetailText(lastOrder?.status || null) || "—"}</div>
                <div className="text-[11px] text-slate-400">數量 {formatNumber(lastOrder?.qty)} · 價格 {formatNumber(lastOrder?.price)}</div>
              </div>
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">最近拒單</div>
                <div className="mt-1 font-semibold text-white">{lastReject?.code || "無"}</div>
                <div className="text-[11px] text-slate-400">{lastReject?.message || "尚無最近拒單"}</div>
              </div>
              <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
                <div className="text-[10px] uppercase tracking-wide text-slate-500">最近失敗</div>
                <div className="mt-1 font-semibold text-white">{lastFailure?.message || "無"}</div>
                <div className="text-[11px] text-slate-400">{formatTime(lastFailure?.timestamp)}</div>
              </div>
            </div>
          </section>
        </div>
      </section>

      <details className="execution-card">
        <summary className="cursor-pointer list-none text-lg font-semibold text-white">進階營運細節（需要時再展開）</summary>
        <div className="mt-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <div className="text-lg font-semibold text-white">執行狀態</div>
              <div className="mt-1 text-sm leading-6 text-slate-300">
                阻塞原因、元資料新鮮度與對帳 / 恢復已移到獨立頁；這裡只保留營運摘要與入口。
              </div>
            </div>
            <a href="/execution/status" className="app-button-secondary">
              前往執行狀態 →
            </a>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm text-slate-300">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Live 部署狀態</div>
              <div className="mt-2 text-base font-semibold text-white">{runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞")}</div>
              <div className="mt-2">{liveReadinessSummary}</div>
            </div>
            <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm text-slate-300">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">元資料新鮮度</div>
              <div className="mt-2 text-base font-semibold text-white">{metadataSmokeFreshnessLabel}</div>
              <div className="mt-2">{runtimeStatusPending ? "正在向 /api/status 取得元資料檢查。" : `生成於 ${formatTime(metadataSmoke?.generated_at)} · 距今 ${metadataSmokeFreshness?.age_minutes != null ? `${metadataSmokeFreshness.age_minutes.toFixed(1)} 分鐘` : "—"}`}</div>
            </div>
            <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm text-slate-300">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">對帳 / 恢復</div>
              <div className="mt-2 text-base font-semibold text-white">{reconciliationStatusLabel}</div>
              <div className="mt-2">{reconciliationSummaryLabel}</div>
            </div>
          </div>
        </div>
      </details>
    </div>
  );
}