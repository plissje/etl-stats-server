import type { ReactNode } from 'react'
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom'
import { OverviewTab, MatchesTab, LeaderboardsTab, PlayersTab, BalancingTab } from './pages/Dashboard'
import { MatchDetail } from './pages/MatchDetail'
import { PlayerProfile } from './pages/PlayerProfile'

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
          <div className="flex items-center gap-4 md:mb-3">
            <Link to="/" className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <span className="bg-gradient-to-tr from-violet-500 to-fuchsia-500 inline-block w-4 h-4 rounded-sm shadow-[0_0_10px_rgba(139,92,246,0.3)]" />
              RTCW: ET Israel Stats
            </Link>
          </div>
          <div className="flex space-x-1 overflow-x-auto w-full md:w-auto scrollbar-hide">
            {[
              { path: '/', label: 'Overview' },
              { path: '/matches', label: 'Match History' },
              { path: '/leaderboards', label: 'Rankings' },
              { path: '/search', label: 'Player Search' },
              { path: '/balancing', label: 'Team Balancer' },
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
          <Route path="/" element={<OverviewTab />} />
          <Route path="/matches" element={<MatchesTab />} />
          <Route path="/leaderboards" element={<LeaderboardsTab />} />
          <Route path="/search" element={<PlayersTab />} />
          <Route path="/balancing" element={<BalancingTab />} />
          <Route path="/match/:id" element={<MatchDetail />} />
          <Route path="/player/:guid" element={<PlayerProfile />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
