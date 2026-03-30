import React, { useState } from 'react'
import { useApiPost, fetchApi } from '../hooks/useApi'
import EquityCurve from '../components/EquityCurve'

interface BacktestResult {
  final_equity: number
  initial_capital: number
  total_trades: number
  equity_curve: { timestamp: string; equity: number }[]
  trades: any[]
}

export default function Backtest() {
  const [days, setDays] = useState(30)
  const [capital, setCapital] = useState(10000)
  const [threshold, setThreshold] = useState(0.7)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runBacktest = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchApi<BacktestResult>(
        `/backtest?days=${days}&initial_capital=${capital}&confidence_threshold=${threshold}`
      )
      setResult(data)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const totalReturn = result
    ? ((result.final_equity - result.initial_capital) / result.initial_capital * 100)
    : 0

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-dark-100">回測引擎</h2>

      {/* 參數設置 */}
      <div className="card">
        <h3 className="text-lg font-semibold text-dark-200 mb-4">回測參數</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-dark-400 mb-1">回測天數</label>
            <input
              type="number"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              min={1}
              max={365}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-dark-100 focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-1">初始資金 (USDT)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              min={100}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-dark-100 focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-1">信心閾值</label>
            <input
              type="number"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              min={0}
              max={1}
              step={0.05}
              className="w-full bg-dark-700 border border-dark-600 rounded-lg px-3 py-2 text-dark-100 focus:outline-none focus:border-accent"
            />
          </div>
        </div>
        <button
          onClick={runBacktest}
          disabled={loading}
          className="btn-primary mt-4"
        >
          {loading ? '回測中...' : '▶ 開始回測'}
        </button>
      </div>

      {/* 錯誤 */}
      {error && (
        <div className="card border-sell text-sell">
          回測失敗: {error}
        </div>
      )}

      {/* 結果 */}
      {result && (
        <div className="space-y-4">
          {/* 統計摘要 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card text-center">
              <div className="text-xs text-dark-400">初始資金</div>
              <div className="text-xl font-mono font-bold text-dark-200">
                ${result.initial_capital.toLocaleString()}
              </div>
            </div>
            <div className="card text-center">
              <div className="text-xs text-dark-400">最終權益</div>
              <div className="text-xl font-mono font-bold text-dark-200">
                ${result.final_equity.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </div>
            </div>
            <div className="card text-center">
              <div className="text-xs text-dark-400">總報酬率</div>
              <div className={`text-xl font-mono font-bold ${totalReturn >= 0 ? 'text-buy' : 'text-sell'}`}>
                {totalReturn >= 0 ? '+' : ''}{totalReturn.toFixed(2)}%
              </div>
            </div>
            <div className="card text-center">
              <div className="text-xs text-dark-400">交易次數</div>
              <div className="text-xl font-mono font-bold text-dark-200">
                {result.total_trades}
              </div>
            </div>
          </div>

          {/* 權益曲線 */}
          <EquityCurve data={result.equity_curve} initialCapital={result.initial_capital} />
        </div>
      )}
    </div>
  )
}
