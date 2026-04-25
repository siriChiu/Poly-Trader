import { humanizeExecutionReason, humanizeLifecycleDiagnosticLabel } from "../utils/runtimeCopy";

type VenueReadinessItem = {
  venue?: string;
  ok?: boolean;
  enabled_in_config?: boolean;
  credentials_configured?: boolean;
  error?: string | null;
  blockers?: string[] | null;
  proof_state?: string | null;
  readiness_scope?: string | null;
  operator_next_action?: string | null;
  verify_next?: string | null;
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
  if (!item.ok) return "元資料契約失敗";
  if (item.enabled_in_config && item.credentials_configured) return "已配置憑證 / 待補實單證據";
  if (item.enabled_in_config) return "僅公開資料 / 元資料路徑";
  return "停用場館 / 僅元資料";
};

const readinessBadgeLabel = (item: VenueReadinessItem) => {
  if (!item.ok) return "元資料失敗";
  if (item.enabled_in_config && item.credentials_configured) return "已配置";
  if (item.enabled_in_config) return "公開資料";
  return "停用";
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
          ? ["order ack lifecycle", "fill lifecycle"]
          : ["live exchange credential", "order ack lifecycle", "fill lifecycle"];
        const blockerSummary = (item.blockers?.length ? item.blockers : defaultProofSummary)
          .map((entry) => humanizeExecutionReason(entry))
          .join(" · ");
        const proofStateLabel = humanizeLifecycleDiagnosticLabel(item.proof_state || item.readiness_scope || "unknown");
        const operatorNextAction = item.operator_next_action ? humanizeExecutionReason(item.operator_next_action) : null;
        const verifyNext = item.verify_next ? humanizeExecutionReason(item.verify_next) : null;
        if (compact) {
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
              <div className="mt-2 opacity-90">
                設定 {item.enabled_in_config ? "啟用" : "停用"} · 憑證 {item.credentials_configured ? "已配置" : "僅公開資料"} · 元資料 {item.ok ? "正常" : "失敗"}
              </div>
              <div className="opacity-90">
                數量步進 {item.contract?.step_size ?? "—"} · 價格刻度 {item.contract?.tick_size ?? "—"} · 最小數量 {formatScalar(item.contract?.min_qty)}
              </div>
              <div className="opacity-90">待補實單證據 · {blockerSummary}</div>
              <div className="opacity-90">證據狀態 {proofStateLabel}</div>
              {operatorNextAction ? <div className="opacity-90">下一步 {operatorNextAction}</div> : null}
              {verifyNext ? <div className="opacity-90">驗證 {verifyNext}</div> : null}
              {item.error ? <div className="mt-1 opacity-90">{item.error}</div> : null}
            </div>
          );
        }
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
            <div className="mt-2 opacity-90">設定 {item.enabled_in_config ? "啟用" : "停用"} · 憑證 {item.credentials_configured ? "已配置" : "僅公開資料"}</div>
            <div className="opacity-90">元資料契約 {item.ok ? "正常" : "失敗"}</div>
            <div className="opacity-90">數量步進 {item.contract?.step_size ?? "—"} · 價格刻度 {item.contract?.tick_size ?? "—"}</div>
            <div className="opacity-90">最小數量 {formatScalar(item.contract?.min_qty)} · 最小成本 {formatScalar(item.contract?.min_cost)}</div>
            <div className="mt-2 opacity-90">待補實單證據 · {blockerSummary}</div>
            <div className="opacity-90">證據狀態 {proofStateLabel}</div>
            {operatorNextAction ? <div className="opacity-90">下一步 {operatorNextAction}</div> : null}
            {verifyNext ? <div className="opacity-90">驗證 {verifyNext}</div> : null}
            {item.error ? <div className="mt-1 opacity-90">{item.error}</div> : null}
          </div>
        );
      })}
    </div>
  );
}
