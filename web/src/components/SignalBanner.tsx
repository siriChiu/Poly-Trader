import React, { useState } from 'react'

interface SignalBannerProps {
  signal: string | null
  confidence: number | null
  automation: boolean
  onToggleAutomation: () => void
  onManualTrade: (side: 'buy' | 'sell') => void
  isToggling?: boolean
  isTrading?: boolean
}

export default function SignalBanner({
  signal,
  confidence,
  automation,
  onToggleAutomation,
  onManualTrade,
  isToggling = false,
  isTrading = false,
}: SignalBannerProps) {
  const [confirmTrade, setConfirmTrade] = useState<'buy' | 'sell' | null>(null)

  const signalColor = signal === 'BUY' ? 'border-buy bg-green-900/20' : 'border-hold bg-yellow-900/20'
  const signalText = signal === 'BUY' ? '📈 買進信號' : '⏸️ 觀望'
  const confidencePct = confidence !== null ? (confidence * 100).toFixed(1) : '—'

  const handleConfirm = () => {
    if (confirmTrade) {
      onManualTrade(confirmTrade)
      setConfirmTrade(null)
    }
  }

  return (
    <div className={`card border-2 ${signalColor}`}>
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        {/* 信號區域 */}
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl font-bold">{signalText}</span>
            {signal === 'BUY' && (
              <span className="badge bg-buy/20 text-buy">BUY</span>
            )}
            {signal !== 'BUY' && signal && (
              <span className="badge bg-hold/20 text-hold">HOLD</span>
            )}
          </div>

          {/* 信心分數進度條 */}
          <div className="w-full max-w-md">
            <div className="flex justify-between text-xs text-dark-400 mb-1">
              <span>信心分數</span>
              <span className="font-mono">{confidencePct}%</span>
            </div>
            <div className="h-3 bg-dark-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  (confidence ?? 0) > 0.7 ? 'bg-buy' : (confidence ?? 0) > 0.5 ? 'bg-hold' : 'bg-sell'
                }`}
                style={{ width: `${confidence ?? 0}%` }}
              />
            </div>
          </div>
        </div>

        {/* 操作區域 */}
        <div className="flex items-center gap-3">
          {/* 手動下單 */}
          {confirmTrade ? (
            <div className="flex items-center gap-2">
              <span className="text-sm text-dark-300">
                確認{confirmTrade === 'buy' ? '買進' : '賣出'}？
              </span>
              <button
                onClick={handleConfirm}
                disabled={isTrading}
                className="btn-buy text-sm py-1 px-3"
              >
                ✓ 確認
              </button>
              <button
                onClick={() => setConfirmTrade(null)}
                className="text-sm text-dark-400 hover:text-dark-200 px-2 py-1"
              >
                取消
              </button>
            </div>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={() => setConfirmTrade('buy')}
                className="btn-buy"
                disabled={isTrading}
              >
                🛒 買進
              </button>
              <button
                onClick={() => setConfirmTrade('sell')}
                className="btn-sell"
                disabled={isTrading}
              >
                💰 賣出
              </button>
            </div>
          )}

          {/* 自動模式開關 */}
          <div className="flex flex-col items-center ml-4">
            <button
              onClick={onToggleAutomation}
              disabled={isToggling}
              className={`relative w-14 h-8 rounded-full transition-colors duration-300 ${
                automation ? 'bg-buy' : 'bg-dark-600'
              }`}
            >
              <span
                className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow transition-transform duration-300 ${
                  automation ? 'translate-x-6' : ''
                }`}
              />
            </button>
            <span className={`text-xs mt-1 font-medium ${automation ? 'text-buy' : 'text-dark-400'}`}>
              {automation ? '自動模式' : '手動模式'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
