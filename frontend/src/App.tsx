import type { ReactNode } from 'react'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { MatchDetail } from './pages/MatchDetail'
import { PlayerProfile } from './pages/PlayerProfile'

function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <nav className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3">
          <Link to="/" className="text-lg font-semibold tracking-tight text-zinc-100">
            ET:L Stats
          </Link>
          <span className="text-xs text-zinc-600">Gather balance</span>
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
          <Route path="/" element={<Dashboard />} />
          <Route path="/match/:id" element={<MatchDetail />} />
          <Route path="/player/:guid" element={<PlayerProfile />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
