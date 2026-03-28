import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchMatches, fetchStatsOverview, fetchLeaderboards, searchPlayers, balanceTeams,
  type MatchSummary, type StatsOverview, type Leaderboards, type LeaderboardEntry, type BalanceResponse 
} from '../api'
// Recharts removed as it is no longer used for map dominance
import { QuakeName } from '../components/QuakeName'

export function OverviewTab() {
  const [stats, setStats] = useState<StatsOverview | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    fetchStatsOverview().then(setStats).catch(e => setErr(String(e)))
  }, [])

  if (err) return <div className="text-red-400">{err}</div>
  if (!stats) return <div className="text-zinc-500 animate-pulse">Loading overview...</div>

  const formatTime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    if (days > 0) return `${days}d ${hours}h`
    if (hours > 0) return `${hours}h ${mins}m`
    return `${mins}m`
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 space-y-12 animate-in fade-in slide-in-from-bottom-2 duration-500">
      {/* Key Stats Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Total Matches', val: stats.total_matches.toLocaleString(), color: 'violet' },
          { label: 'Unique Players', val: stats.total_players.toLocaleString(), color: 'emerald' },
          { label: 'Total Kills', val: stats.total_kills.toLocaleString(), color: 'rose' },
          { label: 'Total Damage', val: (stats.total_damage / 1000).toFixed(1) + 'k', color: 'blue' },
          { label: 'Time Played', val: formatTime(stats.total_time_played_s), color: 'amber' },
        ].map((s) => (
          <div key={s.label} className={`bg-zinc-900/50 p-5 rounded-xl border border-zinc-800/80 shadow-lg relative overflow-hidden group hover:border-${s.color}-500/50 transition duration-300`}>
            <div className={`absolute inset-0 bg-gradient-to-br from-${s.color}-500/10 to-transparent opacity-0 group-hover:opacity-100 transition duration-500`} />
            <div className="text-[10px] tracking-wider uppercase text-zinc-500 mb-1 font-bold">{s.label}</div>
            <div className="text-2xl font-light text-zinc-100">{s.val}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Hall of Fame - SR */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-zinc-100 flex items-center gap-2">
            <span className="w-1.5 h-6 bg-emerald-500 rounded-full inline-block" />
            Hall of Fame
          </h3>
          <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl overflow-hidden divide-y divide-zinc-800/40">
            {stats.top_players.map((p, i) => (
              <Link key={p.guid} to={`/player/${p.guid}`} className="flex justify-between items-center px-4 py-3 hover:bg-zinc-800/30 transition group">
                <span className="text-zinc-300 font-medium group-hover:translate-x-1 transition duration-200">
                  <span className={`mr-2 font-mono ${i === 0 ? 'text-amber-400' : 'text-zinc-600'}`}>
                    {i === 0 ? '👑' : `#${i+1}`}
                  </span>
                  {p.name}
                </span>
                <span className="text-violet-400 font-mono text-sm">{Math.round(p.rating)} SR</span>
              </Link>
            ))}
            {stats.top_players.length === 0 && <div className="p-8 text-center text-zinc-600 italic">No rankings yet.</div>}
          </div>
        </div>

        {/* Most MVPs */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-zinc-100 flex items-center gap-2">
            <span className="w-1.5 h-6 bg-amber-500 rounded-full inline-block" />
            Most MVPs
          </h3>
          <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl overflow-hidden divide-y divide-zinc-800/40">
            {stats.top_mvps.map((p, i) => (
              <Link key={p.guid} to={`/player/${p.guid}`} className="flex justify-between items-center px-4 py-3 hover:bg-zinc-800/30 transition group">
                <span className="text-zinc-300 font-medium group-hover:translate-x-1 transition duration-200">
                  <span className="text-zinc-600 mr-2 font-mono">#{i+1}</span>
                  {p.name}
                </span>
                <span className="text-amber-400 font-mono text-sm">{p.count} ⭐</span>
              </Link>
            ))}
            {stats.top_mvps.length === 0 && <div className="p-8 text-center text-zinc-600 italic">No MVPs tracked.</div>}
          </div>
        </div>

        {/* Top Played Maps */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-zinc-100 flex items-center gap-2">
            <span className="w-1.5 h-6 bg-violet-500 rounded-full inline-block" />
            Popular Warzones
          </h3>
          <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl overflow-hidden divide-y divide-zinc-800/40">
            {stats.top_maps.map((m, i) => (
              <div key={m.mapname} className="flex justify-between items-center px-4 py-3 hover:bg-zinc-800/30 transition">
                <span className="text-zinc-300 font-medium">
                  <span className="text-zinc-600 mr-2 font-mono">#{i+1}</span>
                  {m.mapname}
                </span>
                <span className="text-zinc-500 text-sm font-mono">{m.count} battles</span>
              </div>
            ))}
            {stats.top_maps.length === 0 && <div className="p-8 text-center text-zinc-600 italic">No data yet.</div>}
          </div>
        </div>
      </div>

      {/* Bottom Section: Recent Battles + Legendary Stats Table */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-zinc-100 flex items-center gap-2">
            <span className="w-1.5 h-6 bg-rose-500 rounded-full inline-block" />
            Recent Battles
          </h3>
          <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-zinc-800/50 text-[10px] uppercase tracking-widest text-zinc-500 font-bold">
                  <th className="px-4 py-3">Map</th>
                  <th className="px-4 py-3 text-right">Date</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/40">
                {stats.recent_matches.map((m) => (
                  <tr key={m.match_id} className="hover:bg-zinc-800/30 transition group">
                    <td className="px-4 py-3">
                      <div className="text-zinc-300 font-medium group-hover:text-violet-400 transition">{m.mapname}</div>
                      <div className="text-[10px] text-zinc-600 font-mono">{m.match_id.slice(0, 8)}</div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="text-zinc-400 text-xs">
                        {new Date(m.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                      </div>
                      <div className="text-[10px] text-zinc-600 uppercase">
                        {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link to={`/match/${m.match_id}`} className="text-zinc-600 hover:text-zinc-100 transition inline-block translate-x-0 group-hover:translate-x-1">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-medium text-zinc-100 flex items-center gap-2">
            <span className="w-1.5 h-6 bg-blue-500 rounded-full inline-block" />
            Global Performance
          </h3>
          {/* Placeholder for now, could be top damage dealers or similar */}
          <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-8 flex flex-col items-center justify-center text-center space-y-4 min-h-[300px]">
            <div className="w-16 h-16 rounded-full bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
               <svg className="w-8 h-8 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
            </div>
            <div>
              <div className="text-zinc-300 font-medium">Aggregated Combat Data</div>
              <div className="text-sm text-zinc-500 max-w-xs mx-auto">This section tracks cumulative performance across all operational theaters.</div>
            </div>
            <div className="grid grid-cols-2 gap-4 w-full pt-4">
               <div className="bg-zinc-800/40 p-3 rounded-lg border border-zinc-700/30">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">KDR Ratio</div>
                  <div className="text-xl font-mono text-zinc-200">{(stats.total_kills / (stats.total_matches * 10 || 1)).toFixed(2)}</div>
               </div>
               <div className="bg-zinc-800/40 p-3 rounded-lg border border-zinc-700/30">
                  <div className="text-[10px] text-zinc-500 uppercase font-bold">Dmg/Match</div>
                  <div className="text-xl font-mono text-zinc-200">{Math.round(stats.total_damage / (stats.total_matches || 1)).toLocaleString()}</div>
               </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function MatchesTab() {
  const [rows, setRows] = useState<MatchSummary[]>([])
  const [mapFilter, setMapFilter] = useState('')

  useEffect(() => {
    fetchMatches(mapFilter || undefined).then(setRows).catch(console.error)
  }, [mapFilter])

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="mb-6 flex">
        <div className="relative w-full max-w-sm">
          <input 
            type="text" 
            placeholder="Filter matches by mapname..." 
            className="w-full bg-zinc-900/80 border border-zinc-800/80 rounded-lg pl-10 pr-4 py-2.5 text-sm text-zinc-100 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition backdrop-blur"
            value={mapFilter} 
            onChange={e => setMapFilter(e.target.value)} 
          />
          <svg className="w-4 h-4 text-zinc-500 absolute left-3.5 top-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
        </div>
      </div>
      <div className="flex flex-col gap-8">
        {Object.entries(
          rows.reduce((acc, match) => {
            const dateStr = match.round_start_unix > 0 
              ? new Date(match.round_start_unix * 1000).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
              : 'Unknown Date'
            if (!acc[dateStr]) acc[dateStr] = []
            acc[dateStr].push(match)
            return acc
          }, {} as Record<string, MatchSummary[]>)
        ).map(([dateLabel, matchGroup]) => (
          <div key={dateLabel} className="space-y-4">
            <div className="flex items-center gap-4 px-2">
              <h4 className="text-zinc-400 text-sm font-semibold uppercase tracking-widest">{dateLabel}</h4>
              <div className="h-px flex-1 bg-zinc-800/50" />
            </div>
            <div className="flex flex-col gap-3">
              {matchGroup.map((m) => {
                const showDate = m.round_start_unix > 0
                const date = showDate ? new Date(m.round_start_unix * 1000) : null

                return (
                  <Link key={m.id} to={`/match/${m.id}`} className="block group">
                    <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-xl overflow-hidden hover:border-violet-500/30 hover:bg-zinc-800/40 transition-all duration-200 shadow-sm flex min-h-[90px]">

                      {/* LEFT: Team rosters + meta — 80% */}
                      <div className="flex-1 px-5 py-4 flex flex-col justify-between gap-2 min-w-0">
                        {/* Row 1: Axis players */}
                        <div className={`flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg px-3 py-1.5 ${
                          m.winner_team === 1 ? 'bg-rose-500/10' : 'bg-transparent'
                        }`}>
                          <span className="text-zinc-500 text-xs font-bold uppercase tracking-wider shrink-0 w-14">Alpha</span>
                          {m.axis_players.length > 0
                            ? m.axis_players.map(n => (
                                <span key={n} className="text-sm font-medium text-zinc-300">{n}</span>
                              ))
                            : <span className="text-zinc-600 text-sm italic">—</span>}
                        </div>
                        {/* Row 2: Allies players */}
                        <div className={`flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg px-3 py-1.5 ${
                          m.winner_team === 2 ? 'bg-sky-500/10' : 'bg-transparent'
                        }`}>
                          <span className="text-zinc-500 text-xs font-bold uppercase tracking-wider shrink-0 w-14">Beta</span>
                          {m.allies_players.length > 0
                            ? m.allies_players.map(n => (
                                <span key={n} className="text-sm font-medium text-zinc-300">{n}</span>
                              ))
                            : <span className="text-zinc-600 text-sm italic">—</span>}
                        </div>
                        {/* Secondary: Map, result, MVP, date */}
                      <div className="flex items-center gap-3 flex-wrap pt-1">
                        {date && <span className="text-zinc-500 text-[10px] font-mono font-bold flex items-center gap-1 bg-zinc-800/30 px-2 py-0.5 rounded border border-zinc-700/20">🕒 {date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}
                        <span className="text-zinc-500 text-xs font-mono tracking-wide">📍 {m.mapname || '(unknown)'}</span>
                        {m.mvp_name && (
                          <span className="text-amber-400 text-[10px] font-bold uppercase tracking-wider bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded flex items-center gap-1">
                            ⭐ MVP: {m.mvp_name}
                          </span>
                        )}
                      </div>
                      </div>

                      {/* RIGHT: Result — ~20% */}
                      <div className={`w-[20%] min-w-[90px] flex flex-col items-center justify-center border-l text-center px-2 shrink-0 ${
                        m.winner_team === 1
                          ? 'border-rose-500/20 bg-rose-500/5'
                          : m.winner_team === 2
                          ? 'border-sky-500/20 bg-sky-500/5'
                          : 'border-zinc-700/40 bg-zinc-800/20'
                      }`}>
                        <span className={`text-xs font-bold uppercase tracking-widest ${
                          m.winner_team === 1 ? 'text-rose-400'
                          : m.winner_team === 2 ? 'text-sky-400'
                          : 'text-zinc-500'
                        }`}>
                          {m.winner_team === 1 ? 'Alpha' : m.winner_team === 2 ? 'Beta' : 'Draw'}
                        </span>
                        <span className={`text-lg font-black mt-0.5 ${
                          m.winner_team === 1 ? 'text-rose-300'
                          : m.winner_team === 2 ? 'text-sky-300'
                          : 'text-zinc-400'
                        }`}>WIN</span>
                      </div>

                    </div>
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
        {rows.length === 0 && <div className="p-8 text-center text-zinc-500 border border-zinc-800/40 border-dashed rounded-xl">No matches found.</div>}
      </div>
    </div>
  )
}

export function LeaderboardsTab() {
  const [boards, setBoards] = useState<Leaderboards | null>(null)
  useEffect(() => { fetchLeaderboards().then(setBoards).catch(console.error) }, [])

  if (!boards) return <div className="animate-pulse flex gap-6 mt-8">
    <div className="w-full h-64 border border-zinc-800 rounded-xl bg-zinc-900/30"></div>
    <div className="w-full h-64 border border-zinc-800 rounded-xl bg-zinc-900/30"></div>
    <div className="w-full h-64 border border-zinc-800 rounded-xl bg-zinc-900/30"></div>
  </div>

  const RenderBoard = ({ title, data, suffix, icon }: { title: string, data: LeaderboardEntry[], suffix: string, icon: React.ReactNode }) => (
    <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl shadow-xl overflow-hidden hover:border-zinc-700/80 transition duration-300">
      <div className="bg-zinc-800/50 px-5 py-3 font-semibold tracking-wide text-zinc-200 border-b border-zinc-800/60 flex items-center gap-2">
        {icon}
        {title}
      </div>
      <ul className="divide-y divide-zinc-800/40">
        {data.map((p, i) => (
          <li key={p.guid} className="flex justify-between px-5 py-3 transition hover:bg-zinc-800/30 group">
            <Link to={`/player/${p.guid}`} className="flex gap-3 hover:text-white text-zinc-300 font-medium items-center">
              <span className={`w-5 text-center font-bold text-sm ${i === 0 ? 'text-amber-400' : i === 1 ? 'text-zinc-300' : i === 2 ? 'text-amber-700' : 'text-zinc-600'}`}>{i + 1}.</span> 
              <span className="group-hover:translate-x-1 transition duration-200">
                <QuakeName name={(p as any).raw_name || p.display_name} />
              </span>
            </Link>
            <span className="text-violet-400/90 font-mono text-sm font-medium">{p.val.toLocaleString()} <span className="text-zinc-600 text-xs">{suffix}</span></span>
          </li>
        ))}
        {data.length === 0 && <li className="p-6 text-center text-zinc-600 border-dashed">No participants yet.</li>}
      </ul>
    </div>
  )

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <RenderBoard 
        title="OpenSkill Rating" 
        data={boards.openskill} 
        suffix="SR" 
        icon={<svg className="w-4 h-4 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
      />
      <RenderBoard 
        title="Top Medics" 
        data={boards.medic} 
        suffix="AVG REV" 
        icon={<svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" /></svg>}
      />
      <RenderBoard 
        title="Sharpshooters" 
        data={boards.sharpshooter} 
        suffix="AVG HS" 
        icon={<svg className="w-4 h-4 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>}
      />
    </div>
  )
}

export function PlayersTab() {
  const [q, setQ] = useState('')
  const [players, setPlayers] = useState<LeaderboardEntry[]>([])

  useEffect(() => {
    const t = setTimeout(() => searchPlayers(q).then(setPlayers).catch(console.error), 200)
    return () => clearTimeout(t)
  }, [q])

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="relative mb-6">
        <input 
          type="text" 
          placeholder="Search by exact display name..." 
          className="w-full bg-zinc-900/80 border border-zinc-800/80 rounded-xl pl-11 pr-4 py-3 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition backdrop-blur text-lg shadow-inner"
          value={q} 
          onChange={e => setQ(e.target.value)} 
        />
        <svg className="w-5 h-5 text-zinc-500 absolute left-4 top-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
      </div>
      <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl shadow-xl overflow-hidden">
        <ul className="divide-y divide-zinc-800/50">
          {players.map(p => (
            <li key={p.guid}>
              <Link to={`/player/${p.guid}`} className="flex justify-between items-center px-6 py-4 hover:bg-zinc-800/40 transition duration-200">
                <span className="font-semibold tracking-wide text-zinc-200 text-lg">
                  <QuakeName name={(p as any).raw_name || p.display_name} />
                </span>
                <span className="text-sm font-medium text-zinc-400 bg-zinc-800/60 px-3 py-1 rounded-full border border-zinc-700/50 shadow-sm">
                  Rating: <span className="text-violet-400">&nbsp;{p.val}</span>
                </span>
              </Link>
            </li>
          ))}
          {players.length === 0 && <li className="px-6 py-10 text-zinc-500 text-center border-dashed border border-transparent">No players align with that search.</li>}
        </ul>
      </div>
    </div>
  )
}

export function BalancingTab() {
  const [selectedPlayers, setSelectedPlayers] = useState<
    { id: string; name: string; sr: number; isManual: boolean }[]
  >([])
  const [manualInput, setManualInput] = useState('')
  const [result, setResult] = useState<BalanceResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<LeaderboardEntry[]>([])

  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults([])
      return
    }
    const t = setTimeout(() => {
      searchPlayers(searchQuery).then(setSearchResults).catch(console.error)
    }, 300)
    return () => clearTimeout(t)
  }, [searchQuery])

  const handleBalance = async () => {
    // Combine manual input and selected players
    const manualLines = manualInput.split('\n').map(s => s.trim()).filter(Boolean)
    const allIdentifiers = [
        ...selectedPlayers.map(p => p.id),
        ...manualLines
    ]
    
    if (allIdentifiers.length < 2) {
      setError('Please select at least 2 players')
      return
    }

    setLoading(true)
    setError('')
    try {
      const res = await balanceTeams(allIdentifiers)
      setResult(res)
    } catch (e: any) {
      setError(e.message || 'Failed to balance teams')
    } finally {
      setLoading(false)
    }
  }

  const addPlayer = (p: LeaderboardEntry) => {
    if (!selectedPlayers.find(sp => sp.id === p.guid)) {
      setSelectedPlayers([...selectedPlayers, { id: p.guid, name: p.display_name, sr: p.val, isManual: false }])
    }
    setSearchQuery('')
    setSearchResults([])
  }

  const removePlayer = (id: string) => {
    setSelectedPlayers(selectedPlayers.filter(p => p.id !== id))
  }

  const manualCount = manualInput.split('\n').map(s => s.trim()).filter(Boolean).length
  const totalCount = selectedPlayers.length + manualCount

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 space-y-10 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Side: Input */}
        <div className="space-y-6">
          <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-2xl p-6 space-y-4 shadow-xl">
            <div className="flex justify-between items-center">
                <h3 className="text-zinc-100 font-bold flex items-center gap-2">
                <span className="w-1.5 h-5 bg-violet-500 rounded-full" />
                Player Selection
                </h3>
                <span className={`text-[10px] font-black px-2 py-0.5 rounded uppercase tracking-widest ${totalCount > 12 ? 'bg-rose-500/20 text-rose-400' : 'bg-zinc-800 text-zinc-500'}`}>
                    {totalCount} Players Selected
                </span>
            </div>
            
            <div className="relative">
              <input
                type="text"
                placeholder="Search player name..."
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-violet-500/50 transition"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              {searchResults.length > 0 && (
                <div className="absolute top-full left-0 w-full mt-2 bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl z-20 overflow-hidden max-h-60 overflow-y-auto">
                  {searchResults.map(p => (
                    <button
                      key={p.guid}
                      className="w-full text-left px-4 py-2 hover:bg-zinc-800 transition text-sm flex justify-between items-center"
                      onClick={() => addPlayer(p)}
                    >
                      <QuakeName name={p.display_name} />
                      <span className="text-[10px] text-zinc-500">{p.val} SR</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="space-y-3">
               <label className="text-[10px] text-zinc-500 uppercase font-black tracking-widest px-1">Selected List</label>
               <div className="min-h-[60px] max-h-[220px] overflow-y-auto custom-scrollbar p-1 space-y-1 bg-zinc-950/30 rounded-xl border border-zinc-800/40">
                  {selectedPlayers.map(p => (
                    <div key={p.id} className="bg-zinc-900/50 flex items-center justify-between px-3 py-2 rounded-lg border border-zinc-800/60 hover:border-zinc-700 transition">
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-zinc-200"><QuakeName name={p.name} /></span>
                        <span className="text-[9px] text-zinc-500 font-mono tracking-tighter">[{p.id.slice(0, 16).toUpperCase()}]</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-violet-400 font-mono text-xs font-bold">{Math.round(p.sr)} SR</span>
                        <button onClick={() => removePlayer(p.id)} className="text-zinc-600 hover:text-rose-500 transition text-lg leading-none">×</button>
                      </div>
                    </div>
                  ))}
                  {selectedPlayers.length === 0 && <span className="text-zinc-600 text-xs italic p-4 block text-center">No players selected from database.</span>}
               </div>
            </div>

            <div className="space-y-2 pt-2">
              <label className="text-[10px] text-zinc-500 uppercase font-black tracking-widest px-1">Quick-Paste Field (Names or GUIDs)</label>
              <textarea
                className="w-full h-24 bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2 text-xs font-mono focus:outline-none focus:border-amber-500/50 transition resize-none custom-scrollbar"
                placeholder="Names or GUIDs here...&#10;One per line."
                value={manualInput}
                onChange={e => setManualInput(e.target.value)}
              />
            </div>

            <button
              className="w-full bg-violet-600 hover:bg-violet-500 text-white font-black py-4 rounded-xl transition shadow-[0_0_20px_rgba(139,92,246,0.2)] disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-widest text-sm"
              onClick={handleBalance}
              disabled={loading}
            >
              {loading ? 'Processing...' : 'Auto-Balance Teams'}
            </button>
            {error && <div className="text-rose-500 text-xs text-center border border-rose-500/20 bg-rose-500/5 p-2 rounded-lg">{error}</div>}
          </div>
        </div>

        {/* Right Side: Results */}
        <div className="space-y-6">
          {!result ? (
            <div className="h-full bg-zinc-900/40 border border-zinc-800/80 border-dashed rounded-2xl flex flex-col items-center justify-center text-center p-12 opacity-40">
               <svg className="w-16 h-16 text-zinc-700 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
               <h4 className="text-zinc-500 font-bold uppercase tracking-widest">Awaiting Battle Formations</h4>
               <p className="text-zinc-700 text-sm max-w-xs mt-2">Select your fighting force on the left to generate balanced tactical units.</p>
            </div>
          ) : (
            <div className="space-y-6 animate-in zoom-in-95 duration-300">
               <div className="flex gap-4">
                  <div className="flex-1 bg-zinc-900/60 border border-rose-500/20 rounded-2xl p-5 shadow-[0_0_30px_rgba(244,63,94,0.1)]">
                     <div className="text-rose-500 text-[10px] font-black uppercase tracking-widest mb-1">Team Alpha</div>
                     <div className="text-2xl font-black text-rose-400">{Math.round(result.alpha_avg_sr)} <span className="text-xs text-zinc-600 font-normal">AVG SR</span></div>
                     <ul className="mt-4 space-y-2">
                        {result.alpha.map(p => (
                          <li key={p.guid} className="flex justify-between items-center text-sm bg-zinc-950/50 p-2 rounded-lg border border-zinc-800/40 hover:border-rose-500/30 transition">
                            <QuakeName name={p.name} />
                            <span className="text-zinc-500 font-mono text-[10px]">{Math.round(p.rating)}</span>
                          </li>
                        ))}
                     </ul>
                  </div>
                  <div className="flex-1 bg-zinc-900/60 border border-sky-500/20 rounded-2xl p-5 shadow-[0_0_30px_rgba(14,165,233,0.1)]">
                     <div className="text-sky-500 text-[10px] font-black uppercase tracking-widest mb-1">Team Beta</div>
                     <div className="text-2xl font-black text-sky-400">{Math.round(result.beta_avg_sr)} <span className="text-xs text-zinc-600 font-normal">AVG SR</span></div>
                     <ul className="mt-4 space-y-2">
                        {result.beta.map(p => (
                          <li key={p.guid} className="flex justify-between items-center text-sm bg-zinc-950/50 p-2 rounded-lg border border-zinc-800/40 hover:border-sky-500/30 transition">
                            <QuakeName name={p.name} />
                            <span className="text-zinc-500 font-mono text-[10px]">{Math.round(p.rating)}</span>
                          </li>
                        ))}
                     </ul>
                  </div>
               </div>
               <div className="bg-zinc-900/40 border border-zinc-800 p-4 rounded-xl flex items-center justify-between">
                  <span className="text-zinc-500 text-xs font-bold uppercase tracking-widest">Statistical Variance</span>
                  <span className={`text-sm font-black ${result.diff < 50 ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {Math.round(result.diff)} SR Difference
                  </span>
               </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
