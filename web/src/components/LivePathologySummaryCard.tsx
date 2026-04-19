type TopMeanShiftFeature = {
  feature?: string | null;
  current_mean?: number | null;
  reference_mean?: number | null;
  mean_delta?: number | null;
};

type LaneSummary = {
  scope?: string | null;
  rows?: number | null;
  win_rate?: number | null;
  avg_pnl?: number | null;
  avg_quality?: number | null;
  avg_drawdown_penalty?: number | null;
  avg_time_underwater?: number | null;
  current_live_structure_bucket?: string | null;
  current_live_structure_bucket_rows?: number | null;
};

type SpilloverPocket = {
  regime_gate?: string | null;
  rows?: number | null;
  win_rate?: number | null;
  avg_pnl?: number | null;
  avg_quality?: number | null;
  avg_drawdown_penalty?: number | null;
  avg_time_underwater?: number | null;
};

type SpilloverSummary = {
  extra_rows?: number | null;
  extra_row_share?: number | null;
  win_rate_delta_vs_exact?: number | null;
  avg_pnl_delta_vs_exact?: number | null;
  avg_quality_delta_vs_exact?: number | null;
  avg_drawdown_penalty_delta_vs_exact?: number | null;
  avg_time_underwater_delta_vs_exact?: number | null;
  worst_extra_regime_gate?: SpilloverPocket | null;
  top_mean_shift_features?: TopMeanShiftFeature[] | null;
};

type RecommendedPatchSummary = {
  status?: string | null;
  reason?: string | null;
  spillover_regime_gate?: string | null;
  reference_patch_scope?: string | null;
  reference_source?: string | null;
  spillover_rows?: number | null;
  recommended_profile?: string | null;
  recommended_profile_source?: string | null;
  collapse_features?: string[] | null;
  min_collapse_flags?: number | null;
  preferred_support_cohort?: string | null;
  support_route_verdict?: string | null;
  support_route_deployable?: boolean | null;
  current_live_structure_bucket?: string | null;
  current_live_structure_bucket_rows?: number | null;
  minimum_support_rows?: number | null;
  gap_to_minimum?: number | null;
  recommended_action?: string | null;
};

export type DecisionQualityScopePathologySummary = {
  focus_scope?: string | null;
  focus_scope_label?: string | null;
  focus_scope_rows?: number | null;
  summary?: string | null;
  exact_live_lane?: LaneSummary | null;
  spillover?: SpilloverSummary | null;
  recommended_patch?: RecommendedPatchSummary | null;
};

type Props = {
  summary?: DecisionQualityScopePathologySummary | null;
  title?: string;
  className?: string;
};

const isFiniteNumber = (value: number | null | undefined): value is number => (
  typeof value === "number" && Number.isFinite(value)
);

const formatPct = (value: number | null | undefined, digits = 1, signed = false) => {
  if (!isFiniteNumber(value)) return "—";
  const prefix = signed && value > 0 ? "+" : "";
  return `${prefix}${(value * 100).toFixed(digits)}%`;
};

