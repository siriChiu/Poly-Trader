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

function humanizeMetadataGovernanceText(value?: string | null): string | null {
  const normalized = String(value || "").trim();
  if (!normalized) return null;
  return normalized
    .split("metadata smoke artifact").join("元資料檢查產物")
    .split("external monitor artifact").join("外部監看產物")
    .split("freshness policy").join("新鮮度規則")
    .split("host scheduler").join("主機排程")
    .split("installed-but-not-ticking").join("已安裝但尚未觀察到自然排程觸發")
    .split("observed-ticking").join("已觀察到自然排程觸發")
    .split("installed_but_artifact_not_fresh").join("已安裝但產物未維持新鮮")
    .split("未維持 fresh").join("未維持新鮮")
    .split("ticking").join("排程觸發")
    .replace(/\s+/g, " ")
    .trim();
}

function humanizeHostSchedulerState(value?: string | null): string | null {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) return null;
  const mapping: Record<string, string> = {
    "observed-ticking": "已觀察到自然排程觸發",
    "installed-but-not-ticking": "已安裝但尚未觀察到自然排程觸發",
    installed: "已安裝",
    "install-ready": "可安裝",
    pending: "等待中",
    stale: "已過期",
    fresh: "新鮮",
  };
  return mapping[normalized] || value || null;
}

function humanizeHostSchedulerLane(value?: string | null): string | null {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) return null;
  const mapping: Record<string, string> = {
    user_crontab: "使用者 crontab",
    systemd_user: "systemd user",
    fallback: "後備命令",
  };
  return mapping[normalized] || value || null;
}

function buildHostSchedulerSummary(governance?: MetadataGovernance): string | null {
  const externalMonitor = governance?.external_monitor ?? null;
  const tickingState = externalMonitor?.ticking_state ?? null;
  const activeLane = humanizeHostSchedulerLane(
    tickingState?.active_lane
    || externalMonitor?.install_contract?.install_status?.active_lane
    || externalMonitor?.install_contract?.preferred_host_lane
    || null,
  );
  const stateLabel = humanizeHostSchedulerState(tickingState?.status || externalMonitor?.status || null);
  const message = humanizeMetadataGovernanceText(
    tickingState?.message || tickingState?.reason || externalMonitor?.reason || null,
  );
  if (!activeLane && !stateLabel && !message) {
    return null;
  }
  return [
    stateLabel ? `主機排程 ${stateLabel}` : null,
    activeLane ? `路徑 ${activeLane}` : null,
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
    return <div>正在向 /api/status 取得元資料檢查。</div>;
  }

  const generatedLine = [
    `生成於 ${formatTime(generatedAt)}`,
    freshness?.age_minutes != null ? `距今 ${freshness.age_minutes.toFixed(1)} 分鐘` : null,
  ].filter(Boolean).join(" · ");
  const governanceLine = humanizeMetadataGovernanceText(governance?.operator_message || "尚未取得治理訊息。") || "尚未取得治理訊息。";
  const hostSchedulerSummary = buildHostSchedulerSummary(governance);
  const lines = [
    generatedLine,
    governanceLine,
    hostSchedulerSummary ? `外部監看 ${hostSchedulerSummary}` : null,
    governance?.escalation_message ? `升級建議 ${humanizeMetadataGovernanceText(governance.escalation_message) || governance.escalation_message}` : null,
  ].filter(Boolean) as string[];

  return (
    <div className={compact ? "space-y-1 text-[11px] leading-5" : "space-y-1 leading-6"}>
      {lines.map((line) => (
        <div key={line}>{line}</div>
      ))}
    </div>
  );
}
