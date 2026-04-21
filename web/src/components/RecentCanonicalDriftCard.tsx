type DriftFeatureShift = {
  feature?: string | null;
  mean_delta?: number | null;
};

type TargetStreak = {
  target?: number | string | null;
  count?: number | null;
  start_timestamp?: string | null;
  end_timestamp?: string | null;
};

type RecentCanonicalDriftWindowSummary = {
  rows?: number | null;
  win_rate?: number | null;
  drift_interpretation?: string | null;
  dominant_regime?: string | null;
  dominant_regime_share?: number | null;
  quality_metrics?: {
    avg_simulated_pnl?: number | null;
    avg_simulated_quality?: number | null;
    avg_drawdown_penalty?: number | null;
    spot_long_win_rate?: number | null;
  } | null;
  feature_diagnostics?: {
    feature_count?: number | null;
    low_variance_count?: number | null;
    compressed_count?: number | null;
    expected_static_count?: number | null;
    expected_compressed_count?: number | null;
    overlay_only_count?: number | null;
    null_heavy_count?: number | null;
    low_distinct_count?: number | null;
  } | null;
  target_path_diagnostics?: {
    tail_target_streak?: TargetStreak | null;
    longest_zero_target_streak?: TargetStreak | null;
    longest_one_target_streak?: TargetStreak | null;
  } | null;
  reference_window_comparison?: {
    prev_win_rate?: number | null;
    prev_quality?: number | null;
    prev_pnl?: number | null;
    win_rate_delta?: number | null;
    quality_delta?: number | null;
    pnl_delta?: number | null;
    top_mean_shift_features?: DriftFeatureShift[] | null;
  } | null;
};

export type RecentCanonicalDriftSummary = {
  generated_at?: string | null;
  source_artifact?: string | null;
  target_col?: string | null;
  horizon_minutes?: number | null;
  primary_window?: {
    window?: string | number | null;
    alerts?: string[] | null;
    summary?: RecentCanonicalDriftWindowSummary | null;
  } | null;
};

type RecentCanonicalDriftCardProps = {
  summary?: RecentCanonicalDriftSummary | null;
  pending?: boolean;
  title?: string;
  className?: string;
};

function formatPct(value?: number | null, digits = 1): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

function formatSigned(value?: number | null, digits = 3): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function formatSignedPct(value?: number | null, digits = 1): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(digits)}%`;
}

function formatStreak(streak?: TargetStreak | null): string {
  if (!streak || typeof streak.count !== "number") return "—";
  const target = streak.target ?? "?";
  return `${streak.count}x${target}`;
}

function interpretationTone(interpretation?: string | null): string {
  if (interpretation === "healthy" || interpretation === "supported_extreme_trend") {
    return "border-emerald-500/25 bg-emerald-500/8";
  }
  if (interpretation === "regime_concentration" || interpretation === "distribution_pathology") {
    return "border-amber-500/25 bg-amber-500/8";
  }
  return "border-white/8 bg-[#0f1528]";
}

export default function RecentCanonicalDriftCard({
  summary,
  pending = false,
  title = "📉 Recent canonical drift",
  className = "",
}: RecentCanonicalDriftCardProps) {
  const primaryWindow = summary?.primary_window ?? null;
  const windowSummary = primaryWindow?.summary ?? null;
  const quality = windowSummary?.quality_metrics ?? null;
  const featureDiag = windowSummary?.feature_diagnostics ?? null;
  const targetPath = windowSummary?.target_path_diagnostics ?? null;
  const reference = windowSummary?.reference_window_comparison ?? null;
  const alerts = Array.isArray(primaryWindow?.alerts) ? primaryWindow?.alerts.filter(Boolean) : [];
  const topShiftFeatures = (Array.isArray(reference?.top_mean_shift_features) ? reference?.top_mean_shift_features : [])
    .map((item) => item?.feature)
    .filter((value): value is string => Boolean(value))
    .slice(0, 3);
  const adverseStreak = targetPath?.longest_zero_target_streak ?? targetPath?.longest_one_target_streak ?? null;
  const summaryGeneratedAt = summary?.generated_at ? new Date(summary.generated_at).toLocaleString("zh-TW") : "—";
  const interpretation = windowSummary?.drift_interpretation || "unavailable";
  const tone = pending ? "border-cyan-500/25 bg-cyan-500/8" : interpretationTone(windowSummary?.drift_interpretation);

  return (
    <div className={`rounded-xl border px-4 py-3 text-sm text-slate-100 ${tone} ${className}`.trim()}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="font-semibold">{title}</div>
          <div className="mt-1 text-[11px] text-slate-300/80">
            {pending ? "正在向 /api/status 同步 recent canonical drift。" : `artifact ${summaryGeneratedAt}`}
          </div>
        </div>
        <div className="rounded-full border border-white/10 bg-black/15 px-2.5 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-200">
          {pending ? "同步中" : interpretation}
        </div>
      </div>

      {pending ? (
        <div className="mt-3 leading-6 text-slate-200/80">
          current blocker pocket 的 recent-window drift 正在同步；在 artifact 到位前不要把 broader 歷史平均值當成 current live truth。
        </div>
      ) : !windowSummary ? (
        <div className="mt-3 leading-6 text-slate-200/80">
          尚未取得 recent drift artifact；請先重跑 recent_drift_report 與 heartbeat fast diagnostics。
        </div>
      ) : (
        <div className="mt-3 space-y-2 text-[12px] leading-6 text-slate-100/90">
          <div>
            window {primaryWindow?.window ?? "—"} · rows {windowSummary.rows ?? "—"} · WR {formatPct(windowSummary.win_rate)} · {windowSummary.dominant_regime || "—"} {formatPct(windowSummary.dominant_regime_share)}
          </div>
          <div>
            alerts {alerts.length ? alerts.join(" · ") : "none"} · quality {formatSigned(quality?.avg_simulated_quality)} · pnl {formatSigned(quality?.avg_simulated_pnl, 4)} · spot-long {formatPct(quality?.spot_long_win_rate)} · DD {formatPct(quality?.avg_drawdown_penalty)}
          </div>
          <div>
            variance {featureDiag?.low_variance_count ?? "—"}/{featureDiag?.feature_count ?? "—"} · compressed {featureDiag?.compressed_count ?? "—"} · null-heavy {featureDiag?.null_heavy_count ?? "—"} · overlay {featureDiag?.overlay_only_count ?? "—"} · expected-static {featureDiag?.expected_static_count ?? "—"}
          </div>
          <div>
            tail {formatStreak(targetPath?.tail_target_streak)} · adverse {formatStreak(adverseStreak)} · prev WR {formatPct(reference?.prev_win_rate)} ({formatSignedPct(reference?.win_rate_delta)})
          </div>
          <div>
            shifts {topShiftFeatures.length ? topShiftFeatures.join(" / ") : "—"}
          </div>
        </div>
      )}
    </div>
  );
}
