/**
 * FeatureChart — Dynamic line chart for ALL features
 * Reads feature list dynamically from the data props, no hard-coded feature keys.
 * Uses colors from ALL_SENSES config.
 */
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
import { ALL_SENSES } from '../config/senses'

interface FeatureChartProps {
  data: Record<string, any>[]
  selectedKey?: string | null
}

export default function FeatureChart({ data, selectedKey }: FeatureChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-12 flex items-center justify-center h-64 text-slate-500">
        尚無特徵趨勢數據
      </div>
    )
  }

  // Dynamically detect all numeric keys from first data point (exclude timestamp)
  const allKeys = data.length > 0
    ? Object.entries(data[0])
        .filter(([k, v]) => k !== 'timestamp' && typeof v === 'number')
        .map(([k]) => k)
    : []

  // Filter by selectedKey if set
  const keys = selectedKey ? allKeys.filter(k => k.includes(selectedKey) || selectedKey.includes(k.replace('feat_', ''))) : allKeys

  // Get color for a key
  const getColor = (key: string): string => {
    const clean = key.replace("feat_", "").replace("4h_", "4h_")
    if (clean in ALL_SENSES) return ALL_SENSES[clean].color
    // Fallback: hash-based color
    let hash = 0
    for (let i = 0; i < clean.length; i++) {
      hash = clean.charCodeAt(i) + ((hash << 5) - hash)
    }
    const h = Math.abs(hash) % 360
    return `hsl(${h}, 70%, 65%)`
  }

  const getLabel = (key: string): string => {
    const clean = key.replace("feat_", "").replace("4h_", "4H ")
    if (clean in ALL_SENSES) return `${ALL_SENSES[clean].emoji} ${ALL_SENSES[clean].name}`
    return clean.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  }

  return (
    <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">📈 特徵趨勢 ({keys.length} features)</h3>
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="timestamp"
            tick={{ fill: '#64748b', fontSize: 10 }}
            tickFormatter={(v) => {
              const d = new Date(v)
              return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
            }}
          />
          <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#e2e8f0',
              fontSize: 11,
            }}
            labelFormatter={(label) => new Date(label as string).toLocaleString('zh-TW')}
          />
          <Legend
            wrapperStyle={{ color: '#94a3b8', fontSize: 10 }}
            verticalAlign="top"
            height={30}
          />
          {keys.map((key) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={getLabel(key)}
              stroke={getColor(key)}
              strokeWidth={1.5}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
