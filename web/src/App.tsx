import React from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import GlobalTopProgress from './components/GlobalTopProgress'

const Dashboard = React.lazy(() => import('./pages/Dashboard'))
const Senses = React.lazy(() => import('./pages/Senses'))
const StrategyLab = React.lazy(() => import('./pages/StrategyLab'))
const ExecutionConsole = React.lazy(() => import('./pages/ExecutionConsole'))
const ExecutionStatus = React.lazy(() => import('./pages/ExecutionStatus'))

const NAV_ITEMS = [
  { to: '/', label: '📊 儀表板', end: true },
  { to: '/execution', label: '⚡ Bot 營運', end: true },
  { to: '/execution/status', label: '🩺 執行狀態' },
  { to: '/senses', label: '🎛️ 特徵管理' },
  { to: '/lab', label: '🧪 策略實驗室' },
]

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div className="min-h-screen bg-dark-950">
        <nav className="sticky top-0 z-50 border-b border-white/6 bg-dark-900/80 backdrop-blur-xl shadow-[0_12px_40px_rgba(6,10,24,0.28)]">
          <div className="w-full px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-14">
              <div className="flex items-center gap-2">
                <span className="text-xl">🔮</span>
                <span className="text-lg font-bold text-dark-100">Poly-Trader</span>
                <span className="text-xs text-dark-500 ml-1">v2.0</span>
              </div>
              <div className="flex items-center gap-1">
                {NAV_ITEMS.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-accent/20 text-accent'
                          : 'text-dark-400 hover:text-dark-200 hover:bg-dark-800'
                      }`
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>
            </div>
          </div>
        </nav>
        <GlobalTopProgress />

        <main className="w-full px-4 sm:px-6 lg:px-8 py-6">
          <React.Suspense fallback={<div className="rounded-xl border border-dark-700 bg-dark-900/70 px-4 py-6 text-sm text-dark-300">頁面載入中…</div>}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/execution" element={<ExecutionConsole />} />
              <Route path="/execution/status" element={<ExecutionStatus />} />
              <Route path="/backtest" element={<Navigate to="/lab" replace />} />
              <Route path="/senses" element={<Senses />} />
              <Route path="/lab" element={<StrategyLab />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </React.Suspense>
        </main>
      </div>
    </BrowserRouter>
  )
}
