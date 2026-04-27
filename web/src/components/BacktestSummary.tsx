/**
 * BacktestSummary — Dashboard backtest card with canonical decision-quality context.
 */
import { humanizeRegimeGateLabel } from "../utils/runtimeCopy";

const formatPct = (value?: number | null) => (
  typeof value === "number" && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "—"
);

const formatDecimal = (value?: number | null, digits = 3) => (
  typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—"
);

export default function BacktestSummary({
  finalEquity, initialCapital, totalTrades, winRate,
  profitLossRatio, maxDrawdown, totalReturn,
  avgEntryQuality, avgAllowedLayers, dominantRegimeGate,
  avgDecisionQualityScore, decisionQualityLabel,
  avgExpectedWinRate, avgExpectedPyramidQuality,
  avgExpectedDrawdownPenalty, avgExpectedTimeUnderwater,
  decisionQualitySampleSize, decisionContract,
}: {
  finalEquity?: number; initialCapital?: number; totalTrades?: number;
  winRate?: number; profitLossRatio?: number; maxDrawdown?: number; totalReturn?: number;
  avgEntryQuality?: number | null; avgAllowedLayers?: number | null; dominantRegimeGate?: string | null;
  avgDecisionQualityScore?: number | null; decisionQualityLabel?: string | null;
  avgExpectedWinRate?: number | null; avgExpectedPyramidQuality?: number | null;
  avgExpectedDrawdownPenalty?: number | null; avgExpectedTimeUnderwater?: number | null;
  decisionQualitySampleSize?: number | null;
  decisionContract?: {
    target_col?: string | null;
    target_label?: string | null;
    sort_semantics?: string | null;
    decision_quality_horizon_minutes?: number | null;
  } | null;
}) {
  const fe = finalEquity ?? 0;
  const ic = initialCapital ?? 0;
  const tt = totalTrades ?? 0;
  const wr = winRate ?? 0;
  const plr = profitLossRatio ?? 0;
  const md = maxDrawdown ?? 0;
  const tr = totalReturn ?? 0;
  const isProfit = tr >= 0;
  const dqAvailable = avgDecisionQualityScore !== null && avgDecisionQualityScore !== undefined;

  return (
    <div className="app-surface-card space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-300">📊 回測摘要</h3>
          <div className="mt-1 text-xs text-slate-500">
            Dashboard 回測卡現已補上正式決策品質語義，不再只剩 ROI / 勝率 / PF。
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold">
          <span className="rounded-full border border-slate-700/50 bg-slate-900/70 px-2 py-0.5 text-slate-200">
            {decisionContract?.target_col || "simulated_pyramid_win"}
          </span>
          <span className="rounded-full border border-cyan-700/40 bg-cyan-950/30 px-2 py-0.5 text-cyan-300">
            決策視窗 {decisionContract?.decision_quality_horizon_minutes || 1440}m
          </span>
          <span className="rounded-full border border-emerald-700/40 bg-emerald-950/30 px-2 py-0.5 text-emerald-300">
            主閘門 {humanizeRegimeGateLabel(dominantRegimeGate || null)}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {[
          { label: "初始資金", value: `$${ic.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: "text-slate-300" },
          { label: "最終權益", value: `$${fe.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: "text-slate-200" },
          { label: "總報酬率", value: `${isProfit ? "+" : ""}${tr.toFixed(2)}%`, color: isProfit ? "text-green-400" : "text-red-400" },
          { label: "交易次數", value: `${tt}`, color: "text-slate-300" },
          { label: "勝率", value: `${wr.toFixed(1)}%`, color: wr >= 50 ? "text-green-400" : "text-orange-400" },
          { label: "盈虧比", value: `${plr.toFixed(2)}`, color: plr >= 1 ? "text-green-400" : "text-orange-400" },
          { label: "最大回撤", value: `${md.toFixed(2)}%`, color: md < 10 ? "text-green-400" : md < 20 ? "text-yellow-400" : "text-red-400" },
        ].map((stat) => (
          <div key={stat.label} className="text-center">
            <div className="text-xs text-slate-500 mb-1">{stat.label}</div>
            <div className={`text-sm font-mono font-bold ${stat.color}`}>{stat.value}</div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-700/50 bg-slate-900/40 p-3 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-xs font-semibold text-slate-300">正式決策品質</div>
            <div className="mt-1 text-[11px] text-slate-500">
              {decisionContract?.target_label || "正式決策品質"}
              {decisionContract?.sort_semantics ? ` · ${decisionContract.sort_semantics}` : ""}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-slate-500">DQ</div>
            <div className="text-lg font-bold text-cyan-300">
              {dqAvailable ? `${formatDecimal(avgDecisionQualityScore)}${decisionQualityLabel ? ` (${decisionQualityLabel})` : ""}` : "—"}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { label: "預期勝率", value: formatPct(avgExpectedWinRate), color: "text-emerald-300" },
            { label: "預期品質", value: formatDecimal(avgExpectedPyramidQuality), color: "text-sky-300" },
            { label: "回撤懲罰", value: formatPct(avgExpectedDrawdownPenalty), color: "text-amber-300" },
            { label: "深套時間", value: formatPct(avgExpectedTimeUnderwater), color: "text-orange-300" },
            { label: "平均進場品質", value: formatDecimal(avgEntryQuality, 2), color: "text-slate-200" },
            { label: "平均允許層數", value: typeof avgAllowedLayers === "number" ? avgAllowedLayers.toFixed(2) : "—", color: "text-slate-200" },
          ].map((stat) => (
            <div key={stat.label} className="rounded-lg border border-slate-800/80 bg-slate-950/30 px-3 py-2">
              <div className="text-[11px] text-slate-500">{stat.label}</div>
              <div className={`mt-1 text-sm font-semibold ${stat.color}`}>{stat.value}</div>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500">
          <span>DQ 樣本: {typeof decisionQualitySampleSize === "number" ? decisionQualitySampleSize : "—"}</span>
          <span>主導閘門：{humanizeRegimeGateLabel(dominantRegimeGate || null)}</span>
        </div>
      </div>
    </div>
  );
}
