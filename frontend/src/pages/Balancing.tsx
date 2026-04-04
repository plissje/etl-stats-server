import { useEffect, useState } from 'react'
import {
  searchPlayers, balanceTeams, fetchLivePlayers,
  type LeaderboardEntry, type BalanceResponse 
} from '../api'
import { QuakeName } from '../components/QuakeName'

export function Balancing() {
  const [selectedPlayers, setSelectedPlayers] = useState<
    { id: string; name: string; sr: number; isManual: boolean; team?: string; role?: string }[]
  >([])
  const [ignoreSpecs, setIgnoreSpecs] = useState(true)
  const [manualInput, setManualInput] = useState('')
  const [result, setResult] = useState<BalanceResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [fetchingLive, setFetchingLive] = useState(false)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<LeaderboardEntry[]>([])

  // Authentication State
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return sessionStorage.getItem('balancing_auth') === 'true'
  })
  const [passInput, setPassInput] = useState('')
  const [authError, setAuthError] = useState(false)

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    // Vite exposes env vars with VITE_ prefix
    const correctPass = import.meta.env.VITE_BALANCER_PASSWORD || "v123"
    
    // Debugging (Remove after verify)
    console.debug("[Auth] Input:", passInput, "Correct:", correctPass)
    
    if (passInput.trim() === correctPass.trim()) {
      setIsAuthenticated(true)
      sessionStorage.setItem('balancing_auth', 'true')
    } else {
      setAuthError(true)
      setTimeout(() => setAuthError(false), 600)
    }
  }

  useEffect(() => {
    if (!isAuthenticated) return
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
    const activeSelected = ignoreSpecs 
        ? selectedPlayers.filter(p => !p.team || p.team !== 'Spectator')
        : selectedPlayers
        
    const allPlayers = [
        ...activeSelected.map(p => ({ guid: p.id, name: p.name })),
        ...manualLines.map(line => ({ guid: line, name: line }))
    ]
    
    if (allPlayers.length < 2) {
      setError('Please select at least 2 players')
      return
    }

    setLoading(true)
    setError('')
    try {
      const res = await balanceTeams(allPlayers)
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
        team: p.team,
        role: p.main_role,
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
      setSelectedPlayers([...selectedPlayers, { id: p.guid, name: p.display_name, sr: p.val, isManual: false, role: 'Unknown' }])
    }
    setSearchQuery('')
    setSearchResults([])
  }

  const removePlayer = (id: string) => {
    setSelectedPlayers(selectedPlayers.filter(p => p.id !== id))
  }

  const totalCount = selectedPlayers.length + manualInput.split('\n').map(s => s.trim()).filter(Boolean).length

  return (
    <div className="relative min-h-[calc(100vh-80px)]">
      {!isAuthenticated && (
        <div className="absolute inset-0 z-40 flex items-center justify-center p-6 bg-transparent overflow-hidden">
          {/* Blurred overlay */}
          <div className="absolute inset-0 bg-zinc-950/60 backdrop-blur-3xl animate-in fade-in duration-1000" />
          
          {/* Login container */}
          <div className="relative w-full max-w-sm bg-zinc-900/80 border border-zinc-800/50 rounded-[2.5rem] p-10 shadow-2xl animate-in zoom-in-95 slide-in-from-bottom-12 duration-700">
            <form onSubmit={handleLogin} className="space-y-8">
              <div className="text-center space-y-3">
                <div className="w-16 h-16 bg-violet-600/10 rounded-3xl flex items-center justify-center mx-auto mb-6 border border-violet-500/20 shadow-inner">
                  <svg className="w-8 h-8 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <h2 className="text-2xl font-black text-white tracking-tight uppercase">Restricted</h2>
                <p className="text-zinc-500 text-xs font-bold tracking-widest uppercase opacity-60 px-4">Identify yourself to access the commander's terminal.</p>
              </div>

              <div className="space-y-5">
                <div className="relative group">
                  <input
                    type="password"
                    autoFocus
                    autoComplete="off"
                    aria-label="Commander Passcode"
                    className={`w-full bg-zinc-950/50 border ${authError ? 'border-rose-500 animate-shake' : 'border-zinc-800 group-hover:border-zinc-700'} rounded-2xl px-4 py-4 text-center text-sm font-black tracking-[0.8em] focus:outline-none focus:border-violet-500/50 transition-all duration-300 placeholder:text-zinc-800 placeholder:tracking-normal outline-none`}
                    placeholder="••••••"
                    value={passInput}
                    onChange={(e) => setPassInput(e.target.value)}
                  />
                  {authError && <p className="absolute -bottom-6 left-0 w-full text-center text-[10px] text-rose-500 font-bold uppercase tracking-widest animate-in fade-in duration-300">Invalid authorization code</p>}
                </div>
                
                <button 
                  type="submit"
                  className="w-full bg-zinc-100 hover:bg-white text-zinc-950 font-black py-4 rounded-2xl transition-all duration-300 shadow-[0_0_20px_rgba(255,255,255,0.1)] active:scale-95 uppercase tracking-[0.2em] text-[11px] cursor-pointer"
                >
                  Authorize
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className={`mx-auto max-w-[1400px] px-4 py-10 space-y-10 animate-in fade-in slide-in-from-bottom-2 duration-500 ${!isAuthenticated ? 'pointer-events-none' : ''}`}>
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
                        onClick={() => setIgnoreSpecs(!ignoreSpecs)}
                        className={`text-[10px] font-black px-3 py-1.5 rounded uppercase tracking-widest border transition flex items-center gap-2 shadow-sm ${ignoreSpecs ? 'bg-amber-500/10 text-amber-400 border-amber-500/20 hover:bg-amber-500/20' : 'bg-zinc-800/10 text-zinc-500 border-zinc-800/50 hover:bg-zinc-800/20'}`}
                        title="Skip Spectators during balancing"
                    >
                        <div className={`w-2 h-2 rounded-full ${ignoreSpecs ? 'bg-amber-500' : 'bg-zinc-700'}`} />
                        Ignore Specs
                    </button>
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
                        Sync
                    </button>
                    <span className={`text-[10px] font-black px-2 py-1.5 rounded uppercase tracking-widest border border-zinc-800 ${totalCount > 12 ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-zinc-950 text-zinc-500 shadow-inner'}`}>
                        {totalCount}
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
                    <div className="space-y-3">
               <label className="text-[10px] text-zinc-500 uppercase font-black tracking-widest px-1">Selected List</label>
               <div className="min-h-[120px] max-h-[300px] overflow-y-auto custom-scrollbar bg-zinc-950/30 rounded-xl border border-zinc-800/40 relative">
                  <table className="w-full border-collapse">
                    <thead className="sticky top-0 bg-zinc-950/90 backdrop-blur-md z-10 border-b border-zinc-800/50 shadow-sm">
                        <tr className="text-[9px] uppercase tracking-widest font-black text-zinc-500">
                            <th className="px-4 py-2.5 text-left border-r border-zinc-800/30">Player</th>
                            <th className="px-4 py-2.5 text-center border-r border-zinc-800/30 w-20">Role</th>
                            <th className="px-4 py-2.5 text-center border-r border-zinc-800/30 w-20">Team</th>
                            <th className="px-4 py-2.5 text-right border-r border-zinc-800/30 w-20">SR</th>
                            <th className="px-4 py-2.5 w-10"></th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-900/50">
                        {selectedPlayers.map(p => (
                            <tr key={p.id} className={`transition group ${p.team === 'Spectator' && ignoreSpecs ? 'opacity-30 grayscale' : 'hover:bg-zinc-800/20'}`}>
                                <td className="px-4 py-2">
                                    <div className="flex flex-col">
                                        <span className="text-sm font-semibold text-zinc-200 truncate max-w-[180px]"><QuakeName name={p.name} /></span>
                                        <span className="text-[9px] text-zinc-700 font-mono tracking-widest">[{p.id.slice(0, 12).toUpperCase()}]</span>
                                    </div>
                                </td>
                                <td className="px-4 py-2 text-center">
                                    {p.role && p.role !== 'Unknown' && (
                                        <span className={`text-[9px] font-black px-1.5 py-0.5 rounded uppercase tracking-tighter shadow-sm border whitespace-nowrap ${
                                            p.role === 'Medic' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                            p.role === 'Rifle/Eng' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                                            p.role === 'Field Ops' ? 'bg-sky-500/10 text-sky-400 border-sky-500/20' :
                                            p.role === 'Engineer' ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
                                            'bg-zinc-800 text-zinc-400'
                                        }`}>
                                            {p.role === 'Rifle/Eng' ? 'R/E' : 
                                             p.role === 'Field Ops' ? 'FOP' : 
                                             p.role === 'Engineer' ? 'ENG' :
                                             p.role.charAt(0)}
                                        </span>
                                    )}
                                </td>
                                <td className="px-4 py-2 text-center">
                                    {p.team && (
                                        <span className={`text-[9px] font-black uppercase tracking-widest ${
                                            p.team === 'Axis' ? 'text-rose-500/80' : 
                                            p.team === 'Allies' ? 'text-sky-500/80' : 
                                            'text-zinc-600'
                                        }`}>
                                            {p.team === 'Spectator' ? 'SPEC' : p.team.slice(0, 2)}
                                        </span>
                                    )}
                                </td>
                                <td className="px-4 py-2 text-right">
                                    <span className="text-violet-400 font-mono text-xs font-black">{Math.round(p.sr)}</span>
                                </td>
                                <td className="px-4 py-2 text-center">
                                    <button 
                                        onClick={() => removePlayer(p.id)}
                                        className="text-zinc-600 hover:text-rose-500 transition-colors text-xl leading-none px-1"
                                    >
                                        ×
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                  </table>
                  {selectedPlayers.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-12 space-y-2">
                        <div className="w-12 h-12 bg-zinc-900 rounded-full flex items-center justify-center border border-zinc-800">
                            <svg className="w-6 h-6 text-zinc-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                            </svg>
                        </div>
                        <span className="text-zinc-600 text-[10px] uppercase font-black tracking-widest italic">No players selected</span>
                    </div>
                  )}
               </div>
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
               <div className="grid grid-cols-2 gap-6 items-stretch">
                  <div className="bg-zinc-900/60 border border-rose-500/20 rounded-[2rem] p-6 shadow-[0_0_30px_rgba(244,63,94,0.1)] flex flex-col h-full overflow-hidden">
                     <div className="flex justify-between items-start mb-6">
                        <div className="space-y-1">
                           <div className="text-rose-500 text-[11px] font-black uppercase tracking-[0.2em]">Team Alpha</div>
                           <div className="text-4xl font-black text-rose-400 leading-none">{Math.round(result.alpha_avg_sr)}</div>
                        </div>
                        <div className="text-[10px] text-zinc-600 font-bold uppercase tracking-widest pt-1">Avg SR</div>
                     </div>
                     <div className="flex-1 overflow-hidden">
                        <table className="w-full border-collapse">
                           <thead>
                              <tr className="text-[9px] uppercase tracking-widest font-black text-zinc-600 border-b border-zinc-800/50">
                                 <th className="px-2 py-2 text-left">Player</th>
                                 <th className="px-2 py-2 text-center w-12">Role</th>
                                 <th className="px-2 py-2 text-right w-16">SR</th>
                              </tr>
                           </thead>
                           <tbody className="divide-y divide-zinc-900/50">
                              {result.alpha.map(p => {
                                const sp = selectedPlayers.find(s => s.id === p.guid);
                                const role = sp?.role;
                                return (
                                  <tr key={p.guid} className="group hover:bg-rose-500/5 transition-colors">
                                    <td className="px-2 py-3">
                                      <div className="text-sm font-semibold text-zinc-100 truncate max-w-[120px] xl:max-w-[180px]">
                                        <QuakeName name={p.name} />
                                      </div>
                                    </td>
                                    <td className="px-2 py-3 text-center">
                                      {role && role !== 'Unknown' && (
                                        <span className={`text-[8px] font-black px-1 rounded uppercase tracking-tighter border ${
                                            role === 'Medic' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                            role === 'Rifle/Eng' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                                            role === 'Field Ops' ? 'bg-sky-500/10 text-sky-400 border-sky-500/20' :
                                            role === 'Engineer' ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
                                            'bg-zinc-800 text-zinc-400'
                                        }`}>
                                            {role === 'Rifle/Eng' ? 'R/E' : 
                                             role === 'Field Ops' ? 'FOP' : 
                                             role === 'Engineer' ? 'ENG' :
                                             role.charAt(0)}
                                        </span>
                                      )}
                                    </td>
                                    <td className="px-2 py-3 text-right">
                                      <span className="text-zinc-500 font-mono text-[10px] font-bold">{Math.round(p.rating)}</span>
                                    </td>
                                  </tr>
                                );
                              })}
                           </tbody>
                        </table>
                     </div>
                  </div>
                  <div className="bg-zinc-900/60 border border-sky-500/20 rounded-[2rem] p-6 shadow-[0_0_30px_rgba(14,165,233,0.1)] flex flex-col h-full overflow-hidden">
                     <div className="flex justify-between items-start mb-6">
                        <div className="space-y-1">
                           <div className="text-sky-500 text-[11px] font-black uppercase tracking-[0.2em]">Team Beta</div>
                           <div className="text-4xl font-black text-sky-400 leading-none">{Math.round(result.beta_avg_sr)}</div>
                        </div>
                        <div className="text-[10px] text-zinc-600 font-bold uppercase tracking-widest pt-1">Avg SR</div>
                     </div>
                     <div className="flex-1 overflow-hidden">
                        <table className="w-full border-collapse">
                           <thead>
                              <tr className="text-[9px] uppercase tracking-widest font-black text-zinc-600 border-b border-zinc-800/50">
                                 <th className="px-2 py-2 text-left">Player</th>
                                 <th className="px-2 py-2 text-center w-12">Role</th>
                                 <th className="px-2 py-2 text-right w-16">SR</th>
                              </tr>
                           </thead>
                           <tbody className="divide-y divide-zinc-900/50">
                              {result.beta.map(p => {
                                const sp = selectedPlayers.find(s => s.id === p.guid);
                                const role = sp?.role;
                                return (
                                  <tr key={p.guid} className="group hover:bg-sky-500/5 transition-colors">
                                    <td className="px-2 py-3">
                                      <div className="text-sm font-semibold text-zinc-100 truncate max-w-[120px] xl:max-w-[180px]">
                                        <QuakeName name={p.name} />
                                      </div>
                                    </td>
                                    <td className="px-2 py-3 text-center">
                                      {role && role !== 'Unknown' && (
                                        <span className={`text-[8px] font-black px-1 rounded uppercase tracking-tighter border ${
                                            role === 'Medic' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                            role === 'Rifle/Eng' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                                            role === 'Field Ops' ? 'bg-sky-500/10 text-sky-400 border-sky-500/20' :
                                            role === 'Engineer' ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
                                            'bg-zinc-800 text-zinc-400'
                                        }`}>
                                            {role === 'Rifle/Eng' ? 'R/E' : 
                                             role === 'Field Ops' ? 'FOP' : 
                                             role === 'Engineer' ? 'ENG' :
                                             role.charAt(0)}
                                        </span>
                                      )}
                                    </td>
                                    <td className="px-2 py-3 text-right">
                                      <span className="text-zinc-500 font-mono text-[10px] font-bold">{Math.round(p.rating)}</span>
                                    </td>
                                  </tr>
                                );
                              })}
                           </tbody>
                        </table>
                     </div>
                  </div>
               </div>

      {/* Tactical Action Bar - 2-Row Optimized Layout */}
      {result && (
        <div className="animate-in slide-in-from-bottom-4 duration-500 delay-150">
          <div className="bg-zinc-900/40 border border-zinc-800/80 p-6 rounded-[2rem] flex flex-col gap-6 shadow-2xl backdrop-blur-md">
            
            {/* Row 1: Informational Data */}
            <div className="flex items-center justify-between">
               <div className="flex items-center gap-10">
                  <div className="flex flex-col">
                     <span className="text-zinc-600 text-[10px] font-black uppercase tracking-[0.2em] mb-1">Statistical Variance</span>
                     <div className="flex items-center gap-3">
                        <span className={`text-3xl font-black leading-none ${result.diff < 50 ? 'text-emerald-400' : 'text-amber-400'}`}>
                           {Math.round(result.diff)}
                        </span>
                        <div className="flex flex-col">
                           <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest leading-tight">SR DIFF</span>
                           <span className={`text-[9px] font-black uppercase tracking-widest ${result.diff < 50 ? 'text-emerald-500/80' : 'text-amber-500/80'}`}>
                              {result.diff < 20 ? 'Optimal' : result.diff < 50 ? 'Balanced' : 'High Variance'}
                           </span>
                        </div>
                     </div>
                  </div>

                  <div className="h-10 w-px bg-zinc-800/50" />

                  <div className="flex flex-col">
                     <span className="text-zinc-600 text-[10px] font-black uppercase tracking-[0.2em] mb-2">Tactical Spread</span>
                     <div className="flex gap-3">
                        <div className="flex items-center gap-2 bg-zinc-950/40 px-3 py-1.5 rounded-xl border border-zinc-800/50">
                           <div className="w-1.5 h-1.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.4)]" />
                           <span className="text-[11px] text-zinc-400 font-black uppercase tracking-[0.2em] leading-none">Alpha</span>
                        </div>
                        <div className="flex items-center gap-2 bg-zinc-950/40 px-3 py-1.5 rounded-xl border border-zinc-800/50">
                           <div className="w-1.5 h-1.5 rounded-full bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.4)]" />
                           <span className="text-[11px] text-zinc-400 font-black uppercase tracking-[0.2em] leading-none">Beta</span>
                        </div>
                     </div>
                  </div>
               </div>

               <div className="text-right flex flex-col justify-center">
                  <span className="text-zinc-500 text-[10px] font-black uppercase tracking-[0.2em] mb-0.5">Fleet Status</span>
                  <span className="text-[9px] text-emerald-500/60 font-bold uppercase tracking-widest animate-pulse">Comms Link Stable</span>
               </div>
            </div>

            <div className="h-px w-full bg-zinc-800/30" />

            {/* Row 2: Action Terminal */}
            <div className="flex items-center justify-between">
               <div className="flex flex-col">
                  <span className="text-zinc-600 text-[10px] font-black uppercase tracking-[0.2em] mb-1">Commander's Terminal</span>
                  <div className="flex items-center gap-2">
                     <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-ping" />
                     <span className="text-xs text-zinc-400 font-medium uppercase tracking-widest opacity-80">Ready for team resonance deployment</span>
                  </div>
               </div>

               <button 
                 disabled
                 className="bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 px-10 py-4 rounded-2xl text-[12px] font-black uppercase tracking-[0.3em] hover:bg-indigo-500/20 transition-all cursor-not-allowed flex items-center gap-4 shadow-[0_0_30px_rgba(99,102,241,0.05)] active:scale-95 group relative overflow-hidden"
               >
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-indigo-400/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
                  <svg className="w-5 h-5 text-indigo-400 opacity-70 group-hover:scale-110 transition-transform" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                  Assign Teams in Game
               </button>
            </div>
          </div>
        </div>
      )}
            </div>
          )}
        </div>
      </div>
      </div>
    </div>
  )
}
