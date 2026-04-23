import {
  humanizeLivePathologyLabel,
  humanizeRuntimeDetailText,
  humanizeStructureBucketLabel,
  humanizeSupportGovernanceRouteLabel,
  humanizeSupportRouteLabel,
} from "../utils/runtimeCopy";

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
  dominant_structure_bucket?: string | null;
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
  support_governance_route?: string | null;
  support_route_deployable?: boolean | null;
  current_live_regime_gate?: string | null;
  patch_scope_matches_live?: boolean | null;
  reference_only_cause?: string | null;
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
  compact?: boolean;
  supportAlignmentStatus?: string | null;
  supportAlignmentSummary?: string | null;
  runtimeExactSupportRows?: number | null;
  calibrationExactLaneRows?: number | null;
  supportRouteVerdict?: string | null;
  supportGovernanceRoute?: string | null;
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
    case "reference_only_non_current_live_scope":
      return "範圍不同，僅作治理參考";
    case "reference_only_while_deployment_blocked":
      return "blocker 未清前僅作治理參考";
    case "deployable_patch_candidate":
      return "已達 runtime / training patch 候選";
    default:
      return status || "patch 狀態未提供";
  }
};

const isReferenceOnlyPatchStatus = (status?: string | null) => (
  String(status || "").startsWith("reference_only_")
);

const formatSupportAlignmentStatus = (status?: string | null) => {
  switch (status) {
    case "runtime_ahead_of_calibration":
      return "執行期樣本先於校準樣本";
    case "aligned":
      return "執行期 / 校準已對齊";
    default:
      return status || null;
  }
};

const PATHOLOGY_LABELS = {
  exactLane: humanizeLivePathologyLabel("exact_lane"),
  spilloverPocket: humanizeLivePathologyLabel("spillover_pocket"),
  spilloverRows: humanizeLivePathologyLabel("spillover_rows"),
  focusScopeRows: humanizeLivePathologyLabel("focus_scope_rows"),
  currentSpillover: humanizeLivePathologyLabel("current_spillover"),
  referencePatch: humanizeLivePathologyLabel("reference_patch"),
  supportRoute: humanizeLivePathologyLabel("support_route"),
  governanceRoute: humanizeLivePathologyLabel("governance_route"),
  top4hShifts: humanizeLivePathologyLabel("top_4h_shifts"),
  nextAction: humanizeLivePathologyLabel("next_action"),
  currentBucketSupport: humanizeLivePathologyLabel("current_bucket_support"),
  exactLaneCohort: humanizeLivePathologyLabel("exact_lane_cohort"),
  historicalLaneBucket: humanizeLivePathologyLabel("historical_lane_bucket"),
  noSpillover: humanizeLivePathologyLabel("no_spillover"),
  patch: humanizeLivePathologyLabel("patch"),
};

