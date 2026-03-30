import React from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts'

interface FeatureDataPoint {
  timestamp: string
  feat_eye_dist: number | null
  feat_ear_zscore: number | null
  feat_nose_sigmoid: number | null
  feat_tongue_pct: number | null
  feat_body_roc: number | null
}

interface FeatureChartProps {
  data: FeatureDataPoint[]
}

const FEATURES = [
  { key: 'feat_eye_dist', label: '👁️ Eye (技術面)', color: '#3b82f6' },
  { key: 'feat_ear_zscore', label: '👂 Ear (市場共識)', color: '#8b5cf6' },
  { key: 'feat_nose_sigmoid', label: '👃 Nose (衍生品)', color: '#f59e0b' },
  { key: 'feat_tongue_pct', label: '👅 Tongue (情緒)', color: '#ec4899' },
  { key: 'feat_body_roc', label: '💪 Body (鏈上資金)', color: '#14b8a6' },
]

export default function FeatureChart({ data }: FeatureChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="card flex items-center justify-center h-64 text-dark-500">
        尚無特徵趨勢數據
      </div>
    )
  }

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-dark-200 mb-4">五感特徵趨勢</h3>
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="timestamp"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickFormatter={(v) => {
              const d = new Date(v)
              return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
            }}
          />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#f1f5f9',
            }}
            labelFormatter={(label) => new Date(label as string).toLocaleString('zh-TW')}
          />
          <Legend
            wrapperStyle={{ color: '#94a3b8', fontSize: 12 }}
          />
          {FEATURES.map((f) => (
            <Line
              key={f.key}
              type="monotone"
              dataKey={f.key}
              name={f.label}
              stroke={f.color}
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
