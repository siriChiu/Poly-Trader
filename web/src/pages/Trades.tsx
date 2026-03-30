import React, { useState } from 'react'
import { useApi } from '../hooks/useApi'
import EquityCurve from '../components/EquityCurve'

interface Trade {
  id: number
  timestamp: string
  action: string
  price: number
  amount: number
  model_confidence: number
  pnl: number | null
}

export default function Trades() {
  const { data: trades, loading, error } = useApi<Trade[]>('/trades')

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-dark-400">
        載入交易歷史中...
      </div>
    )
  }

  if (error) {
    return (
      <div className="card text-sell">載入失敗: {error}</div>
    )
  }

  // 構建簡單的權益曲線（累積 PnL）
  const equityData = (trades || [])
    .slice()
    .reverse()
    .reduce<{ timestamp: string; equity: number }[]>((acc, t) => {
      const prev = acc.length > 0 ? acc[acc.length - 1].equity : 10000
      const pnl = t.pnl ?? 0
      acc.push({ timestamp: t.timestamp, equity: prev + pnl })
      return acc
    }, [])

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-dark-100">交易歷史</h2>

      {/* 權益曲線 */}
      <EquityCurve data={equityData} initialCapital={10000} />

      {/* 交易表格 */}
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-dark-400 border-b border-dark-700">
              <th className="text-left py-3 px-2">時間</th>
              <th className="text-left py-3 px-2">方向</th>
              <th className="text-right py-3 px-2">價格</th>
              <th className="text-right py-3 px-2">數量</th>
              <th className="text-right py-3 px-2">信心分數</th>
              <th className="text-right py-3 px-2">損益</th>
            </tr>
          </thead>
          <tbody>
            {trades && trades.length > 0 ? (
              trades.map((t) => (
                <tr key={t.id} className="border-b border-dark-800 hover:bg-dark-800/50 transition-colors">
                  <td className="py-3 px-2 font-mono text-dark-300">
                    {t.timestamp ? new Date(t.timestamp).toLocaleString('zh-TW') : '—'}
                  </td>
                  <td className="py-3 px-2">
                    <span className={`badge ${t.action === 'BUY' ? 'bg-buy/20 text-buy' : 'bg-sell/20 text-sell'}`}>
                      {t.action}
                    </span>
                  </td>
                  <td className="py-3 px-2 text-right font-mono">${t.price?.toLocaleString()}</td>
                  <td className="py-3 px-2 text-right font-mono">{t.amount?.toFixed(6)}</td>
                  <td className="py-3 px-2 text-right font-mono">
                    {(t.model_confidence * 100).toFixed(1)}%
                  </td>
                  <td className={`py-3 px-2 text-right font-mono ${
                    t.pnl !== null && t.pnl !== undefined
                      ? t.pnl >= 0 ? 'text-buy' : 'text-sell'
                      : 'text-dark-500'
                  }`}>
                    {t.pnl !== null && t.pnl !== undefined
                      ? `${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(2)}`
                      : '—'}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="text-center py-8 text-dark-500">
                  尚無交易記錄
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