const formatDecimal = (value: number | null | undefined, digits = 3, signed = false) => {
  if (!isFiniteNumber(value)) return "—";
  const prefix = signed && value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(digits)}`;
};

const formatMeanShift = (shift: TopMeanShiftFeature) => {
  const feature = shift.feature || "unknown";
  const current = formatDecimal(shift.current_mean ?? null, 3);
  const reference = formatDecimal(shift.reference_mean ?? null, 3);
  const delta = formatDecimal(shift.mean_delta ?? null, 3, true);
  return `${feature} ${reference}→${current} (Δ ${delta})`;
};

const formatPatchStatus = (status?: string | null) => {
  switch (status) {
    case "reference_only_until_exact_support_ready":
      return "先當治理參考，不可直接放行";
    case "deployable_patch_candidate":
      return "已達可部署 patch 候選";
    default:
      return status || "patch 狀態未提供";
  }
};

export default function LivePathologySummaryCard({
  summary,
  title = "🧬 Live lane / spillover 對照",
  className = "",
}: Props) {
  if (!summary) return null;

  const exactLane = summary.exact_live_lane ?? null;
  const spillover = summary.spillover ?? null;
  const spilloverPocket = spillover?.worst_extra_regime_gate ?? null;
  const recommendedPatch = summary.recommended_patch ?? null;
  const topShifts = Array.isArray(spillover?.top_mean_shift_features)
    ? spillover.top_mean_shift_features.slice(0, 3)
    : [];
  const collapseFeatures = Array.isArray(recommendedPatch?.collapse_features)
    ? recommendedPatch.collapse_features.slice(0, 4)
    : [];
  const spilloverLabel = summary.focus_scope_label
    ? `${summary.focus_scope_label} spillover pocket`
    : "broader-scope spillover pocket";

  if (!summary.summary && !exactLane && !spilloverPocket && !recommendedPatch) return null;

  return (
    <div className={`rounded-xl border border-amber-700/40 bg-amber-950/10 p-4 text-xs text-amber-50 space-y-3 ${className}`.trim()}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">{title}</div>
          <div className="mt-1 text-[11px] leading-5 text-amber-100/80">
            不要把 exact live lane 與更寬 scope 的 spillover 混成同一個 current-live 真相。
          </div>
        </div>
        <div className="rounded-full border border-amber-500/30 bg-amber-400/10 px-2.5 py-1 text-[10px] uppercase tracking-[0.16em] text-amber-200">
          {summary.focus_scope_label || summary.focus_scope || "scope"}
        </div>
      </div>

      {summary.summary && (
        <div className="rounded-lg border border-amber-500/20 bg-black/10 px-3 py-2 leading-5 text-amber-50/90">
          {summary.summary}
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-950/10 px-3 py-3 text-emerald-50">
          <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-200/80">exact live lane</div>
          <div className="mt-1 text-sm font-semibold text-emerald-100">
            {exactLane?.scope || "regime_label+regime_gate+entry_quality_label"}
          </div>
          <div className="mt-2 space-y-1 text-[11px] leading-5 text-emerald-50/85">
            <div>
              rows {exactLane?.rows ?? "—"}
              {exactLane?.current_live_structure_bucket_rows != null ? ` · current bucket ${exactLane.current_live_structure_bucket_rows}` : ""}
            </div>
            <div>{exactLane?.current_live_structure_bucket || "未提供 current live structure bucket"}</div>
            <div>
              WR {formatPct(exactLane?.win_rate ?? null)} · 品質 {formatDecimal(exactLane?.avg_quality ?? null)} · PnL {formatPct(exactLane?.avg_pnl ?? null, 2, true)}
            </div>
            <div>
              DD 懲罰 {formatPct(exactLane?.avg_drawdown_penalty ?? null)} · 深套 {formatPct(exactLane?.avg_time_underwater ?? null)}
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-red-500/20 bg-red-950/10 px-3 py-3 text-red-50">
          <div className="text-[10px] uppercase tracking-[0.16em] text-red-200/80">{spilloverLabel}</div>
          <div className="mt-1 text-sm font-semibold text-red-100">
            {spilloverPocket?.regime_gate || summary.focus_scope_label || "no spillover"}
          </div>
          <div className="mt-2 space-y-1 text-[11px] leading-5 text-red-50/85">
            <div>
              focus scope rows {summary.focus_scope_rows ?? "—"}
              {spillover?.extra_rows != null ? ` · spillover rows ${spillover.extra_rows}` : ""}
              {spillover?.extra_row_share != null ? ` (${formatPct(spillover.extra_row_share)})` : ""}
            </div>
            <div>
              WR {formatPct(spilloverPocket?.win_rate ?? null)} · 品質 {formatDecimal(spilloverPocket?.avg_quality ?? null)} · PnL {formatPct(spilloverPocket?.avg_pnl ?? null, 2, true)}
            </div>
            <div>
              Δ WR {formatPct(spillover?.win_rate_delta_vs_exact ?? null, 1, true)} · Δ 品質 {formatDecimal(spillover?.avg_quality_delta_vs_exact ?? null, 3, true)} · Δ PnL {formatPct(spillover?.avg_pnl_delta_vs_exact ?? null, 2, true)}
            </div>
            <div>
              DD 懲罰 {formatPct(spilloverPocket?.avg_drawdown_penalty ?? null)} · 深套 {formatPct(spilloverPocket?.avg_time_underwater ?? null)}
            </div>
          </div>
        </div>
      </div>

      {topShifts.length > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] uppercase tracking-[0.16em] text-amber-200/80">top 4H shifts</div>
          <div className="flex flex-wrap gap-2">
            {topShifts.map((shift, index) => (
              <div key={`${shift.feature || "shift"}-${index}`} className="rounded-full border border-amber-500/20 bg-black/10 px-3 py-1.5 text-[11px] text-amber-50/90">
                {formatMeanShift(shift)}
              </div>
            ))}
          </div>
        </div>
      )}

      {recommendedPatch && (
        <div className="rounded-lg border border-sky-500/20 bg-sky-950/10 px-3 py-3 text-sky-50 space-y-2">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <div className="text-[10px] uppercase tracking-[0.16em] text-sky-200/80">建議正式 patch</div>
              <div className="mt-1 text-sm font-semibold text-sky-100">
                {recommendedPatch.recommended_profile || "未提供 profile"}
              </div>
            </div>
            <div className="rounded-full border border-sky-500/30 bg-sky-400/10 px-2.5 py-1 text-[10px] uppercase tracking-[0.16em] text-sky-200">
              {formatPatchStatus(recommendedPatch.status)}
            </div>
          </div>
          <div className="space-y-1 text-[11px] leading-5 text-sky-50/90">
            <div>
              live spillover {recommendedPatch.spillover_regime_gate || "—"}
              {recommendedPatch.spillover_rows != null ? ` · rows ${recommendedPatch.spillover_rows}` : ""}
            </div>
            <div>
              reference patch {recommendedPatch.reference_patch_scope || recommendedPatch.spillover_regime_gate || "—"}
              {recommendedPatch.reference_source ? ` · via ${recommendedPatch.reference_source}` : ""}
            </div>
            <div>
              support {recommendedPatch.current_live_structure_bucket_rows ?? "—"}
              /
              {recommendedPatch.minimum_support_rows ?? "—"}
              {recommendedPatch.gap_to_minimum != null ? ` · gap ${recommendedPatch.gap_to_minimum}` : ""}
            </div>
            <div>
              support route {recommendedPatch.support_route_verdict || "—"}
              {recommendedPatch.preferred_support_cohort ? ` · cohort ${recommendedPatch.preferred_support_cohort}` : ""}
            </div>
            {recommendedPatch.reason && <div>{recommendedPatch.reason}</div>}
            {recommendedPatch.recommended_action && <div>action {recommendedPatch.recommended_action}</div>}
          </div>
          {collapseFeatures.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {collapseFeatures.map((feature) => (
                <div key={feature} className="rounded-full border border-sky-500/20 bg-black/10 px-3 py-1.5 text-[11px] text-sky-50/90">
                  {feature}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
