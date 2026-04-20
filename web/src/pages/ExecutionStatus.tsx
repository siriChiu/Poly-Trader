import { useMemo } from "react";
import VenueReadinessSummary from "../components/VenueReadinessSummary";
import { useApi } from "../hooks/useApi";
import { ExecutionHero, ExecutionMetricCard, ExecutionPill, ExecutionSectionCard } from "../components/execution/ExecutionSurface";

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

function summarizePreviewRecords(records?: PreviewRecord[] | null): string {
  if (!Array.isArray(records) || records.length === 0) return "none";
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
    ? "public-only / metadata only"
    : "balance unavailable";
  const accountBalanceUnavailableReason = !accountCredentialsConfigured
    ? "private balance unavailable until exchange credentials are configured"
    : "balance unavailable in latest account snapshot";
  const accountBalanceSummaryValue = balanceTotal !== null
    ? `${formatNumber(balanceTotal)} ${balanceCurrency}`
    : accountBalanceUnavailableLabel;
  const accountBalanceSummaryFree = balanceFree !== null
    ? `free ${balanceFree.toFixed(2)} ${balanceCurrency}`
    : accountBalanceUnavailableReason;
  const readinessTone = getStatusTone(executionSurfaceContract?.live_ready ? "ready" : liveRuntimeTruth?.deployment_blocker || "blocked");
  const metadataTone = getStatusTone(metadataFreshness?.status);
  const reconciliationTone = getStatusTone(executionReconciliation?.status);
  const healthTone = getStatusTone(accountSummary?.degraded ? "degraded" : accountSummary?.health?.connected ? "connected" : "warning");

  const currentLiveBlocker = liveRuntimeTruth?.deployment_blocker || null;
  const primaryRuntimeMessage = runtimeStatusPending
    ? "正在同步 /api/status"
    : (liveRuntimeTruth?.deployment_blocker_reason
      || liveRuntimeTruth?.deployment_blocker
      || liveRuntimeTruth?.execution_guardrail_reason
      || liveReadyBlockers[0]
      || executionSurfaceContract?.operator_message
      || "目前沒有額外 blocker 摘要。");
  const currentLiveBlockerLabel = runtimeStatusPending ? "同步中" : (currentLiveBlocker || "unavailable");
  const metadataFreshnessLabel = runtimeStatusPending
    ? "同步中"
    : (metadataFreshness?.label || metadataFreshness?.status || "unavailable");
  const reconciliationStatusLabel = runtimeStatusPending ? "同步中" : (executionReconciliation?.status || "unavailable");
  const supportAlignmentLabel = runtimeStatusPending ? "同步中" : (liveRuntimeTruth?.support_alignment_status || "unavailable");
  const venueBlockersLabel = runtimeStatusPending
    ? "同步中"
    : (liveReadyBlockers.length > 0 ? liveReadyBlockers.join(" · ") : "none");

  const lifecycleSummary = useMemo(() => {
    return [
      `stage ${lifecycleAudit?.stage || "unknown"}`,
      `replay ${lifecycleContract?.replay_verdict || (lifecycleAudit?.restart_replay_required ? "required" : "not-required")}`,
      `coverage ${lifecycleContract?.artifact_coverage || "unknown"}`,
    ].join(" · ");
  }, [lifecycleAudit, lifecycleContract]);

  return (
    <div className="execution-shell app-page-shell text-white">
      <ExecutionHero
        className="app-page-header"
        eyebrow="執行狀態 / Diagnostics"
        title="先看 blocker，再決定是否介入"
        subtitle="這頁只保留執行診斷：可部署、資料新鮮度、對帳與恢復。"
        statusPills={(
          <>
            <ExecutionPill>{runtimeStatus?.symbol || "BTCUSDT"}</ExecutionPill>
            <ExecutionPill>{executionSummary?.mode || (runtimeStatus?.dry_run ? "dry_run" : "unknown")}</ExecutionPill>
            <ExecutionPill>{executionSummary?.venue || "unknown"}</ExecutionPill>
            <ExecutionPill className={getStatusTone(runtimeStatus?.automation ? "ok" : "warning")}>
              automation {runtimeStatus?.automation ? "ON" : "OFF"}
            </ExecutionPill>
            <ExecutionPill className={readinessTone}>
              {executionSurfaceContract?.live_ready ? "可部署" : "仍阻塞"}
            </ExecutionPill>
            <ExecutionPill className={metadataTone}>
              freshness {metadataFreshnessLabel}
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

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <ExecutionMetricCard
            title="可部署"
            value={executionSurfaceContract?.live_ready ? "可進場" : "仍阻塞"}
            detail={`blocker ${currentLiveBlockerLabel} · ${primaryRuntimeMessage} · scope ${executionSurfaceContract?.readiness_scope || "runtime_governance_visibility_only"}`}
            toneClass={readinessTone.includes("amber") ? "text-amber-100" : readinessTone.includes("emerald") || readinessTone.includes("cyan") ? "text-emerald-200" : "text-white"}
          />
          <ExecutionMetricCard
            title="資料新鮮度"
            value={metadataFreshnessLabel}
            detail={runtimeStatusPending
              ? "正在向 /api/status 取得 metadata smoke。"
              : `generated ${formatTime(metadataSmoke?.generated_at)} · age ${metadataFreshness?.age_minutes != null ? `${metadataFreshness.age_minutes.toFixed(1)} 分鐘` : "—"}`}
            toneClass={metadataTone.includes("amber") ? "text-amber-100" : metadataTone.includes("emerald") || metadataTone.includes("cyan") ? "text-emerald-200" : "text-white"}
          />
          <ExecutionMetricCard
            title="對帳狀態"
            value={reconciliationStatusLabel}
            detail={runtimeStatusPending
              ? "正在向 /api/status 取得 reconciliation / recovery 摘要。"
              : `${executionReconciliation?.summary || "尚未取得 reconciliation 摘要。"} · ${lifecycleSummary}`}
            toneClass={reconciliationTone.includes("rose") ? "text-rose-200" : reconciliationTone.includes("amber") ? "text-amber-100" : "text-white"}
          />
          <ExecutionMetricCard
            title="帳戶快照"
            value={accountBalanceSummaryValue}
            detail={`${accountBalanceSummaryFree} · 倉位 ${accountSummary?.position_count ?? positions.length} · 掛單 ${accountSummary?.open_order_count ?? openOrders.length}`}
            toneClass={healthTone.includes("rose") ? "text-rose-200" : healthTone.includes("amber") ? "text-amber-100" : "text-white"}
          />
        </div>
      </ExecutionHero>

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="space-y-4">
          <ExecutionSectionCard
            title="部署診斷"
            subtitle={liveRuntimeTruth?.runtime_closure_summary || primaryRuntimeMessage}
            aside={(
              <div className={`rounded-full border px-2.5 py-1 text-[11px] ${readinessTone}`}>
                {liveRuntimeTruth?.runtime_closure_state || (executionSurfaceContract?.live_ready ? "ready" : "blocked")}
              </div>
            )}
          >
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">主 blocker</div>
                <div className="mt-2 font-semibold text-white">{primaryRuntimeMessage}</div>
                <div className="mt-2 text-slate-400">deployment blocker {runtimeStatusPending ? "同步中" : (liveRuntimeTruth?.deployment_blocker || "none")}</div>
                <div className="text-slate-400">execution guardrail {liveRuntimeTruth?.execution_guardrail_reason || "none"}</div>
                <div className="text-slate-400">venue blockers {venueBlockersLabel}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">部署計算</div>
                <div className="mt-2 font-semibold text-white">layers {liveRuntimeTruth?.allowed_layers_raw ?? "—"} → {liveRuntimeTruth?.allowed_layers ?? "—"}</div>
                <div className="mt-2 text-slate-400">raw reason {liveRuntimeTruth?.allowed_layers_raw_reason || "—"}</div>
                <div className="text-slate-400">final reason {liveRuntimeTruth?.allowed_layers_reason || "—"}</div>
                <div className="mt-2 text-slate-400">support {liveRuntimeTruth?.support_rows_text || `${liveRuntimeTruth?.runtime_exact_support_rows ?? "—"} / ${liveRuntimeTruth?.calibration_exact_lane_rows ?? "—"}`}</div>
                <div className="text-slate-400">alignment {supportAlignmentLabel}</div>
              </div>
            </div>

            <div className="mt-4 rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-semibold text-white">市場路由</div>
                <div className="text-[11px] text-slate-400">active sleeves {liveRouting?.active_ratio_text || "0/0"}</div>
              </div>
              <div className="mt-2 text-slate-300">
                {liveRouting?.current_regime || liveRuntimeTruth?.regime_label || "—"} · gate {liveRouting?.current_regime_gate || liveRuntimeTruth?.regime_gate || "—"} · bucket {liveRouting?.current_structure_bucket || liveRuntimeTruth?.structure_bucket || "—"}
              </div>
              <div className="mt-2 text-sm text-slate-400">{liveRouting?.summary || liveRuntimeTruth?.support_alignment_summary || "尚未取得 sleeve routing 摘要。"}</div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
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
            </div>
          </ExecutionSectionCard>

          <section className="rounded-[24px] border border-white/8 bg-[#151b31] p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-lg font-semibold text-white">帳戶快照</div>
                <div className="mt-1 text-sm text-slate-400">captured {formatTime(accountSummary?.captured_at)} · {accountSummary?.requested_symbol || "—"} → {accountSummary?.normalized_symbol || "—"}</div>
              </div>
              <div className={`rounded-full border px-2.5 py-1 text-[11px] ${healthTone}`}>
                {accountSummary?.degraded ? "degraded" : accountSummary?.health?.connected ? "connected" : "review"}
              </div>
            </div>

            {(accountSummary?.operator_message || accountSummary?.recovery_hint || accountSummary?.health?.error) && (
              <div className="mt-3 rounded-2xl border border-white/8 bg-white/5 px-3 py-2 text-sm text-slate-300">
                {accountSummary?.operator_message || accountSummary?.recovery_hint || accountSummary?.health?.error}
              </div>
            )}

            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">Balance</div>
                <div className="mt-2 font-semibold text-white">{accountBalanceSummaryValue}</div>
                <div className="mt-2 text-slate-400">{accountBalanceSummaryFree}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">Positions</div>
                <div className="mt-2 font-semibold text-white">{accountSummary?.position_count ?? positions.length}</div>
                <div className="mt-2 text-slate-400">{summarizePreviewRecords(positions.slice(0, 2))}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">Open orders</div>
                <div className="mt-2 font-semibold text-white">{accountSummary?.open_order_count ?? openOrders.length}</div>
                <div className="mt-2 text-slate-400">{summarizePreviewRecords(openOrders.slice(0, 2))}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">Guardrails</div>
                <div className="mt-2 font-semibold text-white">daily {formatPercent(guardrails?.daily_loss_ratio, 2)}</div>
                <div className="mt-2 text-slate-400">limit {formatPercent(guardrails?.max_daily_loss_pct, 1)}</div>
                <div className="text-slate-400">failures {guardrails?.consecutive_failures ?? 0}/{guardrails?.max_consecutive_failures ?? 0}</div>
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">最近委託</div>
                <div className="mt-2 font-semibold text-white">{lastOrder?.side || "—"} · {lastOrder?.status || "—"}</div>
                <div className="mt-2 text-slate-400">qty {formatNumber(lastOrder?.qty)} · price {formatNumber(lastOrder?.price)}</div>
                <div className="text-slate-400">{lastOrder?.order_id || lastOrder?.client_order_id || "尚無 order id"}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">最近拒單</div>
                <div className="mt-2 font-semibold text-white">{lastReject?.code || "none"}</div>
                <div className="mt-2 text-slate-400">{lastReject?.message || "尚無拒單紀錄"}</div>
                <div className="text-slate-400">{formatTime(lastReject?.timestamp)}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4 text-sm">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">最近失敗</div>
                <div className="mt-2 font-semibold text-white">{lastFailure?.message || "none"}</div>
                <div className="mt-2 text-slate-400">{formatTime(lastFailure?.timestamp)}</div>
                <div className="text-slate-400">kill switch {guardrails?.kill_switch ? "ON" : "off"}</div>
              </div>
            </div>
          </section>
        </div>

        <div className="space-y-4">
          <section className="rounded-[24px] border border-white/8 bg-[#151b31] p-4">
            <div className="text-lg font-semibold text-white">場館狀態</div>
            <div className="mt-1 text-sm text-slate-400">generated {formatTime(metadataSmoke?.generated_at)} · governance {metadataGovernance?.status || "unknown"}</div>
            <div className={`mt-3 rounded-2xl border px-3 py-3 text-sm ${metadataTone}`}>
              <div className="font-semibold">freshness {metadataFreshnessLabel}</div>
              <div className="mt-1">artifact age {metadataFreshness?.age_minutes != null ? `${metadataFreshness.age_minutes.toFixed(1)} 分鐘` : "—"}</div>
              <div className="mt-2 opacity-90">{metadataGovernance?.operator_message || "尚未取得 governance 訊息。"}</div>
              {metadataGovernance?.escalation_message && (
                <div className="mt-2 opacity-80">escalation {metadataGovernance.escalation_message}</div>
              )}
            </div>

            <VenueReadinessSummary venues={venueChecks} className="mt-4" />
          </section>

          <details className="execution-card">
            <summary className="cursor-pointer list-none text-lg font-semibold text-white">進階診斷（需要時再展開）</summary>
            <div className="mt-4 space-y-3 text-sm text-slate-300">
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">Surface contract</div>
                <div className="mt-2">canonical route {executionSurfaceContract?.canonical_execution_route || "unknown"}</div>
                <div className="mt-1">canonical surface {executionSurfaceContract?.canonical_surface_label || diagnosticsSurface?.label || "Execution 狀態"}</div>
                <div className="mt-1">operations {operationsSurface?.label || "Bot 營運"} · {operationsSurface?.route || "/execution"}</div>
                <div className="mt-1">diagnostics {diagnosticsSurface?.label || "Execution 狀態"} · {diagnosticsSurface?.route || "/execution/status"}</div>
                <div className="mt-1">shortcut {executionSurfaceContract?.shortcut_surface?.name || "signal_banner"} · {executionSurfaceContract?.shortcut_surface?.status || "available"}</div>
              </div>
              <div className="rounded-[20px] border border-white/8 bg-[#0f1528] p-4">
                <div className="text-[11px] uppercase tracking-wide text-slate-500">Latest timeline</div>
                <div className="mt-2">timeline {executionReconciliation?.lifecycle_timeline?.status || "unknown"} · total {executionReconciliation?.lifecycle_timeline?.total_events ?? timelineEvents.length}</div>
                <div className="mt-1">latest {executionReconciliation?.lifecycle_timeline?.latest_event?.event_type || "—"} · {executionReconciliation?.lifecycle_timeline?.latest_event?.order_state || "—"}</div>
                <div className="mt-2 text-slate-400">{timelineEvents.length > 0 ? `${formatTime(timelineEvents[timelineEvents.length - 1]?.timestamp)} · ${timelineEvents[timelineEvents.length - 1]?.summary || timelineEvents[timelineEvents.length - 1]?.source || "—"}` : "尚未取得 lifecycle timeline。"}</div>
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
              {executionReconciliation?.summary || "尚未取得 reconciliation 摘要。"}
            </div>
          </div>
          <div className="text-right text-xs text-slate-200">
            <div className="font-semibold">{reconciliationStatusLabel}</div>
            <div className="opacity-80">{formatTime(executionReconciliation?.checked_at)}</div>
          </div>
        </div>

        {reconciliationIssues.length > 0 && (
          <div className="mt-4 rounded-2xl border border-amber-500/25 bg-amber-500/10 px-3 py-3 text-sm text-amber-100">
            issues {reconciliationIssues.join(" · ")}
          </div>
        )}

        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4 text-sm">
          <div className="rounded-[20px] border border-white/10 bg-black/15 p-4">
            <div className="text-[11px] uppercase tracking-wide opacity-70">Snapshot / symbol</div>
            <div className="mt-2">freshness {executionReconciliation?.account_snapshot?.freshness?.status || "unknown"}</div>
            <div>age {executionReconciliation?.account_snapshot?.freshness?.age_minutes != null ? `${executionReconciliation.account_snapshot.freshness.age_minutes.toFixed(1)}m` : "—"}</div>
            <div className="mt-2 opacity-80">config {executionReconciliation?.symbol_scope?.config_symbol || "—"}</div>
            <div className="opacity-80">requested {executionReconciliation?.symbol_scope?.requested_symbol || "—"}</div>
            <div className="opacity-80">normalized {executionReconciliation?.symbol_scope?.normalized_symbol || "—"}</div>
          </div>
          <div className="rounded-[20px] border border-white/10 bg-black/15 p-4">
            <div className="text-[11px] uppercase tracking-wide opacity-70">Trade history</div>
            <div className="mt-2">status {executionReconciliation?.trade_history_alignment?.status || "unknown"}</div>
            <div className="opacity-80">reason {executionReconciliation?.trade_history_alignment?.reason || "—"}</div>
            <div className="mt-2 opacity-80">latest trade {formatTime(executionReconciliation?.trade_history_alignment?.latest_trade?.timestamp)}</div>
            <div className="opacity-80">{executionReconciliation?.trade_history_alignment?.latest_trade?.exchange || "—"} · {executionReconciliation?.trade_history_alignment?.latest_trade?.symbol || "—"}</div>
          </div>
          <div className="rounded-[20px] border border-white/10 bg-black/15 p-4">
            <div className="text-[11px] uppercase tracking-wide opacity-70">Open orders</div>
            <div className="mt-2">status {executionReconciliation?.open_order_alignment?.status || "unknown"}</div>
            <div className="opacity-80">reason {executionReconciliation?.open_order_alignment?.reason || "—"}</div>
            <div className="mt-2 opacity-80">matched {executionReconciliation?.open_order_alignment?.matched_open_order?.id || "—"}</div>
            <div className="opacity-80">{executionReconciliation?.open_order_alignment?.matched_open_order?.symbol || "—"} · {executionReconciliation?.open_order_alignment?.matched_open_order?.status || "—"}</div>
          </div>
          <div className="rounded-[20px] border border-white/10 bg-black/15 p-4">
            <div className="text-[11px] uppercase tracking-wide opacity-70">Replay</div>
            <div className="mt-2">stage {lifecycleAudit?.stage || "unknown"}</div>
            <div className="opacity-80">recovery {recoveryState?.status || "unknown"}</div>
            <div className="opacity-80">restart replay {lifecycleAudit?.restart_replay_required ? "required" : "not-required"}</div>
            <div className="mt-2 opacity-80">baseline {lifecycleContract?.baseline_contract_status || "unknown"}</div>
            <div className="opacity-80">replay verdict {lifecycleContract?.replay_verdict || "unknown"}</div>
            <div className="opacity-80">artifact coverage {lifecycleContract?.artifact_coverage || "unknown"}</div>
          </div>
        </div>

        <div className="mt-4 rounded-[20px] border border-white/10 bg-black/15 p-4 text-sm text-slate-100">
          <div className="font-semibold">下一步</div>
          <div className="mt-2">{recoveryState?.summary || lifecycleContract?.summary || "尚未取得 recovery summary。"}</div>
          <div className="mt-2 text-slate-300">operator action {recoveryState?.operator_action || lifecycleAudit?.operator_action || "先回 Bot 營運確認目前 run 與資金。"}</div>
          <div className="mt-1 text-slate-400">missing lifecycle events {(lifecycleContract?.missing_event_types || []).join(" / ") || "none"}</div>
          <div className="mt-1 text-slate-400">next artifact {lifecycleContract?.operator_next_artifact || "—"}</div>
          <div className="mt-1 text-slate-400">runtime order ts {lifecycleAudit?.evidence?.runtime_order_timestamp || "—"} · trade history ts {lifecycleAudit?.evidence?.trade_history_timestamp || "—"}</div>
        </div>

        <div className="mt-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-base font-semibold text-white">Venue lanes</div>
            <div className="text-xs text-slate-300">{lifecycleContract?.venue_lanes_summary || "尚未提供 venue lane 摘要。"}</div>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {venueLanes.length > 0 ? venueLanes.map((lane, idx) => (
              <div key={`${lane.venue || lane.label || "lane"}-${idx}`} className={`rounded-[20px] border p-4 text-sm ${getStatusTone(lane.status)}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-semibold">{lane.label || lane.venue || `lane ${idx + 1}`}</div>
                  <div>{lane.status || "unknown"}</div>
                </div>
                <div className="mt-2">{lane.summary || "—"}</div>
                <div className="mt-2 text-slate-200">baseline {lane.baseline_observed ?? 0}/{lane.baseline_required ?? 0} · path {lane.path_observed ?? 0}/{lane.path_expected ?? 0}</div>
                <div className="text-slate-200">replay {lane.restart_replay_status || "—"}</div>
                <div className="mt-2 text-slate-200">next artifact {lane.operator_next_artifact || "—"}</div>
              </div>
            )) : (
              <div className="rounded-[20px] border border-white/10 bg-black/15 p-4 text-sm text-slate-300">
                尚未取得 venue-specific closure lanes。
              </div>
            )}
          </div>
        </div>

        <div className="mt-4 rounded-[20px] border border-white/10 bg-black/15 p-4 text-sm text-slate-100">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="font-semibold">Timeline</div>
            <div className="text-xs text-slate-300">status {executionReconciliation?.lifecycle_timeline?.status || "unknown"} · total {executionReconciliation?.lifecycle_timeline?.total_events ?? timelineEvents.length}</div>
          </div>
          <div className="mt-2 text-slate-300">latest event {executionReconciliation?.lifecycle_timeline?.latest_event?.event_type || "—"} · {executionReconciliation?.lifecycle_timeline?.latest_event?.order_state || "—"}</div>
          <div className="mt-3 space-y-2">
            {timelineEvents.length > 0 ? timelineEvents.slice(-4).map((event, idx) => (
              <div key={`${event.timestamp || "timeline"}-${event.event_type || idx}`} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
                <div>{formatTime(event.timestamp)} · {event.event_type || "unknown"} · {event.order_state || "—"}</div>
                <div className="mt-1 text-slate-300">{event.summary || event.source || "—"}</div>
              </div>
            )) : (
              <div className="text-slate-300">尚無 lifecycle timeline。</div>
            )}
          </div>
        </div>
      </details>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-[24px] border border-white/8 bg-[#151b31] p-4 text-sm text-slate-300">
          <div className="text-lg font-semibold text-white">營運入口</div>
          <div className="mt-2">需要啟停 Bot、看資金使用與 run 進度，請回到 Bot 營運。</div>
          <a href="/execution" className="mt-3 inline-flex rounded-xl border border-cyan-400/35 bg-cyan-500/10 px-4 py-2 font-medium text-cyan-100 transition hover:bg-cyan-500/20">
            前往 Bot 營運 →
          </a>
        </div>
        <div className="rounded-[24px] border border-white/8 bg-[#151b31] p-4 text-sm text-slate-300">
          <div className="text-lg font-semibold text-white">策略入口</div>
          <div className="mt-2">需要回頭檢查 sleeve 與策略表現，請到策略實驗室。</div>
          <a href="/lab" className="mt-3 inline-flex rounded-xl border border-white/10 bg-white/5 px-4 py-2 font-medium text-slate-100 transition hover:border-cyan-300/35 hover:text-white">
            前往策略實驗室 →
          </a>
        </div>
      </section>
    </div>
  );
}
