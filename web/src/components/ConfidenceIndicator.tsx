/**
 * ConfidenceIndicator — 即時決策品質指示器
 * 將 live predictor 的 canonical decision-quality contract 直接顯示在 Dashboard。
 */
import React from "react";
import {
  humanizeCurrentLiveBlockerLabel,
  humanizeExecutionReason,
  humanizeFeatureKey,
  humanizeQ15BucketRootCauseAction,
  humanizeQ15BucketRootCauseLabel,
  humanizeQ15ComponentExperimentVerdictLabel,
  humanizeQ15FloorCrossVerdictLabel,
  humanizeRuntimeDetailText,
  humanizeStructureBucketLabel,
  humanizeSupportProgressStatusLabel,
} from "../utils/runtimeCopy";

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
  q35OverallVerdict?: string | null;
  q35RedesignVerdict?: string | null;
  q35RuntimeRemainingGapToFloor?: number | null;
  q35RecommendedMode?: string | null;
  q35RecommendedAction?: string | null;
  q35NextPatchTarget?: string | null;
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
  q35OverallVerdict,
  q35RedesignVerdict,
  q35RuntimeRemainingGapToFloor,
  q35RecommendedMode,
  q35RecommendedAction,
  q35NextPatchTarget,
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
  const supportStatusLabel = humanizeSupportProgressStatusLabel(supportStatus);
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
  const bucketKey = (currentLiveStructureBucket || "").toLowerCase();
  const currentLiveStructureBucketLabel = humanizeStructureBucketLabel(currentLiveStructureBucket || "—");
  const bestSingleComponentLabel = humanizeFeatureKey(bestSingleComponent || null, { preferShortLabel: true });
  const q15SupportAuditApplicable = bucketKey === "q15" || bucketKey.endsWith("|q15");
  const q35ScalingAuditApplicable = bucketKey === "q35" || bucketKey.endsWith("|q35");
  const q15FloorCrossLabel = q15SupportAuditApplicable
    ? humanizeQ15FloorCrossVerdictLabel(floorCrossVerdict || "—")
    : "目前不適用";
  const q15FloorCrossHint = q15SupportAuditApplicable
    ? `最佳單一元件 ${bestSingleComponentLabel}`
    : `目前 bucket ${currentLiveStructureBucketLabel}；q15 floor-cross drill-down 只保留 reference-only，不代表 /api/status 缺資料。`;
  const q15ComponentExperimentLabel = q15SupportAuditApplicable
    ? humanizeQ15ComponentExperimentVerdictLabel(componentExperimentVerdict || "—")
    : "僅供參考";
  const q15ComponentExperimentHint = q15SupportAuditApplicable
    ? `所需分數差 ${formatDecimal(bestSingleComponentRequiredScoreDelta, 4)}`
    : "目前 live row 已離開 q15 lane；請改看 current live blocker 與 current bucket root cause，而不是把 q15 experiment 空值誤讀成 blocker truth。";
  const q35ScalingVerdictLabel = q35ScalingAuditApplicable
    ? humanizeQ15BucketRootCauseLabel(q35OverallVerdict || "—")
    : "目前 bucket 非 q35";
  const q35ScalingVerdictHint = q35ScalingAuditApplicable
    ? `重設判讀 ${humanizeQ15BucketRootCauseLabel(q35RedesignVerdict || "—")} · 尚差 ${formatDecimal(q35RuntimeRemainingGapToFloor, 4)}`
    : `目前 bucket ${currentLiveStructureBucketLabel}；q35 scaling audit 只保留 reference-only，不代表 blocker 已解除。`;
  const q35ScalingActionLabel = q35ScalingAuditApplicable
    ? humanizeQ15BucketRootCauseAction(q35RecommendedMode || "—")
    : "僅供參考";
  const q35ScalingActionHint = q35ScalingAuditApplicable
    ? `下一個 patch ${humanizeRuntimeDetailText(q35NextPatchTarget || "—")} · ${humanizeRuntimeDetailText(q35RecommendedAction || "尚未提供 q35 audit action")}`
    : "目前 live row 不在 q35 lane；q35 公式 / 重設結論只保留背景研究用途。";

  return (
    <div className={`app-surface-card ${lv.bg}`}>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <div className="text-sm font-semibold text-slate-300">{lv.emoji} 即時決策品質</div>
          <div className="mt-1 text-xs text-slate-500">
            Dashboard 已改用現貨多單正式決策品質語義，不再顯示舊做空文案。
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold">
          <span className={`rounded-full border px-2 py-0.5 ${gateTone}`}>4H 關卡 {regimeGate || "—"}</span>
          <span className="rounded-full border border-sky-700/40 bg-sky-950/30 px-2 py-0.5 text-sky-300">
            進場分數 {formatDecimal(entryQuality, 2)}{entryQualityLabel ? ` · ${entryQualityLabel}` : ""}
          </span>
          <span className="rounded-full border border-slate-700/50 bg-slate-900/70 px-2 py-0.5 text-slate-200">
            層數 {layerLabel}
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
        <span className={lv.color}>多單勝率代理</span>
        <span className="text-slate-600">|</span>
        <span>
          {confidenceLevel === "HIGH"
            ? "> 0.70：允許金字塔進場"
            : confidenceLevel === "MEDIUM"
              ? "0.55~0.70：可留意，但仍受關卡 / 層數約束"
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
          <div className={`font-semibold ${q15PatchExecutionBlocked ? "text-amber-200" : "text-emerald-200"}`}>q15 精準樣本 bias50 執行期 patch 已套用</div>
          <div className={`mt-1 text-xs leading-5 ${q15PatchExecutionBlocked ? "text-amber-100/80" : "text-emerald-100/80"}`}>
            {q15PatchCapacityOpened
              ? "精準樣本已就緒，執行期目前對 current q15 live row 套用 support-aware bias50 component patch，且已打開 deployment capacity；若 signal 仍是 HOLD，代表容量已開但方向訊號仍不足（即 capacity opened but signal still HOLD）。"
              : "q15 patch 已經吃到 current live row，但 execution 仍被精準 live bucket blocker / 保護欄壓住；這代表 patch active 只證明 runtime floor-cross 元件已落地，不等於目前可部署（即 q15 patch 已經吃到 current live row，但 execution 仍被 exact live bucket blocker / guardrail 壓住）。"}
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
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">最近 50 筆解除視窗</div>
                  <div className="mt-1 font-medium text-white">{breakerWins ?? "—"} / {breakerWindow ?? "—"} 勝</div>
                  <div className="mt-1 text-slate-400">勝率 {formatPct(breakerRecentWinRate)} · 門檻 {formatPct(breakerFloor)}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">解除差距</div>
                  <div className="mt-1 font-medium text-white">至少還差 {breakerWinsGap ?? "—"} 勝</div>
                  <div className="mt-1 text-slate-400">所需勝場 {breakerRequiredWins ?? "—"}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">連敗解除條件</div>
                  <div className="mt-1 font-medium text-white">{breakerCurrentStreak ?? "—"} / {breakerStreakLimit ?? "—"}</div>
                  <div className="mt-1 text-slate-400">當前連敗維持低於 breaker 上限時才可解除。</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">操作員下一步</div>
                  <div className="mt-1 font-medium text-white">先等 canonical 1440m 最近 50 筆恢復</div>
                  <div className="mt-1 text-slate-400">不要把 support / component patch 當成 breaker release 替代品。</div>
                </div>
              </>
            ) : (
              <>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">精準 support</div>
                  <div className="mt-1 font-medium text-white">{supportRows ?? "—"} / {supportMinimum ?? "—"}</div>
                  <div className="mt-1 text-slate-400">狀態 {supportStatusLabel}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] tracking-wide text-slate-400">當前 bucket</div>
                  <div className="mt-1 font-medium text-white">{currentLiveStructureBucketLabel}</div>
                  <div className="mt-1 text-slate-400">距離最小樣本差 {supportGap ?? "—"}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">樣本變化</div>
                  <div className="mt-1 font-medium text-white">{supportDelta ?? "—"}</div>
                  <div className="mt-1 text-slate-400">下一輪應持續確認樣本是否繼續累積。</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">
                    {q35ScalingAuditApplicable ? "q35 縮放判讀" : "q15 floor-cross 合法性"}
                  </div>
                  <div className="mt-1 font-medium text-white">
                    {q35ScalingAuditApplicable ? q35ScalingVerdictLabel : q15FloorCrossLabel}
                  </div>
                  <div className="mt-1 text-slate-400">
                    {q35ScalingAuditApplicable ? q35ScalingVerdictHint : q15FloorCrossHint}
                  </div>
                </div>
                <div className="rounded-lg border border-white/10 bg-slate-950/30 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">
                    {q35ScalingAuditApplicable ? "q35 下一步" : "q15 元件實驗"}
                  </div>
                  <div className="mt-1 font-medium text-white">
                    {q35ScalingAuditApplicable ? q35ScalingActionLabel : q15ComponentExperimentLabel}
                  </div>
                  <div className="mt-1 text-slate-400">
                    {q35ScalingAuditApplicable ? q35ScalingActionHint : q15ComponentExperimentHint}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500">
        <span>版本： {decisionProfileVersion || "phase16_baseline_v2"}</span>
        <span>決策週期： {decisionQualityHorizonMinutes || 1440}m</span>
        {timestamp && <span>更新: {new Date(timestamp).toLocaleTimeString("zh-TW")}</span>}
      </div>
    </div>
  );
}
