/**
 * ConfidenceIndicator — 即時決策品質指示器
 * 將 live predictor 的 canonical decision-quality contract 直接顯示在 Dashboard。
 */
import React from "react";
import { humanizeCurrentLiveBlockerLabel, humanizeExecutionReason } from "../utils/runtimeCopy";

interface Props {
  confidence: number;        // 0~1 long-win probability proxy
  signal: string;            // BUY / HOLD / ABSTAIN / CIRCUIT_BREAKER
  confidenceLevel: string;   // HIGH / MEDIUM / LOW / ABSTAIN / CIRCUIT_BREAKER
  shouldTrade: boolean;
  regimeGate?: string | null;
  entryQuality?: number | null;
  entryQualityLabel?: string | null;
  allowedLayers?: number | null;
  decisionQualityScore?: number | null;
  decisionQualityLabel?: string | null;
  expectedWinRate?: number | null;
  expectedPyramidQuality?: number | null;
  expectedDrawdownPenalty?: number | null;
  expectedTimeUnderwater?: number | null;
  decisionQualitySampleSize?: number | null;
  decisionQualityHorizonMinutes?: number | null;
  decisionProfileVersion?: string | null;
  currentLiveStructureBucket?: string | null;
  deploymentBlocker?: string | null;
  deploymentBlockerReason?: string | null;
  deploymentBlockerDetails?: {
    recent_window?: {
      window_size?: number | null;
      wins?: number | null;
      win_rate?: number | null;
      floor?: number | null;
    } | null;
    release_condition?: {
      streak_must_be_below?: number | null;
      current_streak?: number | null;
      recent_window?: number | null;
      recent_win_rate_must_be_at_least?: number | null;
      current_recent_window_win_rate?: number | null;
      current_recent_window_wins?: number | null;
      required_recent_window_wins?: number | null;
      additional_recent_window_wins_needed?: number | null;
    } | null;
  } | null;
  supportProgress?: {
    status?: string | null;
    current_rows?: number | null;
    minimum_support_rows?: number | null;
    gap_to_minimum?: number | null;
    delta_vs_previous?: number | null;
  } | null;
  minimumSupportRows?: number | null;
  currentLiveStructureBucketGapToMinimum?: number | null;
  floorCrossVerdict?: string | null;
  bestSingleComponent?: string | null;
  bestSingleComponentRequiredScoreDelta?: number | null;
  componentExperimentVerdict?: string | null;
  q15ExactSupportedComponentPatchApplied?: boolean | null;
  timestamp?: string;
}

const formatPct = (value?: number | null) => (
  typeof value === "number" && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "—"
);

const formatDecimal = (value?: number | null, digits = 3) => (
  typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—"
);

