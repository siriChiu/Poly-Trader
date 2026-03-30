import React, { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'
import { useApi, useApiPost } from '../hooks/useApi'
import SenseCard from '../components/SenseCard'
import SignalBanner from '../components/SignalBanner'
import FeatureChart from '../components/FeatureChart'

const SENSE_CONFIG = [
  { key: 'eye_dist', name: 'Eye', nameZh: '眼·技術面', icon: '👁️', description: '價格與阻力/支撐距離比例' },
  { key: 'ear_prob', name: 'Ear', nameZh: '耳·市場共識', icon: '👂', description: 'Polymarket 預測市場概率' },
  { key: 'funding_rate', name: 'Nose', nameZh: '鼻·衍生品', icon: '👃', description: '永續合約資金費率' },
  { key: 'fear_greed_index', name: 'Tongue', nameZh: '舌·情緒', icon: '👅', description: '恐懼貪婪指數 (0-100)' },
  { key: 'stablecoin_mcap', name: 'Body', nameZh: '身·鏈上資金', icon: '💪', description: '穩定幣市值變化率 (ROC)' },
]

export default function Dashboard() {
  const { senses: wsSenses, signal: wsSignal, isConnected } = useWebSocket()
  const { data: status, refetch: refetchStatus } = useApi<any>('/status')
  const { data: features, refetch: refetchFeatures } = useApi<any[]>('/features?days=1')
  const { post: toggleAutomation, loading: isToggling } = useApiPost<any>()
  const { post: manualTrade, loading: isTrading } = useApiPost<any>()

  const [automation, setAutomation] = useState(false)

  // 同步自動模式狀態
  useEffect(() => {
    if (status?.automation !== undefined) {
      setAutomation(status.automation)
    }
  }, [status])

  // WebSocket 推送的最新五感數據
  const latestSenses = wsSenses || {}

  const handleToggleAutomation = async () => {
    const result = await toggleAutomation('/automation/toggle')
    if (result) {
      setAutomation(result.automation)
    }
  }

  const handleManualTrade = async (side: 'buy' | 'sell') => {
    const result = await manualTrade('/trade', {
      side,
      symbol: status?.symbol || 'BTCUSDT',
      qty: 0.001,
    })
    if (result?.success) {
      refetchStatus()
    }
  }

  return (
    <div className="space-y-6">
      {/* 系統狀態欄 */}
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <div>
              <span className="text-xs text-dark-400">BTC 價格</span>
              <div className="text-2xl font-bold font-mono text-dark-100">
                ${latestSenses.close_price?.toLocaleString() ?? '—'}
              </div>
            </div>
            <div className="h-10 w-px bg-dark-700" />
            <div>
              <span className="text-xs text-dark-400">模式</span>
              <div className={`text-lg font-semibold ${automation ? 'text-buy' : 'text-dark-300'}`}>
                {automation ? '🤖 自動' : '🖐️ 手動'}
              </div>
            </div>
            <div className="h-10 w-px bg-dark-700" />
            <div>
              <span className="text-xs text-dark-400">數據量</span>
              <div className="text-lg font-mono text-dark-200">
                {status?.data_counts?.raw_market_data ?? 0} 筆
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-buy animate-pulse' : 'bg-sell'}`} />
            <span className="text-xs text-dark-400">
              {isConnected ? '即時連線' : '斷線中'}
            </span>
          </div>
        </div>
      </div>

      {/* 五感卡片 */}
      <div>
        <h2 className="text-lg font-semibold text-dark-300 mb-3">五感即時數據</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {SENSE_CONFIG.map((s) => (
            <SenseCard
              key={s.key}
              name={s.name}
              nameZh={s.nameZh}
              icon={s.icon}
              value={latestSenses[s.key] ?? null}
              description={s.description}
              updatedAt={latestSenses.timestamp}
            />
          ))}
        </div>
      </div>

      {/* 信號橫幅 */}
      <SignalBanner
        signal={wsSignal?.signal ?? null}
        confidence={wsSignal?.confidence ?? null}
        automation={automation}
        onToggleAutomation={handleToggleAutomation}
        onManualTrade={handleManualTrade}
        isToggling={isToggling}
        isTrading={isTrading}
      />

      {/* 特徵趨勢圖 */}
      <FeatureChart data={features || []} />
    </div>
  )
}
