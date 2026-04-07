import React from 'react'
import { useApi } from '../hooks/useApi'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts'

interface ValidationDetail {
  name: string
  ic: number | null
  null_ratio: number
  status: 'ok' | 'warning' | 'critical'
}

interface ValidationData {
  status: 'ok' | 'warning' | 'critical'
  issues: string[]
  details: Record<string, ValidationDetail>
  needs_hat_meeting: boolean
  sample_count: number
  timestamp: string
}

const STATUS_COLORS = {
  ok: '#22c55e',
  warning: '#eab308',
  critical: '#ef4444',
}

const STATUS_ICONS = {
  ok: '✅',
  warning: '⚠️',
  critical: '🔴',
}

export default function Validation() {
  const { data, loading, error, refresh } = useApi<ValidationData>('/validation')

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-dark-400">
        載入特徵驗證中...
      </div>
    )
  }

  if (error) {
    return (
      <div className="card text-sell">
        載入失敗: {error}
        <button onClick={refresh} className="ml-4 btn-primary text-sm">重試</button>
      </div>
    )
  }

  if (!data) return null

  // IC 條形圖數據
  const icData = Object.entries(data.details).map(([key, detail]) => ({
    name: detail.name.split('·')[0]?.trim() || key,
    fullName: detail.name,
    ic: detail.ic ?? 0,
    status: detail.status,
  }))

  // 分位數勝率熱圖（簡化為條形圖）
  const nullData = Object.entries(data.details).map(([key, detail]) => ({
    name: detail.name.split('·')[0]?.trim() || key,
    fullName: detail.name,
    nullRatio: detail.null_ratio * 100,
    status: detail.status,
  }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-dark-100">特徵有效性分析</h2>
        <div className="flex items-center gap-2">
          <span className={`badge ${
            data.status === 'ok' ? 'bg-buy/20 text-buy' :
            data.status === 'warning' ? 'bg-hold/20 text-hold' :
            'bg-sell/20 text-sell'
          }`}>
            {STATUS_ICONS[data.status]} {data.status.toUpperCase()}
          </span>
          <span className="text-xs text-dark-400">樣本數: {data.sample_count}</span>
        </div>
      </div>

      {/* 概覽卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {Object.entries(data.details).map(([key, detail]) => (
          <div key={key} className={`card border ${
            detail.status === 'ok' ? 'border-buy/30' :
            detail.status === 'warning' ? 'border-hold/30' :
            'border-sell/30'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <span>{STATUS_ICONS[detail.status]}</span>
              <span className="text-sm font-semibold text-dark-200">{detail.name}</span>
            </div>
            <div className="text-xs text-dark-400">
              IC: <span className="font-mono text-dark-200">
                {detail.ic !== null ? detail.ic.toFixed(4) : 'N/A'}
              </span>
            </div>
            <div className="text-xs text-dark-400">
              空值率: <span className="font-mono text-dark-200">
                {(detail.null_ratio * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* IC 條形圖 */}
      <div className="card">
        <h3 className="text-lg font-semibold text-dark-200 mb-4">信息係數 (IC) 條形圖</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={icData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
                color: '#f1f5f9',
              }}
              formatter={(value: number, name: string, props: any) => [
                value.toFixed(4),
                props.payload.fullName,
              ]}
            />
            <Bar dataKey="ic" radius={[4, 4, 0, 0]}>
              {icData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={STATUS_COLORS[entry.status]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-dark-500 mt-2">
          IC &gt; 0.03 (綠) = 有效 | 0.01-0.03 (黃) = 偏弱 | &lt; 0.01 (紅) = 需汰換
        </p>
      </div>

      {/* 空值率條形圖 */}
      <div className="card">
        <h3 className="text-lg font-semibold text-dark-200 mb-4">數據完整性（空值率）</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={nullData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} unit="%" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
                color: '#f1f5f9',
              }}
              formatter={(value: number) => [`${value.toFixed(1)}%`, '空值率']}
            />
            <Bar dataKey="nullRatio" radius={[4, 4, 0, 0]}>
              {nullData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.nullRatio > 50 ? '#ef4444' : entry.nullRatio > 20 ? '#eab308' : '#22c55e'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 問題列表 */}
      {data.issues.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-dark-200 mb-3">發現的問題</h3>
          <ul className="space-y-2">
            {data.issues.map((issue, i) => (
              <li key={i} className="text-sm text-dark-300 flex items-start gap-2">
                <span className="text-dark-500">•</span>
                <span>{issue}</span>
              </li>
            ))}
          </ul>
          {data.needs_hat_meeting && (
            <div className="mt-4 p-3 bg-sell/10 border border-sell/30 rounded-lg text-sm text-sell">
              🎩 觸發六帽會議：部分特徵預測力不足，需要重新評估或汰換
            </div>
          )}
        </div>
      )}

      {/* 時間戳 */}
      <div className="text-xs text-dark-600 text-right">
        驗證時間: {new Date(data.timestamp).toLocaleString('zh-TW')}
      </div>
    </div>
  )
}
