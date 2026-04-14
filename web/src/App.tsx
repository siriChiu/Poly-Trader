import React from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Senses from './pages/Senses'
import StrategyLab from './pages/StrategyLab'
import GlobalTopProgress from './components/GlobalTopProgress'

const NAV_ITEMS = [
  { to: '/', label: '📊 儀表板', end: true },
  { to: '/senses', label: '🎛️ 特徵管理' },
  { to: '/lab', label: '🧪 策略實驗室' },
]

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div className="min-h-screen bg-dark-950">
        <nav className="bg-dark-900 border-b border-dark-700 sticky top-0 z-50">
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
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/backtest" element={<Navigate to="/lab" replace />} />
            <Route path="/senses" element={<Senses />} />
            <Route path="/lab" element={<StrategyLab />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
