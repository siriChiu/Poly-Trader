type MetadataFreshness = {
  status?: string;
  label?: string;
  age_minutes?: number | null;
  stale_after_minutes?: number | null;
} | null;

type MetadataGovernance = {
  status?: string;
  operator_message?: string;
  escalation_message?: string | null;
  external_monitor?: {
    status?: string;
    reason?: string;
    install_contract?: {
      preferred_host_lane?: string;
      install_status?: {
        active_lane?: string | null;
      } | null;
    } | null;
    ticking_state?: {
      status?: string;
      reason?: string;
      message?: string;
      active_lane?: string | null;
    } | null;
  } | null;
} | null;

type ExecutionMetadataFreshnessDetailProps = {
  pending?: boolean;
  generatedAt?: string | null;
  freshness?: MetadataFreshness;
  governance?: MetadataGovernance;
  compact?: boolean;
};

function formatTime(value?: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("zh-TW");
}

function buildHostSchedulerSummary(governance?: MetadataGovernance): string | null {
  const externalMonitor = governance?.external_monitor ?? null;
  const tickingState = externalMonitor?.ticking_state ?? null;
  const activeLane = tickingState?.active_lane
    || externalMonitor?.install_contract?.install_status?.active_lane
    || externalMonitor?.install_contract?.preferred_host_lane
    || null;
  const stateLabel = tickingState?.status || externalMonitor?.status || null;
  const message = tickingState?.message || tickingState?.reason || externalMonitor?.reason || null;
  if (!activeLane && !stateLabel && !message) {
    return null;
  }
  return [
    stateLabel ? `host scheduler ${stateLabel}` : null,
    activeLane ? `lane ${activeLane}` : null,
    message,
  ].filter(Boolean).join(" · ");
}

export default function ExecutionMetadataFreshnessDetail({
  pending = false,
  generatedAt,
  freshness,
  governance,
  compact = false,
}: ExecutionMetadataFreshnessDetailProps) {
  if (pending) {
    return <div>正在向 /api/status 取得 metadata smoke。</div>;
  }

  const generatedLine = [
    `generated ${formatTime(generatedAt)}`,
    freshness?.age_minutes != null ? `age ${freshness.age_minutes.toFixed(1)} 分鐘` : null,
  ].filter(Boolean).join(" · ");
  const governanceLine = governance?.operator_message || "尚未取得 governance 訊息。";
  const hostSchedulerSummary = buildHostSchedulerSummary(governance);
  const lines = [
    generatedLine,
    governanceLine,
    hostSchedulerSummary ? `external monitor ${hostSchedulerSummary}` : null,
    governance?.escalation_message ? `escalation ${governance.escalation_message}` : null,
  ].filter(Boolean) as string[];

  return (
    <div className={compact ? "space-y-1 text-[11px] leading-5" : "space-y-1 leading-6"}>
      {lines.map((line) => (
        <div key={line}>{line}</div>
      ))}
    </div>
  );
}
