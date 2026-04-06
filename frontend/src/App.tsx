import type { ReactNode } from 'react'
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom'
import { Overview } from './pages/Overview'
import { Matches } from './pages/Matches'
import { Leaderboards } from './pages/Leaderboards'
import { Players } from './pages/Players'
import { Balancing } from './pages/Balancing'
import { MatchDetail } from './pages/MatchDetail'
import { PlayerProfile } from './pages/PlayerProfile'
import { HowItWorks } from './pages/HowItWorks'

function RouteLink({ to, label }: { to: string, label: string }) {
  const loc = useLocation()
  const isActive = loc.pathname === to
  return (
    <Link
      to={to}
      className={`px-4 py-2 text-sm font-semibold tracking-wide border-b-2 transition-all duration-300 whitespace-nowrap ${
        isActive
          ? 'border-violet-500 text-violet-400 drop-shadow-[0_0_12px_rgba(139,92,246,0.3)]'
          : 'border-transparent text-zinc-500 hover:text-zinc-300 hover:border-zinc-700 hover:bg-zinc-800/30 rounded-t-lg'
      }`}
    >
      {label}
    </Link>
  )
}

function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <nav className="border-b border-zinc-800 bg-zinc-950/90 backdrop-blur sticky top-0 z-10 w-full">
        <div className="mx-auto flex flex-col md:flex-row max-w-7xl items-center justify-between px-4 pt-3 md:pb-0 gap-4">
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center font-black text-white group-hover:bg-indigo-500 transition-all duration-300 shadow-[0_0_20px_rgba(79,70,229,0.4)] group-hover:scale-105 active:scale-95">
                ETL
              </div>
              <div className="flex flex-col -gap-1">
                <span className="text-lg font-black tracking-tighter text-white group-hover:text-indigo-400 transition-colors">STATS</span>
                <span className="text-[10px] font-bold text-indigo-400/80 tracking-[0.2em] -mt-1 opacity-80">v2026.4.6.3</span>
              </div>
            </Link>
          </div>
          <div className="flex space-x-1 overflow-x-auto w-full md:w-auto scrollbar-hide">
            {[
              { path: '/', label: 'Overview' },
              { path: '/matches', label: 'Match History' },
              { path: '/leaderboards', label: 'Rankings' },
              { path: '/search', label: 'Player Search' },
              { path: '/balancing', label: 'Team Balancer' },
              { path: '/how-it-works', label: 'How it Works' },
            ].map(t => (
              <RouteLink key={t.path} to={t.path} label={t.label} />
            ))}
          </div>
        </div>
      </nav>
      {children}
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/matches" element={<Matches />} />
          <Route path="/leaderboards" element={<Leaderboards />} />
          <Route path="/search" element={<Players />} />
          <Route path="/balancing" element={<Balancing />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/match/:id" element={<MatchDetail />} />
          <Route path="/player/:guid" element={<PlayerProfile />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
