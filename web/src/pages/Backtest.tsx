/**
 * Backtest — 回測頁面
 */
import { useState, useCallback } from "react";
import EquityCurve from "../components/EquityCurve";
import BacktestSummary from "../components/BacktestSummary";
import { fetchApi } from "../hooks/useApi";

interface BacktestResult {
  final_equity: number;
  initial_capital: number;
  total_trades: number;
  win_rate: number;
  profit_loss_ratio: number;
  max_drawdown: number;
  total_return: number;
  avg_entry_quality?: number | null;
  avg_allowed_layers?: number | null;
  dominant_regime_gate?: string | null;
  avg_expected_win_rate?: number | null;
  avg_expected_pyramid_quality?: number | null;
  avg_expected_drawdown_penalty?: number | null;
  avg_expected_time_underwater?: number | null;
  avg_decision_quality_score?: number | null;
  decision_quality_label?: string | null;
  decision_quality_sample_size?: number | null;
  decision_contract?: {
    target_col?: string | null;
    target_label?: string | null;
    sort_semantics?: string | null;
    decision_quality_horizon_minutes?: number | null;
  } | null;
  equity_curve: { timestamp: string; equity: number }[];
  trades: {
    timestamp: string;
    entry_timestamp?: string | null;
    action: string;
    price: number;
    amount: number;
    pnl: number;
    reason?: string | null;
    regime_gate?: string | null;
    entry_quality?: number | null;
    entry_quality_label?: string | null;
    allowed_layers?: number | null;
  }[];
}

const formatDecimal = (value?: number | null, digits = 2) => (
  typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—"
);

export default function Backtest() {
  const [days, setDays] = useState(30);
  const [capital, setCapital] = useState(10000);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasRun, setHasRun] = useState(false);

  const runBacktest = useCallback(async () => {
    setLoading(true);
    setError(null);
    setHasRun(true);
    try {
      const data = await fetchApi<BacktestResult>(
        `/api/backtest?days=${days}&initial_capital=${capital}`
      );
      setResult(data);
    } catch (e: any) {
      setError(e.message || "回測失敗");
    } finally {
      setLoading(false);
    }
  }, [days, capital]);

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
          <BacktestSummary
            finalEquity={result.final_equity}
            initialCapital={result.initial_capital}
            totalTrades={result.total_trades}
            winRate={result.win_rate}
            profitLossRatio={result.profit_loss_ratio}
            maxDrawdown={result.max_drawdown}
            totalReturn={result.total_return}
            avgEntryQuality={result.avg_entry_quality}
            avgAllowedLayers={result.avg_allowed_layers}
            dominantRegimeGate={result.dominant_regime_gate}
            avgDecisionQualityScore={result.avg_decision_quality_score}
            decisionQualityLabel={result.decision_quality_label}
            avgExpectedWinRate={result.avg_expected_win_rate}
            avgExpectedPyramidQuality={result.avg_expected_pyramid_quality}
            avgExpectedDrawdownPenalty={result.avg_expected_drawdown_penalty}
            avgExpectedTimeUnderwater={result.avg_expected_time_underwater}
            decisionQualitySampleSize={result.decision_quality_sample_size}
            decisionContract={result.decision_contract}
          />

          <div className="rounded-xl border border-slate-700/50 bg-slate-900/40 p-4 text-xs text-slate-400">
            <div className="font-semibold text-slate-300">🧭 回測排序語義</div>
            <div className="mt-1 leading-6">
              {result.decision_contract?.target_label || "Canonical Decision Quality"}
              {result.decision_contract?.sort_semantics ? ` · ${result.decision_contract.sort_semantics}` : ""}
            </div>
            <div className="mt-2 grid gap-2 md:grid-cols-4">
              <div className="rounded-lg bg-slate-950/40 px-3 py-2">
                <div className="text-slate-500">目標欄位</div>
                <div className="text-slate-200">{result.decision_contract?.target_col || "simulated_pyramid_win"}</div>
              </div>
              <div className="rounded-lg bg-slate-950/40 px-3 py-2">
                <div className="text-slate-500">Horizon</div>
                <div className="text-cyan-300">{result.decision_contract?.decision_quality_horizon_minutes || 1440}m</div>
              </div>
              <div className="rounded-lg bg-slate-950/40 px-3 py-2">
                <div className="text-slate-500">主導 gate</div>
                <div className="text-emerald-300">{result.dominant_regime_gate || "—"}</div>
              </div>
              <div className="rounded-lg bg-slate-950/40 px-3 py-2">
                <div className="text-slate-500">DQ 樣本</div>
                <div className="text-slate-200">{result.decision_quality_sample_size ?? "—"}</div>
              </div>
            </div>
          </div>

          {/* Equity curve */}
          <EquityCurve data={result.equity_curve} initialCapital={result.initial_capital} />

          {/* Trade log */}
          {result.trades.length > 0 && (
            <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-slate-300">📋 交易記錄（最近 {result.trades.length} 筆）</h3>
                <div className="text-[11px] text-slate-500">退出交易同時附帶 entry gate / quality / layers，避免表格退回成只有 ROI/PnL 的舊語義。</div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="pb-2 pr-4">進場 / 出場</th>
                      <th className="pb-2 pr-4">方向 / 原因</th>
                      <th className="pb-2 pr-4">Gate / Layers</th>
                      <th className="pb-2 pr-4">Entry Quality</th>
                      <th className="pb-2 pr-4">價格 / 數量</th>
                      <th className="pb-2">盈虧</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((trade, i) => (
                      <tr key={i} className="border-t border-slate-800 align-top">
                        <td className="py-2 pr-4 text-[11px] text-slate-400 font-mono">
                          <div>{trade.entry_timestamp ? new Date(trade.entry_timestamp).toLocaleString("zh-TW", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—"}</div>
                          <div className="mt-1 text-slate-500">→ {new Date(trade.timestamp).toLocaleString("zh-TW", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}</div>
                        </td>
                        <td className="py-2 pr-4">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            trade.action === "buy" ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400"
                          }`}>
                            {trade.action === "buy" ? "買入" : "賣出"}
                          </span>
                          <div className="mt-1 text-[11px] text-slate-500">{trade.reason || "—"}</div>
                        </td>
                        <td className="py-2 pr-4 text-[11px]">
                          <div className="text-emerald-300">{trade.regime_gate || "—"}</div>
                          <div className="mt-1 text-slate-500">Layers {typeof trade.allowed_layers === "number" ? trade.allowed_layers.toFixed(2) : "—"}</div>
                        </td>
                        <td className="py-2 pr-4 text-[11px]">
                          <div className="text-cyan-300">{trade.entry_quality_label || "—"}</div>
                          <div className="mt-1 text-slate-500">score {formatDecimal(trade.entry_quality)}</div>
                        </td>
                        <td className="py-2 pr-4 text-[11px] font-mono">
                          <div className="text-slate-200">${trade.price.toLocaleString()}</div>
                          <div className="mt-1 text-slate-500">qty {trade.amount}</div>
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
