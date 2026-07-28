import React from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import GlobalTopProgress from './components/GlobalTopProgress'

const CommandCenter = React.lazy(() => import('./pages/CommandCenter'))
const Dashboard = React.lazy(() => import('./pages/Dashboard'))
const Senses = React.lazy(() => import('./pages/Senses'))
const StrategyLab = React.lazy(() => import('./pages/StrategyLab'))
const ExecutionConsole = React.lazy(() => import('./pages/ExecutionConsole'))
const ExecutionStatus = React.lazy(() => import('./pages/ExecutionStatus'))

const NAV_ITEMS = [
  { to: '/', label: '總覽', end: true },
  { to: '/lab', label: '策略', end: true },
  { to: '/execution', label: '營運', end: true },
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
                <details className="relative">
                  <summary className="app-nav-link cursor-pointer list-none">進階</summary>
                  <div className="absolute right-0 top-[calc(100%+8px)] z-50 grid min-w-44 gap-1 rounded-2xl border border-white/10 bg-slate-950/95 p-2 shadow-2xl backdrop-blur-xl">
                    <NavLink to="/diagnostics" className="rounded-xl px-3 py-2 text-sm text-slate-300 hover:bg-white/5 hover:text-white">完整儀表板</NavLink>
                    <NavLink to="/execution/status" className="rounded-xl px-3 py-2 text-sm text-slate-300 hover:bg-white/5 hover:text-white">執行診斷</NavLink>
                    <NavLink to="/senses" className="rounded-xl px-3 py-2 text-sm text-slate-300 hover:bg-white/5 hover:text-white">特徵管理</NavLink>
                  </div>
                </details>
              </div>
            </div>
          </div>
        </nav>
        <GlobalTopProgress />

        <main className="w-full px-4 py-6 sm:px-6 lg:px-8">
          <React.Suspense fallback={<div className="app-surface-card text-sm text-dark-300">頁面載入中…</div>}>
            <Routes>
              <Route path="/" element={<CommandCenter />} />
              <Route path="/diagnostics" element={<Dashboard />} />
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
