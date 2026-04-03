import { useEffect, useState } from 'react'
import {
  searchPlayers, balanceTeams, fetchLivePlayers,
  type LeaderboardEntry, type BalanceResponse 
} from '../api'
import { QuakeName } from '../components/QuakeName'

export function Balancing() {
  const [selectedPlayers, setSelectedPlayers] = useState<
    { id: string; name: string; sr: number; isManual: boolean }[]
  >([])
  const [manualInput, setManualInput] = useState('')
  const [result, setResult] = useState<BalanceResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [fetchingLive, setFetchingLive] = useState(false)
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
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to balance teams')
    } finally {
      setLoading(false)
    }
  }

  const handleSyncLive = async () => {
    setFetchingLive(true)
    setError('')
    try {
      const players = await fetchLivePlayers()
      if (players.length === 0) {
        setError('No active players found on the server')
        return
      }
      
      const mapped = players.map(p => ({
        id: p.guid,
        name: p.name,
        sr: p.rating,
        isManual: false
      }))
      
      setSelectedPlayers(mapped)
      setManualInput('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to sync with server')
    } finally {
      setFetchingLive(false)
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

  const totalCount = selectedPlayers.length + manualInput.split('\n').map(s => s.trim()).filter(Boolean).length

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 space-y-10 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-6">
          <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-2xl p-6 space-y-4 shadow-xl">
            <div className="flex justify-between items-center">
                <h3 className="text-zinc-100 font-bold flex items-center gap-2">
                <span className="w-1.5 h-5 bg-violet-500 rounded-full" />
                Player Selection
                </h3>
                <div className="flex items-center gap-3">
                    <button 
                        onClick={handleSyncLive}
                        disabled={fetchingLive}
                        className="text-[10px] font-black px-3 py-1.5 rounded uppercase tracking-widest bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition disabled:opacity-50 flex items-center gap-2 shadow-sm"
                    >
                        {fetchingLive ? (
                            <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                        ) : (
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                        )}
                        Sync from Live Server
                    </button>
                    <span className={`text-[10px] font-black px-2 py-1.5 rounded uppercase tracking-widest border border-zinc-800 ${totalCount > 12 ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-zinc-950 text-zinc-500 shadow-inner'}`}>
                        {totalCount} Selected
                    </span>
                </div>
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
