import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchStatsOverview, type StatsOverview } from '../api'

export function Overview() {
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
                  <tr key={m.id} className="hover:bg-zinc-800/30 transition group">
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
                      <Link to={`/match/${m.id}`} className="text-zinc-600 hover:text-zinc-100 transition inline-block translate-x-0 group-hover:translate-x-1">
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