export default function LivePathologySummaryCard({
  summary,
  title = "🧬 精準路徑 / 外溢口袋對照",
  className = "",
  compact = false,
  supportAlignmentStatus,
  supportAlignmentSummary,
  runtimeExactSupportRows,
  calibrationExactLaneRows,
  supportRouteVerdict,
  supportGovernanceRoute,
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
  const focusScopeLabel = humanizeRuntimeDetailText(summary.focus_scope_label || summary.focus_scope || "範圍");
  const spilloverLabel = summary.focus_scope_label
    ? `${humanizeRuntimeDetailText(summary.focus_scope_label)} ${PATHOLOGY_LABELS.spilloverPocket}`
    : `較寬範圍 ${PATHOLOGY_LABELS.spilloverPocket}`;

  if (!summary.summary && !exactLane && !spilloverPocket && !recommendedPatch) return null;

  const compactTopShifts = topShifts.slice(0, 2);
  const patchProfileLabel = humanizeRuntimeDetailText(recommendedPatch?.recommended_profile || "未提供 profile");
  const compactPatchLabel = humanizeRuntimeDetailText(
    recommendedPatch?.recommended_profile
    || recommendedPatch?.reference_patch_scope
    || (recommendedPatch ? formatPatchStatus(recommendedPatch.status) : null)
  );
  const compactPatchStatusLabel = recommendedPatch ? formatPatchStatus(recommendedPatch.status) : null;
  const patchSectionTitle = isReferenceOnlyPatchStatus(recommendedPatch?.status)
    ? "治理 / 訓練 patch 參考"
    : "建議正式 patch";
  const currentBucketSupportRows = recommendedPatch?.current_live_structure_bucket_rows ?? exactLane?.current_live_structure_bucket_rows;
  const currentBucketSupportMinimum = recommendedPatch?.minimum_support_rows ?? null;
  const currentBucketSupportLabel = currentBucketSupportRows != null
    ? `${PATHOLOGY_LABELS.currentBucketSupport} ${currentBucketSupportRows}${currentBucketSupportMinimum != null ? `/${currentBucketSupportMinimum}` : ""}`
    : null;
  const exactLaneRowsLabel = exactLane?.rows != null
    ? `${PATHOLOGY_LABELS.exactLaneCohort} ${exactLane.rows}`
    : `${PATHOLOGY_LABELS.exactLaneCohort} —`;
  const exactLaneHistoricalBucket = exactLane?.dominant_structure_bucket || null;
  const exactLaneHistoricalBucketLabel = exactLaneHistoricalBucket && exactLaneHistoricalBucket !== exactLane?.current_live_structure_bucket
    ? `${PATHOLOGY_LABELS.historicalLaneBucket} ${humanizeStructureBucketLabel(exactLaneHistoricalBucket)}`
    : null;
  const exactLaneCurrentBucketLabel = exactLane?.current_live_structure_bucket
    ? `當前 bucket ${humanizeStructureBucketLabel(exactLane.current_live_structure_bucket)}`
    : humanizeStructureBucketLabel(exactLane?.scope || "未提供 bucket");
  const spilloverPocketLabel = humanizeStructureBucketLabel(spilloverPocket?.regime_gate || spilloverLabel || PATHOLOGY_LABELS.noSpillover);
  const supportAlignmentStatusLabel = formatSupportAlignmentStatus(supportAlignmentStatus);
  const supportAlignmentCountsLabel = runtimeExactSupportRows != null || calibrationExactLaneRows != null
    ? `執行期 / 校準 ${runtimeExactSupportRows ?? "—"} / ${calibrationExactLaneRows ?? "—"}`
    : null;
  const supportAlignmentTone = supportAlignmentStatus === "runtime_ahead_of_calibration"
    ? "text-amber-200/90"
    : supportAlignmentStatus === "aligned"
      ? "text-emerald-200/90"
      : "text-slate-200/80";
  const supportRouteLabel = supportRouteVerdict || recommendedPatch?.support_route_verdict || null;
  const supportGovernanceRouteLabel = supportGovernanceRoute || recommendedPatch?.support_governance_route || null;
  const supportRouteDisplayLabel = humanizeSupportRouteLabel(supportRouteLabel);
  const supportGovernanceRouteDisplayLabel = humanizeSupportGovernanceRouteLabel(supportGovernanceRouteLabel);

  if (compact) {
    return (
      <div className={`app-surface-card border-amber-700/40 bg-amber-950/10 text-xs text-amber-50 space-y-3 ${className}`.trim()}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">{title}</div>
            <div className="mt-1 text-[11px] leading-5 text-amber-100/80">
              摘要版只保留目前精準路徑、外溢口袋與 patch 治理真相；完整診斷請看執行狀態。
            </div>
          </div>
          <div className="rounded-full border border-amber-500/30 bg-amber-400/10 px-2.5 py-1 text-[10px] uppercase tracking-[0.16em] text-amber-200">
            {focusScopeLabel}
          </div>
        </div>

        <div className="grid gap-2 xl:grid-cols-3">
          <div className="rounded-lg border border-emerald-500/20 bg-emerald-950/10 px-3 py-2 text-[11px] leading-5 text-emerald-50">
            <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-200/80">{PATHOLOGY_LABELS.exactLane}</div>
            <div className="mt-1 font-semibold text-emerald-100">
              勝率 {formatPct(exactLane?.win_rate ?? null)} · 品質 {formatDecimal(exactLane?.avg_quality ?? null)}
            </div>
            <div className="text-emerald-50/80">
              {exactLaneCurrentBucketLabel}
            </div>
            <div className="text-emerald-50/80">
              {exactLaneRowsLabel}
              {currentBucketSupportLabel ? ` · ${currentBucketSupportLabel}` : ""}
            </div>
            {exactLaneHistoricalBucketLabel && (
              <div className="text-emerald-50/80">{exactLaneHistoricalBucketLabel}</div>
            )}
            {(supportAlignmentCountsLabel || supportAlignmentStatusLabel) && (
              <div className={supportAlignmentTone}>
                {supportAlignmentCountsLabel || "執行期 / 校準 — / —"}
                {supportAlignmentStatusLabel ? ` · ${supportAlignmentStatusLabel}` : ""}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-red-500/20 bg-red-950/10 px-3 py-2 text-[11px] leading-5 text-red-50">
            <div className="text-[10px] uppercase tracking-[0.16em] text-red-200/80">{PATHOLOGY_LABELS.spilloverPocket}</div>
            <div className="mt-1 font-semibold text-red-100">
              {spilloverPocketLabel}
            </div>
            <div className="text-red-50/80">
              {spillover?.extra_rows != null ? `${PATHOLOGY_LABELS.spilloverRows} ${spillover.extra_rows}` : `${PATHOLOGY_LABELS.spilloverRows} —`}
              {spillover?.extra_row_share != null ? ` (${formatPct(spillover.extra_row_share)})` : ""}
            </div>
            <div className="text-red-50/80">
              Δ 勝率 {formatPct(spillover?.win_rate_delta_vs_exact ?? null, 1, true)} · Δ 品質 {formatDecimal(spillover?.avg_quality_delta_vs_exact ?? null, 3, true)}
            </div>
          </div>

          <div className="rounded-lg border border-sky-500/20 bg-sky-950/10 px-3 py-2 text-[11px] leading-5 text-sky-50">
            <div className="text-[10px] uppercase tracking-[0.16em] text-sky-200/80">{PATHOLOGY_LABELS.patch}</div>
            <div className="mt-1 font-semibold text-sky-100">{compactPatchLabel || "未提供 patch"}</div>
            <div className="text-sky-50/80">
              樣本 {recommendedPatch?.current_live_structure_bucket_rows ?? "—"}/{recommendedPatch?.minimum_support_rows ?? "—"}
              {recommendedPatch?.gap_to_minimum != null ? ` · gap ${recommendedPatch.gap_to_minimum}` : ""}
            </div>
            <div className="text-sky-50/80">
              {compactPatchStatusLabel || "patch 狀態未提供"}
              {supportRouteLabel ? ` · ${PATHOLOGY_LABELS.supportRoute} ${supportRouteDisplayLabel}` : ""}
              {supportGovernanceRouteLabel ? ` · ${PATHOLOGY_LABELS.governanceRoute} ${supportGovernanceRouteDisplayLabel}` : ""}
            </div>
          </div>
        </div>

        {compactTopShifts.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {compactTopShifts.map((shift, index) => (
              <div key={`${shift.feature || "compact-shift"}-${index}`} className="rounded-full border border-amber-500/20 bg-black/10 px-3 py-1.5 text-[11px] text-amber-50/90">
                {formatMeanShift(shift)}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`app-surface-card border-amber-700/40 bg-amber-950/10 text-xs text-amber-50 space-y-3 ${className}`.trim()}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">{title}</div>
          <div className="mt-1 text-[11px] leading-5 text-amber-100/80">
            不要把精準路徑與更寬範圍的外溢口袋混成同一個目前 live 真相。
          </div>
        </div>
        <div className="rounded-full border border-amber-500/30 bg-amber-400/10 px-2.5 py-1 text-[10px] uppercase tracking-[0.16em] text-amber-200">
          {summary.focus_scope_label || summary.focus_scope || "範圍"}
        </div>
      </div>

      {summary.summary && (
        <div className="rounded-lg border border-amber-500/20 bg-black/10 px-3 py-2 leading-5 text-amber-50/90">
          {summary.summary}
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-950/10 px-3 py-3 text-emerald-50">
          <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-200/80">{PATHOLOGY_LABELS.exactLane}</div>
          <div className="mt-1 text-sm font-semibold text-emerald-100">
            {exactLane?.scope || "regime_label+regime_gate+entry_quality_label"}
          </div>
          <div className="mt-2 space-y-1 text-[11px] leading-5 text-emerald-50/85">
            <div>
              {exactLaneRowsLabel}
              {currentBucketSupportLabel ? ` · ${currentBucketSupportLabel}` : ""}
            </div>
            {(supportAlignmentCountsLabel || supportAlignmentStatusLabel) && (
              <div className={supportAlignmentTone}>
                {supportAlignmentCountsLabel || "執行期 / 校準 — / —"}
                {supportAlignmentStatusLabel ? ` · ${supportAlignmentStatusLabel}` : ""}
              </div>
            )}
            {supportAlignmentSummary && (
              <div className={supportAlignmentTone}>{supportAlignmentSummary}</div>
            )}
            <div>{exactLaneCurrentBucketLabel}</div>
            {exactLaneHistoricalBucketLabel && (
              <div>{exactLaneHistoricalBucketLabel}</div>
            )}
            <div>
              勝率 {formatPct(exactLane?.win_rate ?? null)} · 品質 {formatDecimal(exactLane?.avg_quality ?? null)} · 損益 {formatPct(exactLane?.avg_pnl ?? null, 2, true)}
            </div>
            <div>
              回撤懲罰 {formatPct(exactLane?.avg_drawdown_penalty ?? null)} · 深套 {formatPct(exactLane?.avg_time_underwater ?? null)}
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-red-500/20 bg-red-950/10 px-3 py-3 text-red-50">
          <div className="text-[10px] uppercase tracking-[0.16em] text-red-200/80">{spilloverLabel}</div>
          <div className="mt-1 text-sm font-semibold text-red-100">
            {spilloverPocketLabel}
          </div>
          <div className="mt-2 space-y-1 text-[11px] leading-5 text-red-50/85">
            <div>
              {PATHOLOGY_LABELS.focusScopeRows} {summary.focus_scope_rows ?? "—"}
              {spillover?.extra_rows != null ? ` · ${PATHOLOGY_LABELS.spilloverRows} ${spillover.extra_rows}` : ""}
              {spillover?.extra_row_share != null ? ` (${formatPct(spillover.extra_row_share)})` : ""}
            </div>
            <div>
              勝率 {formatPct(spilloverPocket?.win_rate ?? null)} · 品質 {formatDecimal(spilloverPocket?.avg_quality ?? null)} · 損益 {formatPct(spilloverPocket?.avg_pnl ?? null, 2, true)}
            </div>
            <div>
              Δ 勝率 {formatPct(spillover?.win_rate_delta_vs_exact ?? null, 1, true)} · Δ 品質 {formatDecimal(spillover?.avg_quality_delta_vs_exact ?? null, 3, true)} · Δ 損益 {formatPct(spillover?.avg_pnl_delta_vs_exact ?? null, 2, true)}
            </div>
            <div>
              回撤懲罰 {formatPct(spilloverPocket?.avg_drawdown_penalty ?? null)} · 深套 {formatPct(spilloverPocket?.avg_time_underwater ?? null)}
            </div>
          </div>
        </div>
      </div>

      {topShifts.length > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] uppercase tracking-[0.16em] text-amber-200/80">{PATHOLOGY_LABELS.top4hShifts}</div>
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
              <div className="text-[10px] uppercase tracking-[0.16em] text-sky-200/80">{patchSectionTitle}</div>
              <div className="mt-1 text-sm font-semibold text-sky-100">
                {patchProfileLabel}
              </div>
            </div>
            <div className="rounded-full border border-sky-500/30 bg-sky-400/10 px-2.5 py-1 text-[10px] uppercase tracking-[0.16em] text-sky-200">
              {formatPatchStatus(recommendedPatch.status)}
            </div>
          </div>
          <div className="space-y-1 text-[11px] leading-5 text-sky-50/90">
            <div>
              {PATHOLOGY_LABELS.currentSpillover} {recommendedPatch.spillover_regime_gate || "—"}
              {recommendedPatch.spillover_rows != null ? ` · 樣本 ${recommendedPatch.spillover_rows}` : ""}
            </div>
            <div>
              {PATHOLOGY_LABELS.referencePatch} {recommendedPatch.reference_patch_scope || recommendedPatch.spillover_regime_gate || "—"}
              {recommendedPatch.reference_source ? ` · 來源 ${recommendedPatch.reference_source}` : ""}
            </div>
            <div>
              樣本 {recommendedPatch.current_live_structure_bucket_rows ?? "—"}
              /
              {recommendedPatch.minimum_support_rows ?? "—"}
              {recommendedPatch.gap_to_minimum != null ? ` · gap ${recommendedPatch.gap_to_minimum}` : ""}
            </div>
            <div>
              {PATHOLOGY_LABELS.supportRoute} {supportRouteDisplayLabel || "—"}
              {supportGovernanceRouteLabel ? ` · ${PATHOLOGY_LABELS.governanceRoute} ${supportGovernanceRouteDisplayLabel}` : ""}
              {recommendedPatch.preferred_support_cohort ? ` · 參考 cohort ${recommendedPatch.preferred_support_cohort}` : ""}
            </div>
            {recommendedPatch.reason && <div>{recommendedPatch.reason}</div>}
            {recommendedPatch.recommended_action && <div>{PATHOLOGY_LABELS.nextAction} {recommendedPatch.recommended_action}</div>}
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
