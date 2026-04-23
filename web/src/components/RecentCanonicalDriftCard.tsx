import { humanizeRecentDriftInterpretation } from "../utils/runtimeCopy";

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

type RecentCanonicalDriftWindowPayload = {
  window?: string | number | null;
  alerts?: string[] | null;
  summary?: RecentCanonicalDriftWindowSummary | null;
};

export type RecentCanonicalDriftSummary = {
  generated_at?: string | null;
  source_artifact?: string | null;
  target_col?: string | null;
  horizon_minutes?: number | null;
  primary_window?: RecentCanonicalDriftWindowPayload | null;
  blocking_window?: RecentCanonicalDriftWindowPayload | null;
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

function humanizeRecentDriftInterpretationLabel(value?: string | null): string {
  return humanizeRecentDriftInterpretation(value);
}

function interpretationTone(interpretationLabel?: string | null): string {
  if (interpretationLabel === "健康" || interpretationLabel === "受支持的極端趨勢") {
    return "border-emerald-500/25 bg-emerald-500/8";
  }
  if (interpretationLabel === "市場狀態過度集中" || interpretationLabel === "分布病態") {
    return "border-amber-500/25 bg-amber-500/8";
  }
  return "border-white/8 bg-[#0f1528]";
}

function windowSignature(windowPayload?: RecentCanonicalDriftWindowPayload | null): string {
  const summary = windowPayload?.summary ?? null;
  const alerts = Array.isArray(windowPayload?.alerts) ? windowPayload?.alerts.filter(Boolean) : [];
  return JSON.stringify({
    window: windowPayload?.window ?? null,
    alerts,
    rows: summary?.rows ?? null,
    interpretation: summary?.drift_interpretation ?? null,
    dominantRegime: summary?.dominant_regime ?? null,
    winRate: summary?.win_rate ?? null,
  });
}

function renderWindowSummary(
  label: string,
  windowPayload?: RecentCanonicalDriftWindowPayload | null,
  { emphasize = false }: { emphasize?: boolean } = {},
) {
  const windowSummary = windowPayload?.summary ?? null;
  if (!windowSummary) return null;

  const quality = windowSummary.quality_metrics ?? null;
  const featureDiag = windowSummary.feature_diagnostics ?? null;
  const targetPath = windowSummary.target_path_diagnostics ?? null;
  const reference = windowSummary.reference_window_comparison ?? null;
  const alerts = Array.isArray(windowPayload?.alerts) ? windowPayload?.alerts.filter(Boolean) : [];
  const topShiftFeatures = (Array.isArray(reference?.top_mean_shift_features) ? reference?.top_mean_shift_features : [])
    .map((item) => item?.feature)
    .filter((value): value is string => Boolean(value))
    .slice(0, 3);
  const adverseStreak = targetPath?.longest_zero_target_streak ?? targetPath?.longest_one_target_streak ?? null;
  const toneClass = emphasize
    ? "border-amber-400/25 bg-amber-500/8"
    : "border-white/8 bg-black/10";

  return (
    <div className={`rounded-lg border px-3 py-2 ${toneClass}`}>
      <div className="font-medium text-slate-100">{label}</div>
      <div>
        視窗 {windowPayload?.window ?? "—"} · 樣本 {windowSummary.rows ?? "—"} · WR {formatPct(windowSummary.win_rate)} · 主導市場 {windowSummary.dominant_regime || "—"} {formatPct(windowSummary.dominant_regime_share)}
      </div>
      <div>
        警示 {alerts.length ? alerts.join(" · ") : "無"} · 品質 {formatSigned(quality?.avg_simulated_quality)} · PnL {formatSigned(quality?.avg_simulated_pnl, 4)} · spot-long {formatPct(quality?.spot_long_win_rate)} · DD {formatPct(quality?.avg_drawdown_penalty)}
      </div>
      <div>
        低變異 {featureDiag?.low_variance_count ?? "—"}/{featureDiag?.feature_count ?? "—"} · 壓縮 {featureDiag?.compressed_count ?? "—"} · 高缺值 {featureDiag?.null_heavy_count ?? "—"} · overlay {featureDiag?.overlay_only_count ?? "—"} · 預期靜態 {featureDiag?.expected_static_count ?? "—"}
      </div>
      <div>
        尾端 {formatStreak(targetPath?.tail_target_streak)} · 最長逆向 {formatStreak(adverseStreak)} · 前一窗 WR {formatPct(reference?.prev_win_rate)} ({formatSignedPct(reference?.win_rate_delta)})
      </div>
      <div>
        主要漂移 {topShiftFeatures.length ? topShiftFeatures.join(" / ") : "—"}
      </div>
    </div>
  );
}

export default function RecentCanonicalDriftCard({
  summary,
  pending = false,
  title = "📉 最近 canonical drift",
  className = "",
}: RecentCanonicalDriftCardProps) {
  const latestWindow = summary?.primary_window ?? null;
  const latestWindowSummary = latestWindow?.summary ?? null;
  const blockingWindow = summary?.blocking_window ?? null;
  const blockingWindowSummary = blockingWindow?.summary ?? null;
  const hasDistinctBlockingWindow = Boolean(
    blockingWindowSummary && windowSignature(blockingWindow) !== windowSignature(latestWindow),
  );
  const summaryGeneratedAt = summary?.generated_at ? new Date(summary.generated_at).toLocaleString("zh-TW") : "—";
  const latestInterpretationLabel = humanizeRecentDriftInterpretationLabel(latestWindowSummary?.drift_interpretation || "unavailable");
  const blockingInterpretationLabel = humanizeRecentDriftInterpretationLabel(blockingWindowSummary?.drift_interpretation || "unavailable");
  const tone = pending
    ? "border-cyan-500/25 bg-cyan-500/8"
    : hasDistinctBlockingWindow
      ? "border-white/8 bg-[#0f1528]"
      : interpretationTone(latestInterpretationLabel);

  return (
    <div className={`rounded-xl border px-4 py-3 text-sm text-slate-100 ${tone} ${className}`.trim()}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="font-semibold">{title}</div>
          <div className="mt-1 text-[11px] text-slate-300/80">
            {pending ? "正在向 /api/status 同步 recent canonical drift。" : `產物時間 ${summaryGeneratedAt}`}
          </div>
        </div>
        <div className="flex flex-wrap justify-end gap-2 text-[11px] uppercase tracking-[0.18em] text-slate-200">
          <div className="rounded-full border border-white/10 bg-black/15 px-2.5 py-1">
            {pending ? "同步中" : `最新視窗 · ${latestInterpretationLabel}`}
          </div>
          {hasDistinctBlockingWindow ? (
            <div className="rounded-full border border-amber-400/25 bg-amber-500/10 px-2.5 py-1 text-amber-100">
              {`阻塞視窗 · ${blockingInterpretationLabel}`}
            </div>
          ) : null}
        </div>
      </div>

      {pending ? (
        <div className="mt-3 leading-6 text-slate-200/80">
          目前 blocker pocket 的 recent-window drift 正在同步；在產物到位前不要把較寬歷史平均值當成目前 live truth。
        </div>
      ) : !latestWindowSummary && !blockingWindowSummary ? (
        <div className="mt-3 leading-6 text-slate-200/80">
          尚未取得 recent drift 產物；請先重跑 recent_drift_report 與 heartbeat fast diagnostics。
        </div>
      ) : (
        <div className="mt-3 space-y-3 text-[12px] leading-6 text-slate-100/90">
          {renderWindowSummary("最新 recent-window", latestWindow)}
          {hasDistinctBlockingWindow
            ? renderWindowSummary("當前 blocker pocket", blockingWindow, { emphasize: true })
            : null}
        </div>
      )}
    </div>
  );
}
