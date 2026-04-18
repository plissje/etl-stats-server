import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchLeaderboards, type Leaderboards, type LeaderboardEntry } from '../api'
import { QuakeName } from '../components/QuakeName'

const RenderBoard = ({ title, data, suffix, icon }: { title: string, data: LeaderboardEntry[], suffix: string, icon: React.ReactNode }) => (
  <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl shadow-xl overflow-hidden hover:border-zinc-700/80 transition duration-300">
    <div className="bg-zinc-800/50 px-5 py-3 font-semibold tracking-wide text-zinc-200 border-b border-zinc-800/60 flex items-center gap-2">
      {icon}
      {title}
    </div>
    <ul className="divide-y divide-zinc-800/40">
      {data.map((p, i) => (
        <li key={p.guid} className="flex justify-between items-center px-5 py-3 transition hover:bg-zinc-800/30 group overflow-hidden">
          <Link to={`/player/${p.guid}`} className="flex gap-3 hover:text-white text-zinc-300 font-medium items-center min-w-0">
            <span className={`w-5 flex-shrink-0 text-center font-bold text-sm ${i === 0 ? 'text-amber-400' : i === 1 ? 'text-zinc-300' : i === 2 ? 'text-amber-700' : 'text-zinc-600'}`}>{i + 1}.</span> 
            <span className="group-hover:translate-x-1 transition duration-200 truncate">
              <QuakeName name={p.display_name} />
            </span>
          </Link>
          <span className="text-violet-400/90 font-mono text-sm font-medium whitespace-nowrap pl-4">{p.val.toLocaleString()} <span className="text-zinc-600 text-xs">{suffix}</span></span>
        </li>
      ))}
      {data.length === 0 && <li className="p-6 text-center text-zinc-600 border-dashed">No participants yet.</li>}
    </ul>
  </div>
)

export function Leaderboards() {
  const [boards, setBoards] = useState<Leaderboards | null>(null)
  useEffect(() => { fetchLeaderboards().then(setBoards).catch(console.error) }, [])

  if (!boards) return (
    <div className="mx-auto max-w-6xl px-4 py-10 animate-pulse flex gap-6 mt-8">
      <div className="w-full h-64 border border-zinc-800 rounded-xl bg-zinc-900/30"></div>
      <div className="w-full h-64 border border-zinc-800 rounded-xl bg-zinc-900/30"></div>
      <div className="w-full h-64 border border-zinc-800 rounded-xl bg-zinc-900/30"></div>
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
        suffix="HS %" 
        icon={<svg className="w-4 h-4 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>}
      />
      <RenderBoard 
        title="Top Killers" 
        data={boards.killer} 
        suffix="AVG KILLS" 
        icon={<svg className="w-4 h-4 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z" /></svg>}
      />
      <RenderBoard 
        title="Undertakers" 
        data={boards.undertaker} 
        suffix="AVG GIBS" 
        icon={<svg className="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>}
      />
      <RenderBoard 
        title="SMG Accuracy" 
        data={boards.accuracy_smg} 
        suffix="SMG %" 
        icon={<svg className="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
      />
    </div>
  )
}
