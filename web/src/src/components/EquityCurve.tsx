import React from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'

interface EquityPoint {
  timestamp: string
  equity: number
}

interface EquityCurveProps {
  data: EquityPoint[]
  initialCapital?: number
}

export default function EquityCurve({ data, initialCapital = 10000 }: EquityCurveProps) {
  if (!data || data.length === 0) {
    return (
      <div className="card flex items-center justify-center h-64 text-dark-500">
        尚無權益曲線數據
      </div>
    )
  }

  const finalEquity = data[data.length - 1]?.equity ?? initialCapital
  const totalReturn = ((finalEquity - initialCapital) / initialCapital) * 100
  const isProfit = totalReturn >= 0

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-dark-200">權益曲線</h3>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-dark-400">
            初始: <span className="text-dark-200 font-mono">${initialCapital.toLocaleString()}</span>
          </span>
          <span className="text-dark-400">
            最終: <span className="text-dark-200 font-mono">${finalEquity.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
          </span>
          <span className={`font-bold ${isProfit ? 'text-buy' : 'text-sell'}`}>
            {isProfit ? '+' : ''}{totalReturn.toFixed(2)}%
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={isProfit ? '#22c55e' : '#ef4444'} stopOpacity={0.3} />
              <stop offset="95%" stopColor={isProfit ? '#22c55e' : '#ef4444'} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="timestamp"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickFormatter={(v) => {
              const d = new Date(v)
              return `${d.getMonth() + 1}/${d.getDate()}`
            }}
          />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickFormatter={(v) => `$${Number(v).toLocaleString()}`}
            domain={['auto', 'auto']}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#f1f5f9',
            }}
            formatter={(value: number) => [`$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`, '權益']}
            labelFormatter={(label) => new Date(label as string).toLocaleString('zh-TW')}
          />
          <Area
            type="monotone"
            dataKey="equity"
            stroke={isProfit ? '#22c55e' : '#ef4444'}
            strokeWidth={2}
            fill="url(#equityGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
