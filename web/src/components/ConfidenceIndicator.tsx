/**
 * ConfidenceIndicator — 即時決策品質指示器
 * 將 live predictor 的 canonical decision-quality contract 直接顯示在 Dashboard。
 */
import React from "react";

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

  return (
    <div className={`rounded-xl border p-5 ${lv.bg}`}>
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

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500">
        <span>Profile: {decisionProfileVersion || "phase16_baseline_v2"}</span>
        <span>Horizon: {decisionQualityHorizonMinutes || 1440}m</span>
        {timestamp && <span>更新: {new Date(timestamp).toLocaleTimeString("zh-TW")}</span>}
      </div>
    </div>
  );
}
