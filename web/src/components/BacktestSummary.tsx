/**
 * BacktestSummary — 回測摘要卡片 (v2 with null safety)
 */
export default function BacktestSummary({
  finalEquity, initialCapital, totalTrades, winRate,
  profitLossRatio, maxDrawdown, totalReturn,
}: {
  finalEquity?: number; initialCapital?: number; totalTrades?: number;
  winRate?: number; profitLossRatio?: number; maxDrawdown?: number; totalReturn?: number;
}) {
  // Safe defaults
  const fe = finalEquity ?? 0;
  const ic = initialCapital ?? 0;
  const tt = totalTrades ?? 0;
  const wr = winRate ?? 0;
  const plr = profitLossRatio ?? 0;
  const md = maxDrawdown ?? 0;
  const tr = totalReturn ?? 0;
  const isProfit = tr >= 0;

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
      <h3 className="text-sm font-semibold text-slate-400 mb-3">📊 回測摘要</h3>
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
    </div>
  );
}
