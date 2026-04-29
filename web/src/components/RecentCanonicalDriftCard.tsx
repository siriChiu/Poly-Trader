import { humanizeFeatureKey, humanizeRecentDriftInterpretation, humanizeRuntimeDetailText } from "../utils/runtimeCopy";

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

type CanonicalTailRegimeBreakdown = {
  rows?: number | null;
  losses?: number | null;
  wins?: number | null;
  loss_rate?: number | null;
};

type CanonicalTailRootCause = {
  window?: number | string | null;
  rows?: number | null;
  losses?: number | null;
  wins?: number | null;
  loss_path_breakdown?: {
    tp_miss_count?: number | null;
    dd_breach_count?: number | null;
    high_underwater_count?: number | null;
    avg_time_underwater?: number | null;
  } | null;
  regime_breakdown?: {
    chop?: CanonicalTailRegimeBreakdown | null;
    bull?: CanonicalTailRegimeBreakdown | null;
    bear?: CanonicalTailRegimeBreakdown | null;
    [key: string]: CanonicalTailRegimeBreakdown | null | undefined;
  } | null;
  dominant_loss_regime?: string | null;
  top_4h_shift_features?: string[] | null;
  feature_shift?: Record<string, unknown> | null;
  key_findings?: string[] | null;
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
    frozen_count?: number | null;
    compressed_count?: number | null;
    expected_static_count?: number | null;
    expected_compressed_count?: number | null;
    overlay_only_count?: number | null;
    unexpected_frozen_count?: number | null;
    unexpected_compressed_count?: number | null;
    null_heavy_count?: number | null;
    low_distinct_count?: number | null;
    low_distinct_features?: string[] | null;
    expected_compressed_features?: string[] | null;
    unexpected_frozen_features?: string[] | null;
    unexpected_compressed_features?: string[] | null;
  } | null;
  target_path_diagnostics?: {
    tail_target_streak?: TargetStreak | null;
    longest_target_streak?: TargetStreak | null;
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
    new_unexpected_frozen_features?: string[] | null;
    new_unexpected_compressed_features?: string[] | null;
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
  canonical_tail_root_cause?: CanonicalTailRootCause | null;
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

function humanizeTargetStreakTarget(target?: number | string | null): string {
  const normalized = String(target ?? "").trim().toLowerCase();
  if (normalized === "1" || normalized === "true" || normalized === "win") return "達標";
  if (normalized === "0" || normalized === "false" || normalized === "loss") return "未達標";
  if (!normalized) return "未知狀態";
  return humanizeRuntimeDetailText(normalized);
}

function formatStreak(streak?: TargetStreak | null): string {
  if (!streak || typeof streak.count !== "number") return "—";
  const targetLabel = humanizeTargetStreakTarget(streak.target);
  const span = streak.start_timestamp || streak.end_timestamp
    ? `（${streak.start_timestamp || "?"} → ${streak.end_timestamp || "?"}）`
    : "";
  return `${streak.count} 筆${targetLabel}${span}`;
}

function formatFeatureLabels(features?: string[] | null): string {
  if (!Array.isArray(features) || features.length === 0) return "—";
  return features
    .filter((value): value is string => Boolean(value))
    .slice(0, 3)
    .map((value) => humanizeFeatureKey(value, { preferShortLabel: true }))
    .join(" / ") || "—";
}

function formatRegimeLossLabel(_label: string, payload?: CanonicalTailRegimeBreakdown | null): string {
  if (!payload) return "—";
  const rows = payload.rows ?? "—";
  const losses = payload.losses ?? "—";
  return `${losses}/${rows} (${formatPct(payload.loss_rate)})`;
}

function renderCanonicalTailRootCause(rootCause?: CanonicalTailRootCause | null) {
  if (!rootCause) return null;
  const pathBreakdown = rootCause.loss_path_breakdown ?? {};
  const regimeBreakdown = rootCause.regime_breakdown ?? {};
  const topShiftLabels = formatFeatureLabels(rootCause.top_4h_shift_features ?? null);
  const keyFindings = Array.isArray(rootCause.key_findings) ? rootCause.key_findings.filter(Boolean).slice(0, 2) : [];
  return (
    <div className="rounded-lg border border-rose-400/20 bg-rose-500/8 px-3 py-2">
      <div className="font-medium text-rose-100">最近 100 筆 loss path 根因</div>
      <div>
        樣本 {rootCause.rows ?? "—"} · loss {rootCause.losses ?? "—"} · win {rootCause.wins ?? "—"} · dominant loss regime {humanizeRecentDriftDominantRegimeLabel(rootCause.dominant_loss_regime)}
      </div>
      <div>
        TP miss {pathBreakdown.tp_miss_count ?? "—"} · DD breach {pathBreakdown.dd_breach_count ?? "—"} · underwater {pathBreakdown.high_underwater_count ?? "—"} · 平均 underwater {formatPct(pathBreakdown.avg_time_underwater)}
      </div>
      <div>
        盤整 {formatRegimeLossLabel("chop", regimeBreakdown?.chop)} · 牛市 {formatRegimeLossLabel("bull", regimeBreakdown?.bull)} · 熊市 {formatRegimeLossLabel("bear", regimeBreakdown?.bear)}
      </div>
      <div>4H shift {topShiftLabels}</div>
      {keyFindings.length ? <div>結論 {keyFindings.join(" · ")}</div> : null}
    </div>
  );
}

function humanizeRecentDriftInterpretationLabel(value?: string | null): string {
  return humanizeRecentDriftInterpretation(value);
}

function humanizeRecentDriftDominantRegimeLabel(value?: string | null): string {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) return "—";
  if (normalized === "bull") return "牛市";
  if (normalized === "bear") return "熊市";
  if (normalized === "chop") return "盤整";
  if (normalized === "neutral") return "中性";
  return humanizeRuntimeDetailText(value);
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
  const alertLabels = alerts.map((alert) => humanizeRuntimeDetailText(alert));
  const dominantRegimeLabel = humanizeRecentDriftDominantRegimeLabel(windowSummary.dominant_regime);
  const topShiftFeatures = (Array.isArray(reference?.top_mean_shift_features) ? reference?.top_mean_shift_features : [])
    .map((item) => item?.feature)
    .filter((value): value is string => Boolean(value))
    .slice(0, 3)
    .map((value) => humanizeFeatureKey(value, { preferShortLabel: true }));
  const adverseStreak = targetPath?.longest_zero_target_streak ?? targetPath?.longest_one_target_streak ?? null;
  const lowDistinctFeatureLabels = formatFeatureLabels(featureDiag?.low_distinct_features ?? null);
  const unexpectedCompressedFeatureLabels = formatFeatureLabels(featureDiag?.unexpected_compressed_features ?? null);
  const newUnexpectedCompressedFeatureLabels = formatFeatureLabels(reference?.new_unexpected_compressed_features ?? null);
  const toneClass = emphasize
    ? "border-amber-400/25 bg-amber-500/8"
    : "border-white/8 bg-black/10";

  return (
    <div className={`rounded-lg border px-3 py-2 ${toneClass}`}>
      <div className="font-medium text-slate-100">{label}</div>
      <div>
        視窗 {windowPayload?.window ?? "—"} · 樣本 {windowSummary.rows ?? "—"} · 勝率 {formatPct(windowSummary.win_rate)} · 主導市場 {dominantRegimeLabel} {formatPct(windowSummary.dominant_regime_share)}
      </div>
      <div>
        警示 {alertLabels.length ? alertLabels.join(" · ") : "無"} · 品質 {formatSigned(quality?.avg_simulated_quality)} · 損益 {formatSigned(quality?.avg_simulated_pnl, 4)} · 現貨多單勝率 {formatPct(quality?.spot_long_win_rate)} · 回撤 {formatPct(quality?.avg_drawdown_penalty)}
      </div>
      <div>
        低變異 {featureDiag?.low_variance_count ?? "—"}/{featureDiag?.feature_count ?? "—"} · 低唯一值 {featureDiag?.low_distinct_count ?? "—"} · 壓縮 {featureDiag?.compressed_count ?? "—"}（預期 {featureDiag?.expected_compressed_count ?? "—"} / 非預期 {featureDiag?.unexpected_compressed_count ?? "—"}） · 非預期凍結 {featureDiag?.unexpected_frozen_count ?? "—"} · 高缺值 {featureDiag?.null_heavy_count ?? "—"} · 疊層觀察 {featureDiag?.overlay_only_count ?? "—"} · 預期靜態 {featureDiag?.expected_static_count ?? "—"}
      </div>
      <div>
        非預期壓縮特徵 {unexpectedCompressedFeatureLabels} · 低唯一值特徵 {lowDistinctFeatureLabels} · 新增壓縮 {newUnexpectedCompressedFeatureLabels}
      </div>
      <div>
        尾端 {formatStreak(targetPath?.tail_target_streak)} · 最長連續 {formatStreak(targetPath?.longest_target_streak)} · 最長逆向 {formatStreak(adverseStreak)} · 前一窗 勝率 {formatPct(reference?.prev_win_rate)} ({formatSignedPct(reference?.win_rate_delta)})
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
          目前阻塞口袋的近期視窗漂移正在同步；在產物到位前不要把較寬歷史平均值當成目前即時真相。
        </div>
      ) : !latestWindowSummary && !blockingWindowSummary ? (
        <div className="mt-3 leading-6 text-slate-200/80">
          尚未取得 recent drift 產物；請先重跑 recent_drift_report 與 heartbeat fast diagnostics。
        </div>
      ) : (
        <div className="mt-3 space-y-3 text-[12px] leading-6 text-slate-100/90">
          {renderCanonicalTailRootCause(summary?.canonical_tail_root_cause ?? null)}
          {renderWindowSummary("最新近期視窗", latestWindow)}
          {hasDistinctBlockingWindow
            ? renderWindowSummary("當前阻塞口袋", blockingWindow, { emphasize: true })
            : null}
        </div>
      )}
    </div>
  );
}
