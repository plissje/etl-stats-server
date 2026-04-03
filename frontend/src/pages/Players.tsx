import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { searchPlayers, type LeaderboardEntry } from '../api'
import { QuakeName } from '../components/QuakeName'

export function Players() {
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
                  <QuakeName name={p.raw_name || p.display_name} />
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
