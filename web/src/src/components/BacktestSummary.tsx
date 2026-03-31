/**
 * BacktestSummary — 回測摘要卡片
 */
import React from "react";

interface Props {
  finalEquity: number;
  initialCapital: number;
  totalTrades: number;
  winRate: number;
  profitLossRatio: number;
  maxDrawdown: number;
  totalReturn: number;
}

export default function BacktestSummary({
  finalEquity,
  initialCapital,
  totalTrades,
  winRate,
  profitLossRatio,
  maxDrawdown,
  totalReturn,
}: Props) {
  const isProfit = totalReturn >= 0;

  const stats = [
    {
      label: "初始資金",
      value: `$${initialCapital.toLocaleString()}`,
      color: "text-slate-300",
    },
    {
      label: "最終權益",
      value: `$${finalEquity.toLocaleString(undefined, { maximumFractionDigits: 2 })}`,
      color: "text-slate-200",
    },
    {
      label: "總報酬率",
      value: `${isProfit ? "+" : ""}${totalReturn.toFixed(2)}%`,
      color: isProfit ? "text-green-400" : "text-red-400",
    },
    {
      label: "交易次數",
      value: `${totalTrades}`,
      color: "text-slate-300",
    },
    {
      label: "勝率",
      value: `${winRate.toFixed(1)}%`,
      color: winRate >= 50 ? "text-green-400" : "text-orange-400",
    },
    {
      label: "盈虧比",
      value: `${profitLossRatio.toFixed(2)}`,
      color: profitLossRatio >= 1 ? "text-green-400" : "text-orange-400",
    },
    {
      label: "最大回撤",
      value: `${maxDrawdown.toFixed(2)}%`,
      color: maxDrawdown < 10 ? "text-green-400" : maxDrawdown < 20 ? "text-yellow-400" : "text-red-400",
    },
  ];

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
      <h3 className="text-sm font-semibold text-slate-400 mb-3">📊 回測摘要</h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {stats.map((stat) => (
          <div key={stat.label} className="text-center">
            <div className="text-xs text-slate-500 mb-1">{stat.label}</div>
            <div className={`text-lg font-mono font-bold ${stat.color}`}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
