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
      <div className="app-shell bg-dark-950">
        <nav className="app-nav-shell sticky top-0 z-50">
          <div className="w-full px-4 sm:px-6 lg:px-8">
            <div className="flex min-h-[64px] flex-col gap-3 py-3 lg:h-16 lg:flex-row lg:items-center lg:justify-between lg:py-0">
              <div className="flex items-center gap-2">
                <span className="text-xl">🔮</span>
                <span className="text-lg font-bold text-dark-100">Poly-Trader</span>
                <span className="text-xs text-dark-500 ml-1">v2.0</span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {NAV_ITEMS.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) => `app-nav-link ${isActive ? 'app-nav-link-active' : ''}`}
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>
            </div>
          </div>
        </nav>
        <GlobalTopProgress />

        <main className="w-full px-4 py-6 sm:px-6 lg:px-8">
          <React.Suspense fallback={<div className="app-surface-card text-sm text-dark-300">頁面載入中…</div>}>
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
