type VenueReadinessItem = {
  venue?: string;
  ok?: boolean;
  enabled_in_config?: boolean;
  credentials_configured?: boolean;
  error?: string | null;
  blockers?: string[] | null;
  contract?: {
    step_size?: string | number | null;
    tick_size?: string | number | null;
    min_qty?: number | null;
    min_cost?: number | null;
  } | null;
};

type VenueReadinessSummaryProps = {
  venues?: VenueReadinessItem[] | null;
  className?: string;
  compact?: boolean;
};

const readinessTone = (item: VenueReadinessItem) => {
  if (!item.ok) return "border-rose-500/30 bg-rose-500/10 text-rose-100";
  if (item.enabled_in_config && item.credentials_configured) return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
  if (item.enabled_in_config) return "border-amber-500/30 bg-amber-500/10 text-amber-100";
  return "border-slate-500/30 bg-slate-500/10 text-slate-200";
};

const readinessLabel = (item: VenueReadinessItem) => {
  if (!item.ok) return "metadata contract failed";
  if (item.enabled_in_config && item.credentials_configured) return "credentials configured / runtime proof pending";
  if (item.enabled_in_config) return "public-only metadata lane";
  return "disabled venue / metadata only";
};

const readinessBadgeLabel = (item: VenueReadinessItem) => {
  if (!item.ok) return "METADATA-FAIL";
  if (item.enabled_in_config && item.credentials_configured) return "CONFIGURED";
  if (item.enabled_in_config) return "READ-ONLY";
  return "DISABLED";
};

function formatScalar(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export default function VenueReadinessSummary({ venues, className = "", compact = false }: VenueReadinessSummaryProps) {
  if (!venues || venues.length === 0) {
    return null;
  }

  return (
    <div className={`grid gap-2 ${compact ? "grid-cols-1" : "md:grid-cols-2"} ${className}`.trim()}>
      {venues.map((item) => {
        const defaultProofSummary = item.credentials_configured
          ? "order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證"
          : "live exchange credential 尚未驗證 · order ack lifecycle 尚未驗證 · fill lifecycle 尚未驗證";
        const blockerSummary = item.blockers?.length ? item.blockers.join(" · ") : defaultProofSummary;
        return (
          <div
            key={item.venue || "unknown"}
            className={`app-surface-muted px-3 py-2 text-[11px] leading-5 ${readinessTone(item)}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-semibold uppercase tracking-wide">{item.venue || "unknown"}</div>
                <div className="opacity-80">{readinessLabel(item)}</div>
              </div>
              <div className="text-right opacity-80">{readinessBadgeLabel(item)}</div>
            </div>
            <div className="mt-2 opacity-90">config {item.enabled_in_config ? "enabled" : "disabled"} · creds {item.credentials_configured ? "configured" : "public-only"}</div>
            <div className="opacity-90">metadata contract {item.ok ? "OK" : "FAIL"}</div>
            <div className="opacity-90">step {item.contract?.step_size ?? "—"} · tick {item.contract?.tick_size ?? "—"}</div>
            <div className="opacity-90">min qty {formatScalar(item.contract?.min_qty)} · min cost {formatScalar(item.contract?.min_cost)}</div>
            <div className="mt-2 opacity-90">missing runtime proof · {blockerSummary}</div>
            {item.error ? <div className="mt-1 opacity-90">{item.error}</div> : null}
          </div>
        );
      })}
    </div>
  );
}
