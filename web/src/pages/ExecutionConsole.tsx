import { useApi } from "../hooks/useApi";

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

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function formatTime(value?: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("zh-TW");
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

export default function ExecutionConsole() {
  const { data: runtimeStatus, loading, error, refresh: refreshRuntimeStatus } = useApi<ExecutionConsoleRuntimeStatusResponse>("/api/status", 60000);

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

  return (
    <div className="space-y-6 text-dark-100">
      <section className="rounded-2xl border border-white/10 bg-dark-900/80 p-6 shadow-[0_20px_80px_rgba(15,23,42,0.35)]">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="inline-flex items-center rounded-full border border-cyan-400/30 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold tracking-[0.2em] text-cyan-200">
              Execution Console / 實戰交易
            </div>
            <h1 className="mt-3 text-3xl font-semibold text-white">營運視圖已從 Dashboard 分拆</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-dark-300">
              這裡先把 live runtime truth、Sleeve routing / bot activation、account snapshot、Recovery / reconciliation、Metadata / venue readiness 從 Dashboard 拆成獨立營運視圖；
              深度 proof chain / diagnostics 仍保留在 Dashboard。
            </p>
            <div className="mt-3 text-xs text-dark-400">
              {executionSurfaceContract?.operator_message || "尚未取得 execution surface contract operator message。"}
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <button
              type="button"
              onClick={() => refreshRuntimeStatus()}
              className="rounded-lg border border-cyan-400/30 bg-cyan-500/10 px-3 py-2 font-medium text-cyan-100 transition hover:bg-cyan-500/20"
            >
              重新整理 runtime
            </button>
            <a href={diagnosticsSurface?.route || "/"} className="rounded-lg border border-white/10 bg-dark-800 px-3 py-2 font-medium text-dark-100 transition hover:border-cyan-400/40 hover:text-cyan-200">
              前往 Dashboard 診斷 →
            </a>
            <a href="/lab" className="rounded-lg border border-white/10 bg-dark-800 px-3 py-2 font-medium text-dark-100 transition hover:border-cyan-400/40 hover:text-cyan-200">
              前往 Strategy Lab 挑策略 →
            </a>
          </div>
        </div>
        {(loading || error) && (
          <div className="mt-4 rounded-xl border border-white/10 bg-dark-950/60 px-4 py-3 text-sm text-dark-300">
            {loading ? "/api/status 載入中…" : `載入失敗：${error}`}
          </div>
        )}
      </section>

      <section className="grid gap-4 xl:grid-cols-4">
        <div className="rounded-2xl border border-white/10 bg-dark-900/70 p-4">
          <div className="text-xs uppercase tracking-[0.2em] text-dark-500">總資金</div>
          <div className="mt-2 text-2xl font-semibold text-white">{formatNumber(balanceTotal)} {balanceCurrency}</div>
          <div className="mt-1 text-sm text-dark-400">已分配 {formatNumber(allocatedCapital)} · 可用 {formatNumber(balanceFree)}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-dark-900/70 p-4">
          <div className="text-xs uppercase tracking-[0.2em] text-dark-500">Sleeves</div>
          <div className="mt-2 text-2xl font-semibold text-white">{liveRouting?.active_ratio_text || "0/0"}</div>
          <div className="mt-1 text-sm text-dark-400">{liveRouting?.current_regime || liveRuntimeTruth?.regime_label || "—"} · {liveRouting?.current_regime_gate || liveRuntimeTruth?.regime_gate || "—"}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-dark-900/70 p-4">
          <div className="text-xs uppercase tracking-[0.2em] text-dark-500">倉位 / 掛單</div>
          <div className="mt-2 text-2xl font-semibold text-white">{accountSummary?.position_count ?? positions.length} / {accountSummary?.open_order_count ?? openOrders.length}</div>
          <div className="mt-1 text-sm text-dark-400">{accountSummary ? (accountSummary.degraded ? "snapshot degraded" : "snapshot fresh") : "snapshot unavailable"}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-dark-900/70 p-4">
          <div className="text-xs uppercase tracking-[0.2em] text-dark-500">路由 / 準備度</div>
          <div className="mt-2 text-2xl font-semibold text-white">{executionSurfaceContract?.live_ready ? "live-ready" : "not-ready"}</div>
          <div className="mt-1 text-sm text-dark-400">canonical route {executionSurfaceContract?.canonical_execution_route ?? "unknown"}</div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-2xl border border-cyan-400/20 bg-cyan-500/10 p-4 text-sm leading-6 text-cyan-50">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="font-semibold">operations surface</div>
            <div className={`rounded-full border px-2 py-1 text-[11px] ${getStatusTone(operationsSurface?.status)}`}>
              {operationsSurface?.status || "planned"}
            </div>
          </div>
          <div className="mt-2 opacity-90">{operationsSurface?.label || "Execution Console / 實戰交易"} · route {operationsSurface?.route || "/execution"}</div>
          <div className="mt-1 opacity-85">{operationsSurface?.message || "尚未提供 operations surface message。"}</div>
          <div className="mt-2 opacity-75">{operationsSurface?.upgrade_prerequisite || "尚未提供 operator-view 升級前提。"}</div>
          <div className="mt-3 rounded-xl border border-white/10 bg-dark-950/40 p-3 text-[12px] text-cyan-50">
            <div className="font-medium">diagnostics surface</div>
            <div className="mt-1 opacity-90">{diagnosticsSurface?.label || "Dashboard / Execution 狀態面板"} · route {diagnosticsSurface?.route || "/"}</div>
            <div className="mt-1 opacity-80">{diagnosticsSurface?.message || "Dashboard 保留 proof chain / recovery diagnostics。"}</div>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-dark-900/70 p-4 text-sm leading-6 text-dark-200">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="font-semibold">Guardrail / blocker</div>
            <div className={`rounded-full border px-2 py-1 text-[11px] ${getStatusTone(liveRuntimeTruth?.deployment_blocker || liveRuntimeTruth?.execution_guardrail_reason)}`}>
              {liveRuntimeTruth?.deployment_blocker || liveRuntimeTruth?.execution_guardrail_reason || "none"}
            </div>
          </div>
          <div className="mt-2 opacity-90">runtime closure {liveRuntimeTruth?.runtime_closure_state || "—"}</div>
          <div className="mt-1 opacity-80">{liveRuntimeTruth?.runtime_closure_summary || "尚未取得 runtime closure summary。"}</div>
          <div className="mt-2 grid gap-2 md:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-dark-950/40 p-3">
              <div className="text-[11px] uppercase tracking-wide text-dark-500">layers</div>
              <div className="mt-1 font-medium text-white">{liveRuntimeTruth?.allowed_layers_raw ?? "—"} → {liveRuntimeTruth?.allowed_layers ?? "—"}</div>
              <div className="mt-1 text-[12px] opacity-80">raw {liveRuntimeTruth?.allowed_layers_raw_reason || "—"}</div>
              <div className="text-[12px] opacity-80">final {liveRuntimeTruth?.allowed_layers_reason || "—"}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-dark-950/40 p-3">
              <div className="text-[11px] uppercase tracking-wide text-dark-500">support alignment</div>
              <div className="mt-1 font-medium text-white">{liveRuntimeTruth?.support_alignment_status || "unavailable"}</div>
              <div className="mt-1 text-[12px] opacity-80">{liveRuntimeTruth?.support_alignment_summary || "尚未取得 support alignment 摘要。"}</div>
            </div>
          </div>
          {liveReadyBlockers.length > 0 && (
            <div className="mt-3 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-[12px] text-amber-100">
              live blockers: {liveReadyBlockers.join(" · ")}
            </div>
          )}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-2xl border border-white/10 bg-dark-900/70 p-4 text-sm leading-6 text-dark-200">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="font-semibold">Sleeve routing / bot activation</div>
            <div className="text-xs text-dark-400">active sleeves {liveRouting?.active_ratio_text || "0/0"}</div>
          </div>
          <div className="mt-2 text-dark-300">
            {liveRouting?.current_regime || liveRuntimeTruth?.regime_label || "—"} · gate {liveRouting?.current_regime_gate || liveRuntimeTruth?.regime_gate || "—"} · bucket {liveRouting?.current_structure_bucket || liveRuntimeTruth?.structure_bucket || "—"}
          </div>
          <div className="mt-1 text-sm text-dark-400">{liveRouting?.summary || "尚未建立 regime-aware sleeve routing 摘要。"}</div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3">
              <div className="text-[11px] uppercase tracking-wide text-emerald-200">active sleeves</div>
              {liveActiveSleeves.length > 0 ? liveActiveSleeves.map((item) => (
                <div key={item.key || item.label} className="mt-2 rounded-lg border border-emerald-500/20 bg-dark-950/30 px-3 py-2">
                  <div className="font-medium text-emerald-100">{item.label || item.key}</div>
                  <div className="mt-1 text-[12px] text-emerald-50/80">{item.why || "—"}</div>
                </div>
              )) : <div className="mt-2 text-[12px] text-emerald-50/80">目前沒有 active sleeves。</div>}
            </div>
            <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-3">
              <div className="text-[11px] uppercase tracking-wide text-rose-200">inactive sleeves</div>
              {liveInactiveSleeves.length > 0 ? liveInactiveSleeves.map((item) => (
                <div key={item.key || item.label} className="mt-2 rounded-lg border border-rose-500/20 bg-dark-950/30 px-3 py-2">
                  <div className="font-medium text-rose-100">{item.label || item.key}</div>
                  <div className="mt-1 text-[12px] text-rose-50/80">{item.why || "—"}</div>
                </div>
              )) : <div className="mt-2 text-[12px] text-rose-50/80">目前沒有 inactive sleeves。</div>}
            </div>
          </div>
          <div className="mt-3 rounded-xl border border-white/10 bg-dark-950/40 p-3 text-[12px] text-dark-300">
            Execution Console 現在直接消費同一份 runtime sleeve routing；真正缺的不是再做一套規則，而是把 bot profile/run lifecycle 與資金配置接上這份 activation truth。
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-dark-900/70 p-4 text-sm leading-6 text-dark-200">
          <div className="font-semibold">Capital / account snapshot</div>
          <div className="mt-2 text-dark-300">captured {formatTime(accountSummary?.captured_at)}</div>
          <div className="text-dark-400">requested {accountSummary?.requested_symbol || "—"} · normalized {accountSummary?.normalized_symbol || "—"}</div>
          {accountSummary?.operator_message && <div className="mt-2 text-dark-300">{accountSummary.operator_message}</div>}
          {(accountSummary?.recovery_hint || accountSummary?.degraded) && (
            <div className="mt-2 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-[12px] text-amber-100">
              {accountSummary?.recovery_hint || (accountSummary?.degraded ? "account snapshot degraded" : "")}
            </div>
          )}
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-dark-950/40 p-3">
              <div className="text-[11px] uppercase tracking-wide text-dark-500">positions</div>
              <div className="mt-1 font-medium text-white">{accountSummary?.position_count ?? positions.length}</div>
              {(positions.slice(0, 3) as Array<Record<string, unknown>>).map((position, idx) => (
                <div key={idx} className="mt-2 text-[12px] opacity-80">
                  {readRecordString(position, ["symbol", "instId", "market", "pair"]) || "unknown"} · size {formatNumber(readRecordNumber(position, ["contracts", "positionAmt", "size", "sz", "amount"]))}
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-white/10 bg-dark-950/40 p-3">
              <div className="text-[11px] uppercase tracking-wide text-dark-500">open orders</div>
              <div className="mt-1 font-medium text-white">{accountSummary?.open_order_count ?? openOrders.length}</div>
              {(openOrders.slice(0, 3) as Array<Record<string, unknown>>).map((order, idx) => (
                <div key={idx} className="mt-2 text-[12px] opacity-80">
                  {readRecordString(order, ["symbol", "instId", "market", "pair"]) || "unknown"} · qty {formatNumber(readRecordNumber(order, ["amount", "qty", "size", "origQty", "sz"]))}
                </div>
              ))}
            </div>
          </div>
          <div className="mt-3 rounded-xl border border-white/10 bg-dark-950/40 p-3 text-[12px] text-dark-300">
            手動交易 controls 與 bot 資金配置尚未搬到這頁；這輪先把 operator 必須看的 snapshot / route contract / blocker truth 切成獨立營運視圖。
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-2xl border border-white/10 bg-dark-900/70 p-4 text-sm leading-6 text-dark-200">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="font-semibold">Recovery / reconciliation</div>
            <div className={`rounded-full border px-2 py-1 text-[11px] ${getStatusTone(executionReconciliation?.status)}`}>
              {executionReconciliation?.status || "unavailable"}
            </div>
          </div>
          <div className="mt-2 text-dark-300">{executionReconciliation?.summary || "尚未取得 execution reconciliation summary。"}</div>
          <div className="mt-1 text-dark-400">checked {formatTime(executionReconciliation?.checked_at)}</div>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-dark-950/40 p-3">
              <div className="text-[11px] uppercase tracking-wide text-dark-500">lifecycle audit</div>
              <div className="mt-1 font-medium text-white">{lifecycleAudit?.stage || "unknown"}</div>
              <div className="mt-1 text-[12px] opacity-80">runtime → history {lifecycleAudit?.runtime_state || "—"} → {lifecycleAudit?.trade_history_state || "—"}</div>
              <div className="text-[12px] opacity-80">restart replay {lifecycleAudit?.restart_replay_required ? "required" : "not-required"}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-dark-950/40 p-3">
              <div className="text-[11px] uppercase tracking-wide text-dark-500">recovery state</div>
              <div className="mt-1 font-medium text-white">{executionReconciliation?.recovery_state?.status || lifecycleContract?.replay_verdict || "unknown"}</div>
              <div className="mt-1 text-[12px] opacity-80">{executionReconciliation?.recovery_state?.operator_action || lifecycleAudit?.operator_action || "先檢查 Dashboard execution diagnostics。"}</div>
            </div>
          </div>
          <div className="mt-3 rounded-xl border border-white/10 bg-dark-950/40 p-3 text-[12px] text-dark-300">
            lifecycle contract {lifecycleContract?.summary || "—"} · baseline {lifecycleContract?.baseline_contract_status || "—"} · coverage {lifecycleContract?.artifact_coverage || "—"}
          </div>
          {venueLanes.length > 0 && (
            <div className="mt-3 space-y-2">
              {venueLanes.slice(0, 3).map((lane, idx) => (
                <div key={`${lane.venue || "venue"}-${idx}`} className="rounded-xl border border-white/10 bg-dark-950/40 p-3 text-[12px] text-dark-300">
                  <div className="font-medium text-white">{lane.venue || "unknown"} · {lane.restart_replay_status || "unknown"}</div>
                  <div className="mt-1">{lane.summary || lane.operator_action_summary || "尚無 lane summary。"}</div>
                  <div className="mt-1 opacity-80">remediation {lane.remediation_priority || "—"} · {lane.remediation_focus || "—"}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-white/10 bg-dark-900/70 p-4 text-sm leading-6 text-dark-200">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="font-semibold">Metadata / venue readiness</div>
            <div className={`rounded-full border px-2 py-1 text-[11px] ${getStatusTone(metadataSmokeFreshness?.status || metadataSmokeGovernance?.status)}`}>
              {metadataSmokeFreshness?.label || metadataSmokeFreshness?.status || metadataSmokeGovernance?.status || "unavailable"}
            </div>
          </div>
          <div className="mt-2 text-dark-300">generated {formatTime(metadataSmoke?.generated_at)}</div>
          <div className="text-dark-400">artifact age {metadataSmokeFreshness?.age_minutes != null ? `${metadataSmokeFreshness.age_minutes.toFixed(1)} 分鐘` : "—"}</div>
          <div className="mt-2 text-dark-300">{metadataSmokeGovernance?.operator_message || "尚未取得 metadata governance message。"}</div>
          {metadataSmokeGovernance?.escalation_message && (
            <div className="mt-2 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-[12px] text-amber-100">
              {metadataSmokeGovernance.escalation_message}
            </div>
          )}
          <div className="mt-3 space-y-2">
            {venueChecks.length > 0 ? venueChecks.map((item) => (
              <div key={item.venue || "unknown"} className="rounded-xl border border-white/10 bg-dark-950/40 p-3 text-[12px] text-dark-300">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-medium text-white">{item.venue || "unknown"}</div>
                  <div className={item.ok ? "text-emerald-300" : "text-rose-300"}>{item.ok ? "OK" : "FAIL"}</div>
                </div>
                <div className="mt-1">config {item.enabled_in_config ? "enabled" : "disabled"} · creds {item.credentials_configured ? "configured" : "public-only"}</div>
                <div className="opacity-80">step {String(item.contract?.step_size ?? "—")} · tick {String(item.contract?.tick_size ?? "—")}</div>
                <div className="opacity-80">min qty {String(item.contract?.min_qty ?? "—")} · min cost {String(item.contract?.min_cost ?? "—")}</div>
                {item.error && <div className="mt-1 text-rose-300">{item.error}</div>}
              </div>
            )) : <div className="rounded-xl border border-white/10 bg-dark-950/40 p-3 text-[12px] text-dark-300">尚未取得 venue metadata smoke。</div>}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-white/10 bg-dark-900/70 p-4 text-sm leading-6 text-dark-200">
        <div className="font-semibold">最近委託 / reject / failure</div>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-white/10 bg-dark-950/40 p-3">
            <div className="text-[11px] uppercase tracking-wide text-dark-500">last order</div>
            <div className="mt-1 font-medium text-white">{lastOrder?.side || "—"} · {lastOrder?.status || "—"}</div>
            <div className="mt-1 text-[12px] opacity-80">{lastOrder?.venue || executionSummary?.venue || "—"} · {lastOrder?.symbol || runtimeStatus?.symbol || "—"}</div>
            <div className="text-[12px] opacity-80">qty {formatNumber(lastOrder?.qty)} · price {formatNumber(lastOrder?.price)}</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-dark-950/40 p-3">
            <div className="text-[11px] uppercase tracking-wide text-dark-500">last reject</div>
            <div className="mt-1 font-medium text-white">{lastReject?.code || "none"}</div>
            <div className="mt-1 text-[12px] opacity-80">{lastReject?.message || "尚無最近 reject。"}</div>
            <div className="text-[12px] opacity-80">{formatTime(lastReject?.timestamp)}</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-dark-950/40 p-3">
            <div className="text-[11px] uppercase tracking-wide text-dark-500">last failure</div>
            <div className="mt-1 font-medium text-white">{lastFailure?.message || "none"}</div>
            <div className="mt-1 text-[12px] opacity-80">{formatTime(lastFailure?.timestamp)}</div>
            <div className="text-[12px] opacity-80">kill switch {guardrails?.kill_switch ? "on" : "off"} · failure halt {guardrails?.failure_halt ? "on" : "off"}</div>
          </div>
        </div>
      </section>
    </div>
  );
}
