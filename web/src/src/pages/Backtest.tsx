/**
 * Backtest — 回測頁面
 */
import { useState, useCallback } from "react";
import EquityCurve from "../components/EquityCurve";
import { fetchApi } from "../hooks/useApi";

interface BacktestResult {
  final_equity: number;
  initial_capital: number;
  total_trades: number;
  win_rate: number;
  profit_loss_ratio: number;
  max_drawdown: number;
  total_return: number;
  equity_curve: { timestamp: string; equity: number }[];
  trades: {
    timestamp: string;
    action: string;
    price: number;
    amount: number;
    confidence: number;
    pnl: number;
  }[];
}

export default function Backtest() {
  const [days, setDays] = useState(30);
  const [capital, setCapital] = useState(10000);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runBacktest = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchApi<BacktestResult>(
        `/api/backtest?days=${days}`
      );
      setResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [days]);

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-slate-100">🔬 回測引擎</h2>

      {/* Parameters */}
      <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-5">
        <h3 className="text-base font-semibold text-slate-300 mb-4">回測參數</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">回測天數</label>
            <input
              type="number"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              min={1}
              max={365}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">初始資金 (USDT)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              min={100}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={runBacktest}
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium px-4 py-2 rounded-lg transition-colors"
            >
              {loading ? "⏳ 回測中..." : "▶ 開始回測"}
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/20 border border-red-700/50 rounded-xl p-4 text-red-400">
          ⚠️ 回測失敗: {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Stats grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {[
              { label: "初始資金", value: `$${result.initial_capital.toLocaleString()}`, color: "text-slate-300" },
              { label: "最終權益", value: `$${result.final_equity.toLocaleString(undefined, { maximumFractionDigits: 2 })}`, color: "text-slate-200" },
              { label: "總報酬率", value: `${result.total_return >= 0 ? "+" : ""}${result.total_return.toFixed(2)}%`, color: result.total_return >= 0 ? "text-green-400" : "text-red-400" },
              { label: "交易次數", value: `${result.total_trades}`, color: "text-slate-300" },
              { label: "勝率", value: `${result.win_rate.toFixed(1)}%`, color: result.win_rate >= 50 ? "text-green-400" : "text-orange-400" },
              { label: "盈虧比", value: `${result.profit_loss_ratio.toFixed(2)}`, color: result.profit_loss_ratio >= 1 ? "text-green-400" : "text-orange-400" },
              { label: "最大回撤", value: `${result.max_drawdown.toFixed(2)}%`, color: result.max_drawdown < 10 ? "text-green-400" : "text-red-400" },
            ].map((stat) => (
              <div key={stat.label} className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-3 text-center">
                <div className="text-xs text-slate-500 mb-1">{stat.label}</div>
                <div className={`text-lg font-mono font-bold ${stat.color}`}>{stat.value}</div>
              </div>
            ))}
          </div>

          {/* Equity curve */}
          <EquityCurve data={result.equity_curve} initialCapital={result.initial_capital} />

          {/* Trade log */}
          {result.trades.length > 0 && (
            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
              <h3 className="text-sm font-semibold text-slate-400 mb-3">📋 交易記錄（最近 {result.trades.length} 筆）</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-500 text-left">
                      <th className="pb-2 pr-4">時間</th>
                      <th className="pb-2 pr-4">方向</th>
                      <th className="pb-2 pr-4">價格</th>
                      <th className="pb-2 pr-4">數量</th>
                      <th className="pb-2 pr-4">信心</th>
                      <th className="pb-2">盈虧</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((trade, i) => (
                      <tr key={i} className="border-t border-slate-800">
                        <td className="py-2 pr-4 text-slate-400 font-mono text-xs">
                          {new Date(trade.timestamp).toLocaleString("zh-TW", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}
                        </td>
                        <td className="py-2 pr-4">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            trade.action === "buy" ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400"
                          }`}>
                            {trade.action === "buy" ? "買入" : "賣出"}
                          </span>
                        </td>
                        <td className="py-2 pr-4 font-mono text-slate-300">
                          ${trade.price.toLocaleString()}
                        </td>
                        <td className="py-2 pr-4 font-mono text-slate-400">
                          {trade.amount}
                        </td>
                        <td className="py-2 pr-4 font-mono text-slate-400">
                          {(trade.confidence * 100).toFixed(0)}%
                        </td>
                        <td className={`py-2 font-mono font-bold ${trade.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                          {trade.pnl >= 0 ? "+" : ""}{trade.pnl.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