export default function ConfidenceIndicator({
  confidence,
  signal,
  confidenceLevel,
  shouldTrade,
  regimeGate,
  entryQuality,
  entryQualityLabel,
  allowedLayers,
  decisionQualityScore,
  decisionQualityLabel,
  expectedWinRate,
  expectedPyramidQuality,
  expectedDrawdownPenalty,
  expectedTimeUnderwater,
  decisionQualitySampleSize,
  decisionQualityHorizonMinutes,
  decisionProfileVersion,
  currentLiveStructureBucket,
  deploymentBlocker,
  deploymentBlockerReason,
  deploymentBlockerDetails,
  supportProgress,
  minimumSupportRows,
  currentLiveStructureBucketGapToMinimum,
  floorCrossVerdict,
  bestSingleComponent,
  bestSingleComponentRequiredScoreDelta,
  componentExperimentVerdict,
  q15ExactSupportedComponentPatchApplied,
  timestamp,
}: Props) {
  const pct = Math.round(confidence * 100);
  const barColor = pct >= 70 ? "bg-emerald-500" : pct >= 55 ? "bg-cyan-500" : pct >= 45 ? "bg-amber-500" : "bg-slate-500";

  const levelConfig: Record<string, { color: string; bg: string; label: string; emoji: string }> = {
    HIGH: { color: "text-emerald-300", bg: "bg-emerald-950/30 border-emerald-700/40", label: "高品質 long setup", emoji: "🎯" },
    MEDIUM: { color: "text-cyan-300", bg: "bg-cyan-950/25 border-cyan-700/40", label: "條件接近可用", emoji: "🧭" },
    LOW: { color: "text-amber-300", bg: "bg-amber-950/25 border-amber-700/40", label: "品質不足，先觀望", emoji: "⏸️" },
    ABSTAIN: { color: "text-slate-300", bg: "bg-slate-900/70 border-slate-700/50", label: "結構不清，暫停進場", emoji: "🛑" },
    CIRCUIT_BREAKER: { color: "text-rose-300", bg: "bg-rose-950/30 border-rose-700/40", label: "保護模式啟動", emoji: "🚨" },
  };

  const signalConfig: Record<string, { color: string; label: string }> = {
    BUY: { color: "text-emerald-300", label: "可分層進場" },
    HOLD: { color: "text-slate-300", label: "先觀望" },
    ABSTAIN: { color: "text-slate-300", label: "暫停交易" },
    CIRCUIT_BREAKER: { color: "text-rose-300", label: "停手機制" },
  };

  const gateConfig: Record<string, string> = {
    ALLOW: "bg-emerald-950/40 text-emerald-300 border-emerald-700/40",
    CAUTION: "bg-amber-950/30 text-amber-300 border-amber-700/40",
    BLOCK: "bg-rose-950/30 text-rose-300 border-rose-700/40",
  };

  const lv = levelConfig[confidenceLevel] || levelConfig.LOW;
  const sig = signalConfig[signal] || signalConfig.HOLD;
  const gateTone = gateConfig[regimeGate || ""] || "bg-slate-900/60 text-slate-300 border-slate-700/50";
  const layerLabel = typeof allowedLayers === "number" && Number.isFinite(allowedLayers)
    ? `${allowedLayers.toFixed(0)} / 3 層`
    : "—";

  const stats = [
    { label: "預期勝率", value: formatPct(expectedWinRate), color: "text-emerald-300" },
    { label: "DQ", value: `${formatDecimal(decisionQualityScore)}${decisionQualityLabel ? ` (${decisionQualityLabel})` : ""}`, color: "text-cyan-300" },
    { label: "預期品質", value: formatDecimal(expectedPyramidQuality), color: "text-sky-300" },
    { label: "回撤懲罰", value: formatPct(expectedDrawdownPenalty), color: "text-amber-300" },
    { label: "深套時間", value: formatPct(expectedTimeUnderwater), color: "text-orange-300" },
    { label: "校準樣本", value: typeof decisionQualitySampleSize === "number" ? `${decisionQualitySampleSize}` : "—", color: "text-slate-200" },
  ];

  const supportStatus = supportProgress?.status || null;
  const supportRows = typeof supportProgress?.current_rows === "number"
    ? supportProgress.current_rows
    : null;
  const supportMinimum = typeof supportProgress?.minimum_support_rows === "number"
    ? supportProgress.minimum_support_rows
    : (typeof minimumSupportRows === "number" ? minimumSupportRows : null);
  const supportGap = typeof supportProgress?.gap_to_minimum === "number"
    ? supportProgress.gap_to_minimum
    : (typeof currentLiveStructureBucketGapToMinimum === "number" ? currentLiveStructureBucketGapToMinimum : null);
  const supportDelta = typeof supportProgress?.delta_vs_previous === "number" ? supportProgress.delta_vs_previous : null;
  const q15PatchExecutionBlocked = Boolean(
    q15ExactSupportedComponentPatchApplied
    && (deploymentBlocker || (typeof allowedLayers === "number" && allowedLayers <= 0))
  );
  const q15PatchCapacityOpened = Boolean(
    q15ExactSupportedComponentPatchApplied
    && !q15PatchExecutionBlocked
    && typeof allowedLayers === "number"
    && allowedLayers > 0
  );
  const breakerRecentWindow = deploymentBlockerDetails?.recent_window ?? null;
  const breakerRelease = deploymentBlockerDetails?.release_condition ?? null;
  const circuitBreakerActive = deploymentBlocker === "circuit_breaker_active";
  const breakerWindow = typeof breakerRelease?.recent_window === "number"
    ? breakerRelease.recent_window
    : (typeof breakerRecentWindow?.window_size === "number" ? breakerRecentWindow.window_size : null);
  const breakerWins = typeof breakerRelease?.current_recent_window_wins === "number"
    ? breakerRelease.current_recent_window_wins
    : (typeof breakerRecentWindow?.wins === "number" ? breakerRecentWindow.wins : null);
  const breakerRequiredWins = typeof breakerRelease?.required_recent_window_wins === "number"
    ? breakerRelease.required_recent_window_wins
    : null;
  const breakerWinsGap = typeof breakerRelease?.additional_recent_window_wins_needed === "number"
    ? breakerRelease.additional_recent_window_wins_needed
    : null;
  const breakerRecentWinRate = typeof breakerRelease?.current_recent_window_win_rate === "number"
    ? breakerRelease.current_recent_window_win_rate
    : (typeof breakerRecentWindow?.win_rate === "number" ? breakerRecentWindow.win_rate : null);
  const breakerFloor = typeof breakerRelease?.recent_win_rate_must_be_at_least === "number"
    ? breakerRelease.recent_win_rate_must_be_at_least
    : (typeof breakerRecentWindow?.floor === "number" ? breakerRecentWindow.floor : null);
  const breakerCurrentStreak = typeof breakerRelease?.current_streak === "number"
    ? breakerRelease.current_streak
    : null;
  const breakerStreakLimit = typeof breakerRelease?.streak_must_be_below === "number"
    ? breakerRelease.streak_must_be_below
    : null;

  return (
    <div className={`app-surface-card ${lv.bg}`}>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <div className="text-sm font-semibold text-slate-300">{lv.emoji} 即時決策品質</div>
          <div className="mt-1 text-xs text-slate-500">
            Dashboard 已改用 spot-long canonical decision-quality 語義，不再顯示舊做空/short copy。
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold">
          <span className={`rounded-full border px-2 py-0.5 ${gateTone}`}>4H Gate {regimeGate || "—"}</span>
          <span className="rounded-full border border-sky-700/40 bg-sky-950/30 px-2 py-0.5 text-sky-300">
            Entry {formatDecimal(entryQuality, 2)}{entryQualityLabel ? ` · ${entryQualityLabel}` : ""}
          </span>
          <span className="rounded-full border border-slate-700/50 bg-slate-900/70 px-2 py-0.5 text-slate-200">
            Layers {layerLabel}
          </span>
          {shouldTrade && (
            <span className="rounded-full border border-emerald-600/50 bg-emerald-600/20 px-2 py-0.5 text-emerald-200 animate-pulse">
              可執行
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-end gap-3 mb-2">
        <span className={`text-5xl font-mono font-bold ${lv.color}`}>{pct}%</span>
        <div>
          <div className={`text-lg font-bold ${sig.color}`}>{sig.label}</div>
          <div className="text-sm text-slate-500">{lv.label}</div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
        <span className={lv.color}>long-win proxy</span>
        <span className="text-slate-600">|</span>
        <span>
          {confidenceLevel === "HIGH"
            ? "> 0.70：允許金字塔進場"
            : confidenceLevel === "MEDIUM"
              ? "0.55~0.70：可留意，但仍受 gate / layers 約束"
              : confidenceLevel === "CIRCUIT_BREAKER"
                ? "保護模式：暫停交易"
                : "< 0.55：先觀望"}
        </span>
      </div>

      <div className="mt-3 h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-3">
        {stats.map((stat) => (
          <div key={stat.label} className="rounded-lg border border-slate-800/80 bg-slate-950/40 px-3 py-2">
            <div className="text-[11px] text-slate-500">{stat.label}</div>
            <div className={`mt-1 text-sm font-semibold ${stat.color}`}>{stat.value}</div>
          </div>
        ))}
      </div>

      {q15ExactSupportedComponentPatchApplied && (
        <div className={`mt-4 rounded-xl border px-4 py-3 text-sm ${q15PatchExecutionBlocked ? "border-amber-700/40 bg-amber-950/20 text-amber-100" : "border-emerald-700/40 bg-emerald-950/20 text-emerald-100"}`}>
          <div className={`font-semibold ${q15PatchExecutionBlocked ? "text-amber-200" : "text-emerald-200"}`}>q15 exact-supported bias50 runtime patch active</div>
          <div className={`mt-1 text-xs leading-5 ${q15PatchExecutionBlocked ? "text-amber-100/80" : "text-emerald-100/80"}`}>
            {q15PatchCapacityOpened
              ? "support 已解，runtime 目前對 current q15 live row 套用 support-aware bias50 component patch，且已開出 deployment capacity；若 signal 仍是 HOLD，代表 capacity opened but signal still HOLD。"
              : "q15 patch 已經吃到 current live row，但 execution 仍被 exact live bucket blocker / guardrail 壓住；這代表 patch active 只證明 runtime floor-cross 元件已落地，不等於目前可部署。"}
          </div>
        </div>
      )}

      {deploymentBlocker && (
        <div className="mt-4 rounded-xl border border-amber-700/40 bg-amber-950/20 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-sm font-semibold text-amber-200">目前 blocker</div>
              <div className="mt-1 text-xs leading-5 text-amber-100/80">
                {humanizeExecutionReason(deploymentBlockerReason || deploymentBlocker)}
              </div>
            </div>
            <div className="rounded-full border border-amber-700/50 bg-amber-950/40 px-2 py-0.5 text-[11px] font-semibold text-amber-200">
              {humanizeCurrentLiveBlockerLabel(deploymentBlocker)}
            </div>
          </div>

          <div className={`mt-3 grid gap-3 text-xs ${circuitBreakerActive ? "md:grid-cols-2 xl:grid-cols-4" : "md:grid-cols-2 xl:grid-cols-5"}`}>
            {circuitBreakerActive ? (
              <>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">recent 50 release window</div>
                  <div className="mt-1 font-medium text-white">{breakerWins ?? "—"} / {breakerWindow ?? "—"} wins</div>
                  <div className="mt-1 text-slate-400">win rate {formatPct(breakerRecentWinRate)} · floor {formatPct(breakerFloor)}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">release gap</div>
                  <div className="mt-1 font-medium text-white">至少還差 {breakerWinsGap ?? "—"} 勝</div>
                  <div className="mt-1 text-slate-400">required wins {breakerRequiredWins ?? "—"}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">streak release condition</div>
                  <div className="mt-1 font-medium text-white">{breakerCurrentStreak ?? "—"} / {breakerStreakLimit ?? "—"}</div>
                  <div className="mt-1 text-slate-400">release when current streak stays below the breaker limit.</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">operator next step</div>
                  <div className="mt-1 font-medium text-white">先等 canonical 1440m 最近 50 筆恢復</div>
                  <div className="mt-1 text-slate-400">不要把 support / component patch 當成 breaker release 替代品。</div>
                </div>
              </>
            ) : (
              <>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">exact support</div>
                  <div className="mt-1 font-medium text-white">{supportRows ?? "—"} / {supportMinimum ?? "—"}</div>
                  <div className="mt-1 text-slate-400">status {supportStatus || "unknown"}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">current live bucket</div>
                  <div className="mt-1 font-medium text-white">{currentLiveStructureBucket || "—"}</div>
                  <div className="mt-1 text-slate-400">gap to minimum {supportGap ?? "—"}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">support delta</div>
                  <div className="mt-1 font-medium text-white">{supportDelta ?? "—"}</div>
                  <div className="mt-1 text-slate-400">下一輪應持續 machine-check rows 累積。</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">floor-cross legality</div>
                  <div className="mt-1 font-medium text-white">{floorCrossVerdict || "—"}</div>
                  <div className="mt-1 text-slate-400">best single component {bestSingleComponent || "—"}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">component experiment</div>
                  <div className="mt-1 font-medium text-white">{componentExperimentVerdict || "—"}</div>
                  <div className="mt-1 text-slate-400">required score delta {formatDecimal(bestSingleComponentRequiredScoreDelta, 4)}</div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500">
        <span>Profile: {decisionProfileVersion || "phase16_baseline_v2"}</span>
        <span>Horizon: {decisionQualityHorizonMinutes || 1440}m</span>
        {timestamp && <span>更新: {new Date(timestamp).toLocaleTimeString("zh-TW")}</span>}
      </div>
    </div>
  );
}
