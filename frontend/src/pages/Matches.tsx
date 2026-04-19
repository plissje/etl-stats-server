import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchMatches, fetchMaps, type MatchSummary } from '../api'

export function Matches() {
  const [rows, setRows] = useState<MatchSummary[]>([])
  const [mapFilter, setMapFilter] = useState('')
  const [playerFilter, setPlayerFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [availableMaps, setAvailableMaps] = useState<string[]>([])
  const [page, setPage] = useState(0)
  const LIMIT = 15

  useEffect(() => {
    fetchMaps().then(setAvailableMaps).catch(console.error)
  }, [])

  useEffect(() => {
    const fromUnix = dateFrom ? Math.floor(new Date(dateFrom).getTime() / 1000) : undefined
    const toUnix = dateTo ? Math.floor(new Date(dateTo + 'T23:59:59').getTime() / 1000) : undefined
    
    fetchMatches(
      mapFilter || undefined, 
      page * LIMIT, 
      LIMIT, 
      playerFilter || undefined, 
      fromUnix, 
      toUnix
    ).then(setRows).catch(console.error)
  }, [mapFilter, playerFilter, dateFrom, dateTo, page])

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col gap-8 mb-12">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-1">
            <h1 className="text-4xl font-black tracking-tight text-white mb-2 leading-none">MATCH HISTORY</h1>
            <p className="text-zinc-500 text-sm font-medium">Browse recent operational datasets and combat records.</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-black text-violet-500/80 uppercase tracking-[0.2em] bg-violet-500/10 px-3 py-1.5 rounded-lg border border-violet-500/20">Archive Interface Active</span>
          </div>
        </div>
        
        {/* Filters Panel */}
        <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-2xl p-6 shadow-xl backdrop-blur-sm grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="space-y-2">
            <label className="text-[10px] font-black text-zinc-600 uppercase tracking-[0.15em] ml-1">Location (Map)</label>
            <div className="relative group">
              <input 
                list="map-list"
                placeholder="All Locations" 
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-zinc-300 focus:outline-none focus:border-violet-500/50 transition shadow-inner"
                value={mapFilter} 
                onChange={e => {
                  setMapFilter(e.target.value)
                  setPage(0)
                }} 
              />
              <datalist id="map-list">
                {availableMaps.map(m => <option key={m} value={m} />)}
              </datalist>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-black text-zinc-600 uppercase tracking-[0.15em] ml-1">Combatant (Player)</label>
            <input 
              type="text" 
              placeholder="Search by name..." 
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-zinc-300 focus:outline-none focus:border-violet-500/50 transition shadow-inner"
              value={playerFilter} 
              onChange={e => {
                setPlayerFilter(e.target.value)
                setPage(0)
              }} 
            />
          </div>

          <div className="space-y-2 md:col-span-2">
            <label className="text-[10px] font-black text-zinc-600 uppercase tracking-[0.15em] ml-1">Temporal Range (Date)</label>
            <div className="flex items-center gap-2">
              <input 
                type="date" 
                className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2 text-sm text-zinc-300 focus:outline-none focus:border-violet-500/50 transition shadow-inner [color-scheme:dark]"
                value={dateFrom} 
                onChange={e => {
                  setDateFrom(e.target.value)
                  setPage(0)
                }} 
              />
              <span className="text-zinc-700 font-bold">—</span>
              <input 
                type="date" 
                className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2 text-sm text-zinc-300 focus:outline-none focus:border-violet-500/50 transition shadow-inner [color-scheme:dark]"
                value={dateTo} 
                onChange={e => {
                  setDateTo(e.target.value)
                  setPage(0)
                }} 
              />
              {(dateFrom || dateTo || mapFilter || playerFilter) && (
                <button 
                  onClick={() => {
                    setMapFilter('')
                    setPlayerFilter('')
                    setDateFrom('')
                    setDateTo('')
                    setPage(0)
                  }}
                  className="ml-2 text-zinc-500 hover:text-rose-400 p-2 transition-colors"
                  title="Clear Filters"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
              )}
            </div>
          </div>
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
                          {(m.round1_duration || m.round2_duration) && (
                            <span className="text-zinc-500 text-[10px] font-mono font-bold bg-zinc-800/30 px-2 py-0.5 rounded border border-zinc-700/20 flex items-center gap-1.5">
                              ⏱️ 
                              <span>
                                <span className="opacity-40 mr-0.5 text-[8px]">β:</span>{m.round1_duration ? `${Math.floor(m.round1_duration/60)}:${String(m.round1_duration%60).padStart(2,'0')}` : '—'}
                              </span>
                              <span className="opacity-20 mx-0.5">/</span>
                              <span>
                                <span className="opacity-40 mr-0.5 text-[8px]">α:</span>{m.round2_duration ? `${Math.floor(m.round2_duration/60)}:${String(m.round2_duration%60).padStart(2,'0')}` : '—'}
                              </span>
                            </span>
                          )}
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
                        }`}>
                          {m.winner_team > 0 ? 'WIN' : 'MATCH'}
                        </span>
                      </div>

                    </div>
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
        {rows.length === 0 && <div className="p-8 text-center text-zinc-500 border border-zinc-800/40 border-dashed rounded-xl">No matches found.</div>}
        
        {/* Pagination Controls */}
        <div className="flex items-center justify-between px-2 pt-4 border-t border-white/5">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="flex items-center gap-2 px-6 py-2 bg-zinc-900 border border-zinc-800 rounded-xl text-xs font-black uppercase tracking-widest text-zinc-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition"
          >
            ← Previous
          </button>
          
          <div className="text-[10px] font-black text-zinc-600 uppercase tracking-widest">
            Page {page + 1}
          </div>

          <button
            onClick={() => setPage(p => p + 1)}
            disabled={rows.length < LIMIT}
            className="flex items-center gap-2 px-6 py-2 bg-zinc-900 border border-zinc-800 rounded-xl text-xs font-black uppercase tracking-widest text-zinc-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  )
}
