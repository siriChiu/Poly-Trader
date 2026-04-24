import { useMemo } from "react";
import ExecutionMetadataFreshnessDetail from "../components/ExecutionMetadataFreshnessDetail";
import VenueReadinessSummary from "../components/VenueReadinessSummary";
import { useApi } from "../hooks/useApi";
import { ExecutionHero, ExecutionMetricCard, ExecutionPill, ExecutionSectionCard } from "../components/execution/ExecutionSurface";
import {
  humanizeCurrentLiveBlockerLabel,
  humanizeExecutionModeLabel,
  humanizeExecutionReason,
  humanizeExecutionReconciliationStatusLabel,
  humanizeExecutionVenueLabel,
  humanizePatchTargetLabel,
  humanizeRuntimeClosureStateLabel,
  humanizeRuntimeDetailText,
  humanizeStructureBucketLabel,
  humanizeSupportGovernanceRouteLabel,
  humanizeSupportProgressDeltaLabel,
  humanizeSupportProgressReferenceLabel,
  humanizeSupportProgressStatusLabel,
  humanizeSupportRouteLabel,
  isExecutionReconciliationLimitedEvidence,
  humanizeQ15BucketRootCauseAction,
  humanizeQ15BucketRootCauseLabel,
  humanizeLifecycleDiagnosticLabel,
} from "../utils/runtimeCopy";

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

type Q15BucketRootCauseSummary = {
  verdict?: string | null;
  candidate_patch_type?: string | null;
  candidate_patch_feature?: string | null;
  next_patch_target?: string | null;
  recommended_mode?: string | null;
  reason?: string | null;
  verify_next?: string | null;
  current_live_structure_bucket?: string | null;
  gap_to_q35_boundary?: number | null;
  runtime_remaining_gap_to_floor?: number | null;
  remaining_gap_to_floor?: number | null;
  dominant_neighbor_bucket?: string | null;
  dominant_neighbor_rows?: number | null;
  near_boundary_rows?: number | null;
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
  current_live_structure_bucket_gap_to_minimum?: number | null;
  support_progress?: {
    status?: string | null;
    current_rows?: number | null;
    minimum_support_rows?: number | null;
    gap_to_minimum?: number | null;
    delta_vs_previous?: number | null;
    regressed_from_supported?: boolean | null;
    recent_supported_rows?: number | null;
    recent_supported_heartbeat?: string | null;
    delta_vs_recent_supported?: number | null;
  } | null;
  runtime_exact_support_rows?: number | null;
  calibration_exact_lane_rows?: number | null;
  current_live_structure_bucket?: string | null;
  q15_bucket_root_cause?: Q15BucketRootCauseSummary | null;
  current_bucket_root_cause?: Q15BucketRootCauseSummary | null;
  sleeve_routing?: SleeveRoutingState | null;
};

type ExecutionStatusResponse = {
  symbol?: string;
  timestamp?: string;
  automation?: boolean;
  dry_run?: boolean;
  execution_surface_contract?: {
    canonical_execution_route?: string;
    canonical_surface_label?: string;
    operations_surface?: SurfaceInfo | null;
    diagnostics_surface?: SurfaceInfo | null;
    shortcut_surface?: {
      name?: string;
      role?: string;
      status?: string;
      message?: string;
      upgrade_prerequisite?: string;
    } | null;
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
      max_consecutive_failures?: number;
      daily_loss_ratio?: number | null;
      max_daily_loss_pct?: number | null;
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
    health?: {
      connected?: boolean;
      credentials_configured?: boolean;
      error?: string;
    } | null;
  } | null;
  execution_reconciliation?: {
    status?: string;
    summary?: string;
    checked_at?: string;
    issues?: string[];
    account_snapshot?: {
      captured_at?: string | null;
      degraded?: boolean;
      position_count?: number;
      open_order_count?: number;
      freshness?: {
        status?: string;
        reason?: string;
        age_minutes?: number | null;
        stale_after_minutes?: number | null;
      } | null;
    } | null;
    symbol_scope?: {
      config_symbol?: string;
      requested_symbol?: string | null;
      normalized_symbol?: string | null;
      status?: string;
      reason?: string;
    } | null;
    trade_history_alignment?: {
      status?: string;
      reason?: string;
      latest_trade?: {
        timestamp?: string | null;
        symbol?: string | null;
        exchange?: string | null;
        action?: string | null;
        order_id?: string | null;
        client_order_id?: string | null;
        order_status?: string | null;
      } | null;
    } | null;
    open_order_alignment?: {
      status?: string;
      reason?: string;
      matched_open_order?: {
        id?: string | null;
        symbol?: string | null;
        status?: string | null;
      } | null;
    } | null;
    lifecycle_audit?: {
      stage?: string;
      reason?: string;
      runtime_state?: string;
      trade_history_state?: string;
      matched_open_order_state?: string;
      restart_replay_required?: boolean;
      operator_action?: string;
      evidence?: {
        runtime_order_timestamp?: string | null;
        trade_history_timestamp?: string | null;
      } | null;
    } | null;
    recovery_state?: {
      status?: string;
      reason?: string;
      summary?: string;
      operator_action?: string;
      restart_replay_required?: boolean;
    } | null;
    lifecycle_contract?: {
      status?: string;
      summary?: string;
      baseline_contract_status?: string;
      replay_readiness?: string;
      replay_verdict?: string;
      replay_verdict_reason?: string;
      replay_verdict_summary?: string;
      artifact_coverage?: string;
      operator_next_artifact?: string;
      missing_event_types?: string[];
      venue_lanes_summary?: string;
      venue_lanes?: Array<{
        venue?: string;
        label?: string;
        status?: string;
        summary?: string;
        baseline_observed?: number;
        baseline_required?: number;
        path_observed?: number;
        path_expected?: number;
        restart_replay_status?: string;
        operator_next_artifact?: string;
        operator_action_summary?: string;
        remediation_focus?: string;
        remediation_priority?: string;
        missing_required_artifacts?: string[];
        provenance_counts?: {
          venue_backed?: number;
          dry_run_only?: number;
          internal_only?: number;
          missing_or_not_applicable?: number;
        } | null;
      }>;
    } | null;
    lifecycle_timeline?: {
      status?: string;
      total_events?: number;
      latest_event?: {
        event_type?: string | null;
        order_state?: string | null;
        timestamp?: string | null;
      } | null;
      events?: Array<{
        timestamp?: string | null;
        event_type?: string | null;
        order_state?: string | null;
        source?: string | null;
        summary?: string | null;
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

type PreviewRecord = Record<string, unknown>;

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function formatPercent(value: number | null | undefined, digits = 1): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

function formatTime(value?: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("zh-TW");
}

function humanizeLifecycleList(values?: Array<string | null | undefined>, emptyLabel = "無"): string {
  if (!Array.isArray(values) || values.length === 0) return emptyLabel;
  const items = values
    .map((value) => humanizeLifecycleDiagnosticLabel(value || "unknown"))
    .filter((value) => Boolean(value));
  return items.length > 0 ? items.join(" / ") : emptyLabel;
}

function pickPreviewText(record: PreviewRecord, keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key];
    if (value == null) continue;
    const text = String(value).trim();
    if (text) return text;
  }
  return null;
}

function toMaybeNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function summarizePreviewRecord(record: PreviewRecord): string {
  const symbol = pickPreviewText(record, ["symbol", "instId", "market", "pair"]) || "—";
  const side = pickPreviewText(record, ["side", "positionSide"]);
  const qty = toMaybeNumber(record.size ?? record.qty ?? record.amount ?? record.contracts ?? record.positionAmt);
  const price = toMaybeNumber(record.price ?? record.entryPrice ?? record.avgPrice ?? record.markPrice);
  const status = pickPreviewText(record, ["status", "state"]);
  return [
    symbol,
    side,
    qty !== null ? `數量 ${formatNumber(qty, 4)}` : null,
    price !== null ? `價格 ${formatNumber(price, 2)}` : null,
    status ? humanizeLifecycleDiagnosticLabel(status) : null,
  ].filter(Boolean).join(" · ");
}

function summarizePreviewRecords(records?: PreviewRecord[] | null): string {
  if (!Array.isArray(records) || records.length === 0) return "無";
  return records.map((record) => summarizePreviewRecord(record)).join(" ｜ ");
}

function getStatusTone(status?: string | null): string {
  const normalized = String(status || "").toLowerCase();
  if (["ok", "healthy", "aligned", "fresh", "running", "connected", "ready"].some((item) => normalized.includes(item))) {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
  }
  if (["stale", "warning", "degraded", "attention", "operator", "replay"].some((item) => normalized.includes(item))) {
    return "border-amber-500/30 bg-amber-500/10 text-amber-100";
  }
  if (["fail", "error", "blocked", "halt", "missing", "not"].some((item) => normalized.includes(item))) {
    return "border-rose-500/30 bg-rose-500/10 text-rose-100";
  }
  return "border-cyan-500/30 bg-cyan-500/10 text-cyan-100";
}

function getValueTone(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value) || value === 0) return "text-slate-100";
  return value > 0 ? "text-emerald-300" : "text-rose-300";
}

