import React from 'react'

interface SenseCardProps {
  name: string
  nameZh: string
  icon: string
  value: number | null
  unit?: string
  description: string
  updatedAt?: string | null
}

const statusColor = (value: number | null): string => {
  if (value === null || value === undefined) return 'text-dark-500'
  if (value > 0.3) return 'text-buy'
  if (value < -0.3) return 'text-sell'
  return 'text-hold'
}

const statusIcon = (value: number | null): string => {
  if (value === null || value === undefined) return '⚪'
  if (value > 0.3) return '🟢'
  if (value < -0.3) return '🔴'
  return '🟡'
}

export default function SenseCard({ name, nameZh, icon, value, unit = '', description, updatedAt }: SenseCardProps) {
  return (
    <div className="card hover:border-dark-500 transition-colors">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{icon}</span>
          <div>
            <div className="text-sm font-semibold text-dark-200">{nameZh}</div>
            <div className="text-xs text-dark-500">{name}</div>
          </div>
        </div>
        <span className="text-lg">{statusIcon(value)}</span>
      </div>

      <div className={`text-3xl font-bold font-mono ${statusColor(value)}`}>
        {value !== null && value !== undefined ? `${value.toFixed(4)}${unit}` : '—'}
      </div>

      <p className="text-xs text-dark-400 mt-2">{description}</p>

      {updatedAt && (
        <div className="text-xs text-dark-600 mt-1">
          更新: {new Date(updatedAt).toLocaleTimeString('zh-TW')}
        </div>
      )}
    </div>
  )
}