function MetricCard({ title, value, detail, tone }: { title: string; value: string; detail: string; tone?: string }) {
  return (
    <div className={`rounded-[20px] border p-4 ${tone || "border-white/8 bg-[#0f1528]"}`}>
      <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">{title}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
      <div className="mt-2 text-sm leading-5 text-slate-400">{detail}</div>
    </div>
  );
}

export default function ExecutionStatus() {
  const { data: runtimeStatus, loading, error, refresh } = useApi<ExecutionStatusResponse>("/api/status", 60000);
  const runtimeStatusPending = loading && !runtimeStatus && !error;

  const executionSurfaceContract = runtimeStatus?.execution_surface_contract ?? null;
  const operationsSurface = executionSurfaceContract?.operations_surface ?? null;
  const diagnosticsSurface = executionSurfaceContract?.diagnostics_surface ?? null;
  const liveRuntimeTruth = runtimeStatus?.execution?.live_runtime_truth ?? executionSurfaceContract?.live_runtime_truth ?? null;
  const liveRouting = liveRuntimeTruth?.sleeve_routing ?? null;
  const liveActiveSleeves = Array.isArray(liveRouting?.active_sleeves) ? liveRouting.active_sleeves : [];
  const liveInactiveSleeves = Array.isArray(liveRouting?.inactive_sleeves) ? liveRouting.inactive_sleeves : [];
  const liveReadyBlockers = Array.isArray(executionSurfaceContract?.live_ready_blockers) ? executionSurfaceContract.live_ready_blockers : [];

  const executionSummary = runtimeStatus?.execution ?? null;
  const guardrails = executionSummary?.guardrails ?? null;
  const accountSummary = runtimeStatus?.account ?? null;
  const positions = Array.isArray(accountSummary?.positions) ? accountSummary.positions : [];
  const openOrders = Array.isArray(accountSummary?.open_orders) ? accountSummary.open_orders : [];
  const lastOrder = guardrails?.last_order ?? null;
  const lastReject = guardrails?.last_reject ?? null;
  const lastFailure = guardrails?.last_failure ?? null;

  const metadataSmoke = runtimeStatus?.execution_metadata_smoke ?? null;
  const metadataFreshness = metadataSmoke?.freshness ?? null;
  const metadataGovernance = metadataSmoke?.governance ?? null;
  const venueChecks = Array.isArray(metadataSmoke?.venues) ? metadataSmoke.venues : [];

  const executionReconciliation = runtimeStatus?.execution_reconciliation ?? null;
  const reconciliationIssues = Array.isArray(executionReconciliation?.issues) ? executionReconciliation.issues : [];
  const lifecycleAudit = executionReconciliation?.lifecycle_audit ?? null;
  const recoveryState = executionReconciliation?.recovery_state ?? null;
  const lifecycleContract = executionReconciliation?.lifecycle_contract ?? null;
  const venueLanes = Array.isArray(lifecycleContract?.venue_lanes) ? lifecycleContract.venue_lanes : [];
  const timelineEvents = Array.isArray(executionReconciliation?.lifecycle_timeline?.events)
    ? executionReconciliation.lifecycle_timeline.events
    : [];

  const balanceCurrency = accountSummary?.balance?.currency || "USDT";
  const balanceTotal = typeof accountSummary?.balance?.total === "number" ? accountSummary.balance.total : null;
  const balanceFree = typeof accountSummary?.balance?.free === "number" ? accountSummary.balance.free : null;
  const accountCredentialsConfigured = Boolean(accountSummary?.health?.credentials_configured);
  const accountBalanceUnavailableLabel = !accountCredentialsConfigured
    ? "僅公開資料 / 元資料觀測"
    : "餘額暫不可用";
  const accountBalanceUnavailableReason = !accountCredentialsConfigured
    ? "尚未配置交易所憑證，因此私有餘額暫不可見。"
    : "最新帳戶快照暫無餘額資料。";
  const accountBalanceSummaryValue = balanceTotal !== null
    ? `${formatNumber(balanceTotal)} ${balanceCurrency}`
    : accountBalanceUnavailableLabel;
  const accountBalanceSummaryFree = balanceFree !== null
    ? `可用 ${balanceFree.toFixed(2)} ${balanceCurrency}`
    : accountBalanceUnavailableReason;
  const lifecycleSummary = useMemo(() => {
    return [
      `階段 ${humanizeLifecycleDiagnosticLabel(lifecycleAudit?.stage || "unknown")}`,
      `重播 ${humanizeLifecycleDiagnosticLabel(lifecycleContract?.replay_verdict || (lifecycleAudit?.restart_replay_required ? "required" : "not-required"))}`,
      `證據覆蓋 ${humanizeLifecycleDiagnosticLabel(lifecycleContract?.artifact_coverage || "unknown")}`,
    ].join(" · ");
  }, [lifecycleAudit, lifecycleContract]);
  const readinessTone = getStatusTone(runtimeStatusPending ? "pending" : (executionSurfaceContract?.live_ready ? "ready" : liveRuntimeTruth?.deployment_blocker || "blocked"));
  const metadataTone = getStatusTone(metadataFreshness?.status);
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
  const reconciliationHeadlineLabel = runtimeStatusPending
    ? "同步中"
    : (reconciliationCoverageLimited ? "證據有限" : reconciliationStatusLabel);
  const reconciliationHeadlineDetail = runtimeStatusPending
    ? "正在向 /api/status 取得對帳 / 恢復摘要。"
    : reconciliationCoverageLimited
      ? `${humanizeRuntimeDetailText(executionReconciliation?.summary || "尚未取得對帳摘要。")} · 尚未有執行期委託，因此目前只能確認「沒有發現明顯對帳落差」，不可視為完整實單驗證。 · ${lifecycleSummary}`
      : `${humanizeRuntimeDetailText(executionReconciliation?.summary || "尚未取得對帳摘要。")} · ${lifecycleSummary}`;
  const reconciliationTone = getStatusTone(reconciliationCoverageLimited ? "warning" : executionReconciliation?.status);
  const healthTone = getStatusTone(accountSummary?.degraded ? "degraded" : accountSummary?.health?.connected ? "connected" : "warning");

  const currentLiveBlocker = liveRuntimeTruth?.deployment_blocker || null;
  const primaryRuntimeMessage = runtimeStatusPending
    ? "正在同步 /api/status"
    : humanizeExecutionReason(
      liveRuntimeTruth?.deployment_blocker_reason
      || liveRuntimeTruth?.deployment_blocker
      || liveRuntimeTruth?.execution_guardrail_reason
      || liveReadyBlockers[0]
      || executionSurfaceContract?.operator_message
      || "目前沒有額外阻塞點摘要。"
    );
  const currentLiveBlockerLabel = runtimeStatusPending
    ? "同步中"
    : humanizeCurrentLiveBlockerLabel(currentLiveBlocker || "unavailable");
  const readinessScopeLabel = runtimeStatusPending
    ? "同步中"
    : humanizeRuntimeDetailText(executionSurfaceContract?.readiness_scope || "runtime_governance_visibility_only");
  const metadataFreshnessLabel = runtimeStatusPending
    ? "同步中"
    : humanizeLifecycleDiagnosticLabel(metadataFreshness?.label || metadataFreshness?.status || "unavailable");
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
  const supportGapLabel = runtimeStatusPending
    ? "同步中"
    : (typeof liveRuntimeTruth?.current_live_structure_bucket_gap_to_minimum === "number"
      ? liveRuntimeTruth.current_live_structure_bucket_gap_to_minimum.toFixed(0)
      : (typeof liveRuntimeTruth?.support_progress?.gap_to_minimum === "number"
        ? liveRuntimeTruth.support_progress.gap_to_minimum.toFixed(0)
        : "—"));
  const supportProgressStatusLabel = runtimeStatusPending
    ? "同步中"
    : humanizeSupportProgressStatusLabel(liveRuntimeTruth?.support_progress?.status || null);
  const supportDeltaLabel = runtimeStatusPending
    ? "同步中"
    : humanizeSupportProgressDeltaLabel(liveRuntimeTruth?.support_progress || null);
  const supportReferenceLabel = runtimeStatusPending
    ? "同步中"
    : humanizeSupportProgressReferenceLabel(liveRuntimeTruth?.support_progress || null);
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
  const deploymentDiagnosticsSubtitle = runtimeStatusPending
    ? "正在同步部署閉環摘要。"
    : humanizeRuntimeDetailText(liveRuntimeTruth?.runtime_closure_summary || primaryRuntimeMessage);
  const executionGuardrailLabel = runtimeStatusPending
    ? "同步中"
    : humanizeRuntimeDetailText(liveRuntimeTruth?.execution_guardrail_reason || null);
  const rawAllowedLayersReasonLabel = runtimeStatusPending
    ? "同步中"
    : humanizeRuntimeDetailText(liveRuntimeTruth?.allowed_layers_raw_reason || null);
  const finalAllowedLayersReasonLabel = runtimeStatusPending
    ? "同步中"
    : humanizeRuntimeDetailText(liveRuntimeTruth?.allowed_layers_reason || null);
  const currentBucketRootCause = liveRuntimeTruth?.current_bucket_root_cause ?? liveRuntimeTruth?.q15_bucket_root_cause ?? null;
  const currentBucketRootCauseLabel = runtimeStatusPending
    ? "同步中"
    : humanizeQ15BucketRootCauseLabel(currentBucketRootCause?.verdict || null);
  const currentBucketRootCauseSummary = runtimeStatusPending
    ? "正在同步當前分桶根因。"
    : humanizeRuntimeDetailText(currentBucketRootCause?.reason || "尚未取得當前分桶根因。");
  const currentBucketRootCauseActionLabel = runtimeStatusPending
    ? "同步中"
    : humanizeQ15BucketRootCauseAction(currentBucketRootCause?.candidate_patch_type || currentBucketRootCause?.recommended_mode || null);
  const currentBucketRootCausePatchTargetLabel = runtimeStatusPending
    ? "同步中"
    : humanizePatchTargetLabel(currentBucketRootCause?.candidate_patch_feature || currentBucketRootCause?.next_patch_target || null);
  const currentBucketRootCauseBucketRaw = currentBucketRootCause?.current_live_structure_bucket
    || liveRuntimeTruth?.current_live_structure_bucket
    || liveRuntimeTruth?.structure_bucket
    || "—";
  const currentBucketRootCauseBucket = runtimeStatusPending
    ? "同步中"
    : humanizeStructureBucketLabel(currentBucketRootCauseBucketRaw);
  const currentBucketRootCauseBucketKey = String(currentBucketRootCauseBucketRaw || "").toLowerCase();
  const currentBucketRootCauseTradeFloorGap = currentBucketRootCause?.runtime_remaining_gap_to_floor
    ?? currentBucketRootCause?.remaining_gap_to_floor
    ?? null;
  const currentBucketRootCauseIsQ35 = currentBucketRootCauseBucketKey === "q35" || currentBucketRootCauseBucketKey.endsWith("|q35");
  const currentBucketRootCauseDrilldownLabel = currentBucketRootCauseIsQ35
    ? `交易門檻缺口 ${formatNumber(currentBucketRootCauseTradeFloorGap, 4)} · q35 公式 / 重設仍只屬治理參考`
    : `近邊界樣本 ${currentBucketRootCause?.near_boundary_rows ?? "—"} · 距 q35 還差 ${formatNumber(currentBucketRootCause?.gap_to_q35_boundary, 4)}`;
  const venueBlockersLabel = runtimeStatusPending
    ? "同步中"
    : (liveReadyBlockers.length > 0 ? liveReadyBlockers.map((item) => humanizeExecutionReason(item)).join(" · ") : "目前沒有額外場館阻塞");
  const executionStatusSymbolLabel = runtimeStatusPending ? "同步中" : (runtimeStatus?.symbol || "BTCUSDT");
  const inferredExecutionStatusMode = runtimeStatus?.dry_run ? "dry_run" : "unknown";
  const executionStatusModeLabel = runtimeStatusPending
    ? "同步中"
    : humanizeExecutionModeLabel(executionSummary?.mode || inferredExecutionStatusMode);
  const executionStatusVenueLabel = runtimeStatusPending
    ? "同步中"
    : humanizeExecutionVenueLabel(executionSummary?.venue || "unknown");
  const automationStatusLabel = runtimeStatusPending ? "自動交易同步中" : `自動交易 ${runtimeStatus?.automation ? "開啟" : "關閉"}`;
  const liveReadinessStatusLabel = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞");
  const liveReadinessMetricValue = runtimeStatusPending ? "同步中" : (executionSurfaceContract?.live_ready ? "可進場" : "仍阻塞");
  const accountVisibilityMetricValue = runtimeStatusPending
    ? "同步中"
    : (balanceTotal !== null ? `${formatNumber(balanceTotal)} ${balanceCurrency}` : (!accountCredentialsConfigured ? "僅元資料快照" : "餘額暫不可用"));
  const accountVisibilityDetail = runtimeStatusPending
    ? "正在向 /api/status 取得帳戶快照。"
    : balanceTotal !== null
      ? `可用餘額 ${balanceFree !== null ? `${balanceFree.toFixed(2)} ${balanceCurrency}` : "—"} · 倉位 ${accountSummary?.position_count ?? positions.length} · 掛單 ${accountSummary?.open_order_count ?? openOrders.length}`
      : !accountCredentialsConfigured
        ? `僅取得元資料；私有餘額仍需配置交易所憑證。 · 倉位 ${accountSummary?.position_count ?? positions.length} · 掛單 ${accountSummary?.open_order_count ?? openOrders.length}`
        : `${accountBalanceUnavailableReason} · 倉位 ${accountSummary?.position_count ?? positions.length} · 掛單 ${accountSummary?.open_order_count ?? openOrders.length}`;
  const accountVisibilityStatusLabel = runtimeStatusPending
    ? "同步中"
    : (!accountCredentialsConfigured ? "僅元資料" : (balanceTotal !== null ? "完整快照" : "餘額暫不可用"));
  const accountSnapshotBadgeLabel = runtimeStatusPending
    ? "同步中"
    : accountSummary?.degraded
      ? "降級"
      : (!accountCredentialsConfigured ? "僅元資料" : (accountSummary?.health?.connected ? "連線正常" : "待檢查"));
  const accountSnapshotBadgeTone = runtimeStatusPending
    ? getStatusTone("pending")
    : accountSummary?.degraded
      ? getStatusTone("degraded")
      : (!accountCredentialsConfigured ? getStatusTone("warning") : healthTone);
  const executionStatusPostureLabel = runtimeStatusPending
    ? "⏳ 整體狀態：同步中"
    : (executionSurfaceContract?.live_ready ? "✅ 整體狀態：可部署" : `🚫 整體狀態：仍阻塞 · ${currentLiveBlockerLabel}`);
  const executionStatusPostureSummary = runtimeStatusPending
    ? "正在同步 /api/status；在執行期真相到位前，不要把資料新鮮或對帳正常誤讀成可部署狀態。"
    : executionSurfaceContract?.live_ready
      ? `目前可部署；資料 ${metadataFreshnessLabel}、對帳 ${reconciliationHeadlineLabel}、帳戶 ${accountVisibilityStatusLabel}。`
      : `先依目前阻塞點行動；資料 ${metadataFreshnessLabel}、對帳 ${reconciliationHeadlineLabel}、帳戶 ${accountVisibilityStatusLabel} 只代表觀測層狀態，不等於可部署。`;
  const executionStatusPostureTone = runtimeStatusPending
    ? getStatusTone("pending")
    : (executionSurfaceContract?.live_ready ? getStatusTone("ready") : getStatusTone("blocked"));

  return (
    <div className="execution-shell app-page-shell text-white">
      <ExecutionHero
        className="app-page-header"
        eyebrow="執行狀態 / 診斷"
        title="先看阻塞點，再決定是否介入"
        subtitle="這頁只保留執行診斷：先看目前阻塞點；資料新鮮、對帳正常只代表觀測層狀態，不代表可部署。"
        statusPills={(
          <>
            <ExecutionPill>{executionStatusSymbolLabel}</ExecutionPill>
            <ExecutionPill>{executionStatusModeLabel}</ExecutionPill>
            <ExecutionPill>{executionStatusVenueLabel}</ExecutionPill>
            <ExecutionPill className={runtimeStatusPending ? getStatusTone("pending") : getStatusTone(runtimeStatus?.automation ? "ok" : "warning")}>
              {automationStatusLabel}
            </ExecutionPill>
            <ExecutionPill className={readinessTone}>
              {liveReadinessStatusLabel}
            </ExecutionPill>
            <ExecutionPill className={metadataTone}>
              元資料 {humanizeLifecycleDiagnosticLabel(metadataFreshnessLabel)}
            </ExecutionPill>
          </>
        )}
        actions={(
          <>
            <button
              type="button"
              onClick={() => refresh()}
              className="app-button-primary"
            >
              重新整理
            </button>
            <a href="/execution" className="app-button-secondary">
              回到 Bot 營運
            </a>
            <a href="/lab" className="app-button-secondary">
              回到策略實驗室
            </a>
          </>
        )}
      >
        {(loading || error) && (
          <div className="rounded-2xl border border-white/8 bg-[#0d1324] px-4 py-3 text-sm text-slate-300">
            {loading ? "/api/status 載入中…" : `載入失敗：${error}`}
          </div>
        )}

        <div className={`rounded-[20px] border px-4 py-4 text-sm ${executionStatusPostureTone}`}>
          <div className="text-[11px] uppercase tracking-[0.22em] opacity-80">整體部署態勢</div>
          <div className="mt-2 text-lg font-semibold text-white">{executionStatusPostureLabel}</div>
          <div className="mt-2 leading-6 opacity-90">{executionStatusPostureSummary}</div>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <ExecutionMetricCard
            title="可部署"
            value={liveReadinessMetricValue}
            detail={`阻塞點 ${currentLiveBlockerLabel} · ${primaryRuntimeMessage} · 治理範圍 ${readinessScopeLabel}`}
            toneClass={readinessTone.includes("amber") ? "text-amber-100" : readinessTone.includes("emerald") || readinessTone.includes("cyan") ? "text-emerald-200" : "text-white"}
          />
          <ExecutionMetricCard
            title="資料新鮮度"
            value={metadataFreshnessLabel}
            detail={(
              <ExecutionMetadataFreshnessDetail
                pending={runtimeStatusPending}
                generatedAt={metadataSmoke?.generated_at}
                freshness={metadataFreshness}
                governance={metadataGovernance}
                compact
              />
            )}
            toneClass={metadataTone.includes("amber") ? "text-amber-100" : metadataTone.includes("emerald") || metadataTone.includes("cyan") ? "text-emerald-200" : "text-white"}
          />
          <ExecutionMetricCard
            title="對帳狀態"
            value={reconciliationHeadlineLabel}
            detail={reconciliationHeadlineDetail}
            toneClass={reconciliationTone.includes("rose") ? "text-rose-200" : reconciliationTone.includes("amber") ? "text-amber-100" : "text-white"}
          />
          <ExecutionMetricCard
            title="帳戶可見性"
            value={accountVisibilityMetricValue}
            detail={accountVisibilityDetail}
            toneClass={accountSnapshotBadgeTone.includes("rose") ? "text-rose-200" : accountSnapshotBadgeTone.includes("amber") ? "text-amber-100" : "text-white"}
          />
        </div>
      </ExecutionHero>

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="space-y-4">
          <ExecutionSectionCard
            title="部署診斷"
            subtitle={deploymentDiagnosticsSubtitle}
            aside={(
              <div className={`rounded-full border px-2.5 py-1 text-[11px] ${readinessTone}`}>
                {runtimeClosureStateLabel}
              </div>
            )}
          >
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">主要阻塞點</div>
                <div className="mt-2 font-semibold text-white">{primaryRuntimeMessage}</div>
                <div className="mt-2 text-slate-400">部署阻塞點 {currentLiveBlockerLabel}</div>
                <div className="text-slate-400">執行保護欄 {executionGuardrailLabel}</div>
                <div className="text-slate-400">場館阻塞 {venueBlockersLabel}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">部署計算</div>
                <div className="mt-2 font-semibold text-white">層數 {liveRuntimeTruth?.allowed_layers_raw ?? "—"} → {liveRuntimeTruth?.allowed_layers ?? "—"}</div>
                <div className="mt-2 text-slate-400">原始原因 {rawAllowedLayersReasonLabel}</div>
                <div className="text-slate-400">最終原因 {finalAllowedLayersReasonLabel}</div>
                <div className="mt-2 text-slate-400">當前分桶 {supportRowsLabel} · 缺口 {supportGapLabel}</div>
                <div className="text-slate-400">支持狀態 {supportProgressStatusLabel}</div>
                <div className="text-slate-400">樣本變化 {supportDeltaLabel}</div>
                <div className="text-slate-400">最近已就緒 {supportReferenceLabel}</div>
                <div className="text-slate-400">支持路徑 {supportRouteVerdictLabel}</div>
                <div className="text-slate-400">治理路徑 {supportGovernanceRouteLabel}</div>
                <div className="text-slate-400">{supportAlignmentCountsLabel}</div>
                <div className="text-slate-400">對齊 {supportAlignmentSummaryLabel}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] tracking-wide text-slate-500">當前分桶根因</div>
                <div className="mt-2 font-semibold text-white">{currentBucketRootCauseLabel}</div>
                <div className="mt-2 text-slate-400">{humanizeRuntimeDetailText(currentBucketRootCauseSummary)}</div>
                <div className="text-slate-400">當前分桶 {currentBucketRootCauseBucket}</div>
                <div className="text-slate-400">候選修補方案 {currentBucketRootCausePatchTargetLabel} · {currentBucketRootCauseActionLabel}</div>
                <div className="text-slate-400">{currentBucketRootCauseDrilldownLabel}</div>
                <div className="text-slate-400">下一步請驗證 {humanizeRuntimeDetailText(currentBucketRootCause?.verify_next || "—")}</div>
              </div>
            </div>

            <div className="mt-4 rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-semibold text-white">市場路由</div>
                <div className="text-[11px] text-slate-400">啟用倉位腿 {liveRouting?.active_ratio_text || "0/0"}</div>
              </div>
              <div className="mt-2 text-slate-300">
                {humanizeStructureBucketLabel(liveRouting?.current_regime || liveRuntimeTruth?.regime_label || "—")} · 閘門 {humanizeStructureBucketLabel(liveRouting?.current_regime_gate || liveRuntimeTruth?.regime_gate || "—")} · 當前分桶 {humanizeStructureBucketLabel(liveRouting?.current_structure_bucket || liveRuntimeTruth?.structure_bucket || "—")}
              </div>
              <div className="mt-2 text-sm text-slate-400">{humanizeRuntimeDetailText(liveRouting?.summary || liveRuntimeTruth?.support_alignment_summary || "尚未取得倉位路由摘要。")}</div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
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
            </div>
          </ExecutionSectionCard>

          <section className="rounded-[24px] border border-white/8 bg-[#151b31] p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">帳戶快照</div>
                <div className="mt-1 text-sm text-slate-400">擷取時間 {formatTime(accountSummary?.captured_at)} · {accountSummary?.requested_symbol || "—"} → {accountSummary?.normalized_symbol || "—"}</div>
              </div>
              <div className={`rounded-full border px-2.5 py-1 text-[11px] ${accountSnapshotBadgeTone}`}>
                {accountSnapshotBadgeLabel}
              </div>
            </div>

            {(accountSummary?.operator_message || accountSummary?.recovery_hint || accountSummary?.health?.error) && (
              <div className="mt-3 rounded-2xl border border-white/8 bg-white/5 px-3 py-2 text-sm text-slate-300">
                {humanizeRuntimeDetailText(accountSummary?.operator_message || accountSummary?.recovery_hint || accountSummary?.health?.error || "—")}
              </div>
            )}

            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">餘額</div>
                <div className="mt-2 font-semibold text-white">{accountBalanceSummaryValue}</div>
                <div className="mt-2 text-slate-400">{accountBalanceSummaryFree}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">倉位</div>
                <div className="mt-2 font-semibold text-white">{accountSummary?.position_count ?? positions.length}</div>
                <div className="mt-2 text-slate-400">{summarizePreviewRecords(positions.slice(0, 2))}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">掛單</div>
                <div className="mt-2 font-semibold text-white">{accountSummary?.open_order_count ?? openOrders.length}</div>
                <div className="mt-2 text-slate-400">{summarizePreviewRecords(openOrders.slice(0, 2))}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">風控</div>
                <div className="mt-2 font-semibold text-white">日損 {formatPercent(guardrails?.daily_loss_ratio, 2)}</div>
                <div className="mt-2 text-slate-400">上限 {formatPercent(guardrails?.max_daily_loss_pct, 1)}</div>
                <div className="text-slate-400">連續失敗 {guardrails?.consecutive_failures ?? 0}/{guardrails?.max_consecutive_failures ?? 0}</div>
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">最近委託</div>
                <div className="mt-2 font-semibold text-white">{lastOrder?.side || "—"} · {lastOrder?.status || "—"}</div>
                <div className="mt-2 text-slate-400">數量 {formatNumber(lastOrder?.qty)} · 價格 {formatNumber(lastOrder?.price)}</div>
                <div className="text-slate-400">{lastOrder?.order_id || lastOrder?.client_order_id || "尚無委託 ID"}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">最近拒單</div>
                <div className="mt-2 font-semibold text-white">{lastReject?.code || "無"}</div>
                <div className="mt-2 text-slate-400">{lastReject?.message || "尚無拒單紀錄"}</div>
                <div className="text-slate-400">{formatTime(lastReject?.timestamp)}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">最近失敗</div>
                <div className="mt-2 font-semibold text-white">{lastFailure?.message || "無"}</div>
                <div className="mt-2 text-slate-400">{formatTime(lastFailure?.timestamp)}</div>
                <div className="text-slate-400">熔斷開關 {guardrails?.kill_switch ? "開啟" : "關閉"}</div>
              </div>
            </div>
          </section>
        </div>

        <div className="space-y-4">
          <section className="rounded-[24px] border border-white/8 bg-[#151b31] p-4">
            <div className="text-lg font-semibold text-white">場館前提與新鮮度</div>
            <div className="mt-1 text-sm text-slate-400">生成於 {formatTime(metadataSmoke?.generated_at)} · 治理狀態 {humanizeLifecycleDiagnosticLabel(metadataGovernance?.status || "unknown")}</div>
            <div className={`mt-3 rounded-2xl border px-3 py-3 text-sm ${metadataTone}`}>
              <div className="font-semibold">元資料狀態 {metadataFreshnessLabel}</div>
              <div className="mt-2 opacity-90">
                <ExecutionMetadataFreshnessDetail
                  pending={runtimeStatusPending}
                  generatedAt={metadataSmoke?.generated_at}
                  freshness={metadataFreshness}
                  governance={metadataGovernance}
                />
              </div>
            </div>

            <VenueReadinessSummary venues={venueChecks} className="mt-4" />
          </section>

          <details className="execution-card">
            <summary className="cursor-pointer list-none text-lg font-semibold text-white">進階診斷（介面契約 / 時間線；需要時再展開）</summary>
            <div className="mt-4 space-y-3 text-sm text-slate-300">
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">介面契約</div>
                <div className="mt-2">canonical 路由 {humanizeRuntimeDetailText(executionSurfaceContract?.canonical_execution_route || "dashboard")}</div>
                <div className="mt-1">canonical 介面 {humanizeRuntimeDetailText(executionSurfaceContract?.canonical_surface_label || diagnosticsSurface?.label || "執行狀態")}</div>
                <div className="mt-1">營運入口 {humanizeRuntimeDetailText(operationsSurface?.label || "Bot 營運")} · {operationsSurface?.route || "/execution"}</div>
                <div className="mt-1">診斷入口 {humanizeRuntimeDetailText(diagnosticsSurface?.label || "執行狀態")} · {diagnosticsSurface?.route || "/execution/status"}</div>
                <div className="mt-1">快捷入口 {humanizeRuntimeDetailText(executionSurfaceContract?.shortcut_surface?.name || "signal_banner")} · {humanizeLifecycleDiagnosticLabel(executionSurfaceContract?.shortcut_surface?.status || "available")}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">最新時間線</div>
                <div className="mt-2">時間線 {humanizeLifecycleDiagnosticLabel(executionReconciliation?.lifecycle_timeline?.status || "unknown")} · 總數 {executionReconciliation?.lifecycle_timeline?.total_events ?? timelineEvents.length}</div>
                <div className="mt-1">最新事件 {humanizeRuntimeDetailText(executionReconciliation?.lifecycle_timeline?.latest_event?.event_type || "—")} · {humanizeLifecycleDiagnosticLabel(executionReconciliation?.lifecycle_timeline?.latest_event?.order_state || "unknown")}</div>
                <div className="mt-2 text-slate-400">{timelineEvents.length > 0 ? `${formatTime(timelineEvents[timelineEvents.length - 1]?.timestamp)} · ${humanizeRuntimeDetailText(timelineEvents[timelineEvents.length - 1]?.summary || timelineEvents[timelineEvents.length - 1]?.source || "—")}` : "尚未取得事件時間線。"}</div>
              </div>
            </div>
          </details>
        </div>
      </section>

      <details className={`rounded-[24px] border p-4 ${reconciliationTone}`}>
        <summary className="cursor-pointer list-none text-lg font-semibold text-white">詳細對帳與恢復</summary>
        <div className="mt-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-sm leading-6 text-slate-200">
              {humanizeRuntimeDetailText(executionReconciliation?.summary || "尚未取得對帳摘要。")}
            </div>
          </div>
          <div className="text-right text-xs text-slate-200">
            <div className="font-semibold">{reconciliationStatusLabel}</div>
            <div className="opacity-80">{formatTime(executionReconciliation?.checked_at)}</div>
          </div>
        </div>

        {reconciliationIssues.length > 0 && (
          <div className="mt-4 rounded-2xl border border-amber-500/25 bg-amber-500/10 px-3 py-3 text-sm text-amber-100">
            問題 {reconciliationIssues.join(" · ")}
          </div>
        )}

        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4 text-sm">
          <div className="rounded-[20px] border border-white/10 bg-black/15 p-4">
            <div className="text-[11px] uppercase tracking-wide opacity-70">快照 / 交易對</div>
            <div className="mt-2">新鮮度 {humanizeLifecycleDiagnosticLabel(executionReconciliation?.account_snapshot?.freshness?.status || "unknown")}</div>
            <div>距今 {executionReconciliation?.account_snapshot?.freshness?.age_minutes != null ? `${executionReconciliation.account_snapshot.freshness.age_minutes.toFixed(1)}m` : "—"}</div>
            <div className="mt-2 opacity-80">設定 {executionReconciliation?.symbol_scope?.config_symbol || "—"}</div>
            <div className="opacity-80">請求 {executionReconciliation?.symbol_scope?.requested_symbol || "—"}</div>
            <div className="opacity-80">正規化 {executionReconciliation?.symbol_scope?.normalized_symbol || "—"}</div>
          </div>
          <div className="rounded-[20px] border border-white/10 bg-black/15 p-4">
            <div className="text-[11px] uppercase tracking-wide opacity-70">交易歷史</div>
            <div className="mt-2">狀態 {humanizeLifecycleDiagnosticLabel(executionReconciliation?.trade_history_alignment?.status || "unknown")}</div>
            <div className="opacity-80">原因 {humanizeRuntimeDetailText(executionReconciliation?.trade_history_alignment?.reason || "—")}</div>
            <div className="mt-2 opacity-80">最新成交 {formatTime(executionReconciliation?.trade_history_alignment?.latest_trade?.timestamp)}</div>
            <div className="opacity-80">{executionReconciliation?.trade_history_alignment?.latest_trade?.exchange || "—"} · {executionReconciliation?.trade_history_alignment?.latest_trade?.symbol || "—"}</div>
          </div>
          <div className="rounded-[20px] border border-white/10 bg-black/15 p-4">
                <div className="text-[11px] uppercase tracking-wide opacity-70">掛單</div>
            <div className="mt-2">狀態 {humanizeLifecycleDiagnosticLabel(executionReconciliation?.open_order_alignment?.status || "unknown")}</div>
            <div className="opacity-80">原因 {humanizeRuntimeDetailText(executionReconciliation?.open_order_alignment?.reason || "—")}</div>
            <div className="mt-2 opacity-80">對齊掛單 {executionReconciliation?.open_order_alignment?.matched_open_order?.id || "—"}</div>
            <div className="opacity-80">{executionReconciliation?.open_order_alignment?.matched_open_order?.symbol || "—"} · {humanizeLifecycleDiagnosticLabel(executionReconciliation?.open_order_alignment?.matched_open_order?.status || "unknown")}</div>
          </div>
          <div className="rounded-[20px] border border-white/10 bg-black/15 p-4">
            <div className="text-[11px] uppercase tracking-wide opacity-70">重播</div>
            <div className="mt-2">階段 {humanizeLifecycleDiagnosticLabel(lifecycleAudit?.stage || "unknown")}</div>
            <div className="opacity-80">恢復 {humanizeLifecycleDiagnosticLabel(recoveryState?.status || "unknown")}</div>
            <div className="opacity-80">重播重啟 {humanizeLifecycleDiagnosticLabel(lifecycleAudit?.restart_replay_required ? "required" : "not-required")}</div>
            <div className="mt-2 opacity-80">基線 {humanizeLifecycleDiagnosticLabel(lifecycleContract?.baseline_contract_status || "unknown")}</div>
            <div className="opacity-80">重播結論 {humanizeLifecycleDiagnosticLabel(lifecycleContract?.replay_verdict || "unknown")}</div>
            <div className="opacity-80">產物覆蓋 {humanizeLifecycleDiagnosticLabel(lifecycleContract?.artifact_coverage || "unknown")}</div>
          </div>
        </div>

        <div className="mt-4 rounded-[20px] border border-white/10 bg-black/15 p-4 text-sm text-slate-100">
          <div className="font-semibold">下一步</div>
          <div className="mt-2">{humanizeRuntimeDetailText(recoveryState?.summary || lifecycleContract?.summary || "尚未取得 recovery summary。")}</div>
          <div className="mt-2 text-slate-300">操作建議 {humanizeRuntimeDetailText(recoveryState?.operator_action || lifecycleAudit?.operator_action || "先回 Bot 營運確認目前 run 與資金。")}</div>
          <div className="mt-1 text-slate-400">缺少生命週期事件 {humanizeLifecycleList(lifecycleContract?.missing_event_types, "無")}</div>
          <div className="mt-1 text-slate-400">下一個產物 {humanizeRuntimeDetailText(lifecycleContract?.operator_next_artifact || "—")}</div>
          <div className="mt-1 text-slate-400">執行期委託時間 {lifecycleAudit?.evidence?.runtime_order_timestamp || "—"} · 交易歷史時間 {lifecycleAudit?.evidence?.trade_history_timestamp || "—"}</div>
        </div>

        <div className="mt-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-base font-semibold text-white">場館通道</div>
            <div className="text-xs text-slate-300">{humanizeRuntimeDetailText(lifecycleContract?.venue_lanes_summary || "尚未提供場館通道摘要。")}</div>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {venueLanes.length > 0 ? venueLanes.map((lane, idx) => (
              <div key={`${lane.venue || lane.label || "lane"}-${idx}`} className={`rounded-[20px] border p-4 text-sm ${getStatusTone(lane.status)}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-semibold">{lane.label || lane.venue || `lane ${idx + 1}`}</div>
                  <div>{humanizeLifecycleDiagnosticLabel(lane.status || "unknown")}</div>
                </div>
                <div className="mt-2">{humanizeRuntimeDetailText(lane.summary || "—")}</div>
                <div className="mt-2 text-slate-200">基線 {lane.baseline_observed ?? 0}/{lane.baseline_required ?? 0} · 路徑 {lane.path_observed ?? 0}/{lane.path_expected ?? 0}</div>
                <div className="text-slate-200">重播 {humanizeLifecycleDiagnosticLabel(lane.restart_replay_status || "unknown")}</div>
                <div className="mt-2 text-slate-200">下一個產物 {humanizeRuntimeDetailText(lane.operator_next_artifact || "—")}</div>
              </div>
            )) : (
              <div className="rounded-[20px] border border-white/10 bg-black/15 p-4 text-sm text-slate-300">
                尚未取得場館別閉環通道。
              </div>
            )}
          </div>
        </div>

        <div className="mt-4 rounded-[20px] border border-white/10 bg-black/15 p-4 text-sm text-slate-100">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="font-semibold">時間線</div>
            <div className="text-xs text-slate-300">狀態 {humanizeLifecycleDiagnosticLabel(executionReconciliation?.lifecycle_timeline?.status || "unknown")} · 總數 {executionReconciliation?.lifecycle_timeline?.total_events ?? timelineEvents.length}</div>
          </div>
          <div className="mt-2 text-slate-300">最新事件 {humanizeRuntimeDetailText(executionReconciliation?.lifecycle_timeline?.latest_event?.event_type || "—")} · {humanizeLifecycleDiagnosticLabel(executionReconciliation?.lifecycle_timeline?.latest_event?.order_state || "unknown")}</div>
          <div className="mt-3 space-y-2">
            {timelineEvents.length > 0 ? timelineEvents.slice(-4).map((event, idx) => (
              <div key={`${event.timestamp || "timeline"}-${event.event_type || idx}`} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
                <div>{formatTime(event.timestamp)} · {humanizeRuntimeDetailText(event.event_type || "unknown")} · {humanizeLifecycleDiagnosticLabel(event.order_state || "unknown")}</div>
                <div className="mt-1 text-slate-300">{humanizeRuntimeDetailText(event.summary || event.source || "—")}</div>
              </div>
            )) : (
              <div className="text-slate-300">尚無事件時間線。</div>
            )}
          </div>
        </div>
      </details>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-[24px] border border-white/8 bg-[#151b31] p-4 text-sm text-slate-300">
          <div className="text-lg font-semibold text-white">營運入口</div>
          <div className="mt-2">需要啟停 Bot、看資金使用與執行進度，請回到 Bot 營運。</div>
          <a href="/execution" className="mt-3 inline-flex rounded-xl border border-cyan-400/35 bg-cyan-500/10 px-4 py-2 font-medium text-cyan-100 transition hover:bg-cyan-500/20">
            前往 Bot 營運 →
          </a>
        </div>
        <div className="rounded-[24px] border border-white/8 bg-[#151b31] p-4 text-sm text-slate-300">
          <div className="text-lg font-semibold text-white">策略入口</div>
          <div className="mt-2">需要回頭檢查倉位腿與策略表現，請到策略實驗室。</div>
          <a href="/lab" className="mt-3 inline-flex rounded-xl border border-white/10 bg-white/5 px-4 py-2 font-medium text-slate-100 transition hover:border-cyan-300/35 hover:text-white">
            前往策略實驗室 →
          </a>
        </div>
      </section>
    </div>
  );
}
