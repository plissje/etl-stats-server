import { Fragment, useEffect, useState, useCallback } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchMatch, type MatchDetail, type PlayerRow } from '../api'
import { QuakeName } from '../components/QuakeName'

type SortKey = keyof Pick<PlayerRow,
  'eff' | 'kdr' | 'kills' | 'deaths' | 'damage_given' | 'damage_received' |
  'headshots' | 'gibs' | 'self_kills' | 'team_kills' | 'revives' | 'time_played_pct' | 'unified_eff' | 'sr_delta'
>
type SortDir = 'asc' | 'desc'

function AwardCard({ emoji, title, value, subtext, empty }: { emoji: string, title: string, value: React.ReactNode, subtext?: string, empty?: boolean }) {
  return (
    <div className={`bg-zinc-900/40 border ${empty ? 'border-zinc-800/20 opacity-40' : 'border-zinc-800/80 shadow-sm hover:border-violet-500/20'} rounded-xl p-4 flex items-start gap-4 transition-colors`}>
      <div className={`text-2xl mt-0.5 select-none ${empty ? 'grayscale' : ''}`}>{emoji}</div>
      <div className="overflow-hidden">
        <p className="text-sm font-semibold text-zinc-400 mb-1">{title}</p>
        <p className="text-lg font-bold text-zinc-100 truncate">{value}</p>
        {subtext && <p className="text-xs text-zinc-500 mt-1">{subtext}</p>}
      </div>
    </div>
  )
}

const CLASS_ICONS: Record<string, string> = {
  soldier: '🪖',
  medic: '💉',
  engineer: '🔧',
  fieldop: '🎒',
  covertops: '🕶️'
}

function PlayerMatchDetails({ row }: { row: PlayerRow }) {
  const uniqueClasses = Array.from(new Set(row.classes_played?.map(c => c.toClass).filter(Boolean) || []))

  return (
    <div className="p-4 md:p-6 bg-zinc-900/80 border-b border-zinc-700 shadow-inner text-sm space-y-6">
      {row.weapon_breakdown && row.weapon_breakdown.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-zinc-300 min-w-[500px]">
            <thead className="text-xs text-zinc-500 border-b border-zinc-700/50 uppercase tracking-wider">
              <tr>
                <th className="py-2 font-medium">Weapon</th>
                <th className="py-2 font-medium text-right">Accuracy</th>
                <th className="py-2 font-medium text-right">Hits / Shots</th>
                <th className="py-2 font-medium text-right">Kills</th>
                <th className="py-2 font-medium text-right">Deaths</th>
                <th className="py-2 font-medium text-right">Headshots</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/30">
              {row.weapon_breakdown.filter(w => w.shots > 0 || w.kills > 0).map(w => {
                const acc = w.shots > 0 ? Math.min(100, Math.round((w.hits / w.shots) * 100)) : 0;
                return (
                  <tr key={w.name} className="hover:bg-zinc-800/30">
                    <td className="py-1.5">{w.name.replace('WS_', '')}</td>
                    <td className="py-1.5 text-right font-mono text-zinc-400">{w.shots > 0 ? `${acc}%` : '-'}</td>
                    <td className="py-1.5 text-right font-mono text-zinc-400">{w.hits} / {w.shots}</td>
                    <td className="py-1.5 text-right font-mono text-zinc-200">{w.kills}</td>
                    <td className="py-1.5 text-right font-mono text-zinc-400">{w.deaths}</td>
                    <td className="py-1.5 text-right font-mono text-zinc-400">{w.headshots}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-8 text-zinc-400 pt-6 border-t border-zinc-800/80 max-w-5xl">
        <div className="space-y-2">
          <div className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest mb-1">Travel</div>
          <div className="flex justify-between items-center bg-zinc-800/20 px-3 py-1.5 rounded-md border border-zinc-700/20"><span>Distance:</span> <span className="text-zinc-200 font-mono font-semibold">{Math.round(row.distance_travelled_meters || 0)}m</span></div>
          <div className="flex justify-between items-center bg-zinc-800/20 px-3 py-1.5 rounded-md border border-zinc-700/20"><span>Spawn Avg:</span> <span className="text-zinc-300 font-mono">{Math.round(row.distance_travelled_spawn_avg || 0)}m</span></div>
        </div>
        
        <div className="space-y-2">
          <div className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest mb-1">Movement</div>
          <div className="flex justify-between items-center bg-zinc-800/20 px-3 py-1.5 rounded-md border border-zinc-700/20"><span>Crouched:</span> <span className="text-zinc-300 font-mono">{Math.floor((row.crouched_seconds || 0)/60)}m {(row.crouched_seconds || 0)%60}s</span></div>
          <div className="flex justify-between items-center bg-zinc-800/20 px-3 py-1.5 rounded-md border border-zinc-700/20"><span>Proned:</span> <span className="text-zinc-300 font-mono">{Math.floor((row.proned_seconds || 0)/60)}m {(row.proned_seconds || 0)%60}s</span></div>
          <div className="flex justify-between items-center bg-zinc-800/20 px-3 py-1.5 rounded-md border border-zinc-700/20"><span>Leaned:</span> <span className="text-zinc-300 font-mono">{Math.floor((row.leaned_seconds || 0)/60)}m {(row.leaned_seconds || 0)%60}s</span></div>
        </div>

        <div className="space-y-2">
          <div className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest mb-1">Profile</div>
          <div className="flex justify-between items-center bg-zinc-800/20 px-3 py-1.5 rounded-md border border-zinc-700/20">
            <span>XP:</span> 
            <span className="text-violet-300 font-mono font-bold">{Math.round(row.xp || 0)}</span>
          </div>
          {uniqueClasses.length > 0 && (
            <div className="flex flex-col gap-2 bg-zinc-800/20 px-3 py-2 rounded-md border border-zinc-700/20 min-h-[44px] justify-center">
              <span className="text-zinc-500 text-[9px] font-bold uppercase tracking-wider opacity-60">Classes Summary</span>
              <div className="flex gap-2.5">
                {uniqueClasses.map(c => (
                  <span key={c} title={c} className="text-xl select-none filter drop-shadow-lg scale-110 hover:scale-125 transition-transform duration-200">
                    {CLASS_ICONS[c] || c}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const COLS: { key: SortKey; label: string; title?: string; defaultDesc?: boolean; width: string }[] = [
  { key: 'eff', label: 'EFF', title: 'Standard Efficiency', defaultDesc: true, width: '55px' },
  { key: 'kdr', label: 'KDR', title: 'Kill/Death Ratio', defaultDesc: true, width: '55px' },
  { key: 'kills', label: 'K', title: 'Kills', defaultDesc: true, width: '45px' },
  { key: 'deaths', label: 'D', title: 'Deaths', defaultDesc: false, width: '45px' },
  { key: 'damage_given', label: 'DMG G', title: 'Damage Given', defaultDesc: true, width: '75px' },
  { key: 'damage_received', label: 'DMG R', title: 'Damage Received', defaultDesc: false, width: '75px' },
  { key: 'headshots', label: 'HS', title: 'Headshots', defaultDesc: true, width: '45px' },
  { key: 'gibs', label: 'GIB', title: 'Gibs', defaultDesc: true, width: '45px' },
  { key: 'self_kills', label: 'SK', title: 'Self Kills', defaultDesc: false, width: '45px' },
  { key: 'team_kills', label: 'TK', title: 'Team Kills', defaultDesc: false, width: '45px' },
  { key: 'revives', label: 'REV', title: 'Revives', defaultDesc: true, width: '50px' },
  { key: 'time_played_pct', label: 'TIME', title: 'Time Played %', defaultDesc: true, width: '55px' },
  { key: 'unified_eff', label: 'UE', title: 'Unified Efficiency', defaultDesc: true, width: '70px' },
  { key: 'sr_delta', label: 'SR Δ', title: 'Skill Rating Change', defaultDesc: true, width: '60px' },
]

function colColor(key: SortKey, val: number, row?: PlayerRow): string {
  if (key === 'kdr') {
    if (val > 1.0) return 'text-emerald-400'
    if (val < 1.0) return 'text-rose-400'
    return 'text-zinc-300'
  }
  if (key === 'damage_given' && row) {
    if (val > row.damage_received) return 'text-emerald-400'
    return 'text-zinc-300'
  }
  if (key === 'damage_received' && row) {
    if (val > row.damage_given) return 'text-rose-400'
    return 'text-zinc-300'
  }
  if (key === 'sr_delta') {
    if (val > 0) return 'text-emerald-400 font-bold'
    if (val < 0) return 'text-rose-400'
    return 'text-zinc-500'
  }
  return 'text-zinc-300'
}

function formatVal(key: SortKey, val: number): string {
  if (key === 'eff') return Math.round(val).toString()
  if (key === 'unified_eff' || key === 'kdr') return val % 1 === 0 ? val.toString() : val.toFixed(1)
  if (key === 'time_played_pct') return val ? Math.round(val) + '%' : '-'
  if (key === 'sr_delta') return val !== undefined && val !== null ? (val > 0 ? `+${val.toFixed(1)}` : val.toFixed(1)) : '-'
  return val.toString()
}

function ScoreTable({
  title, accent, rows,
  sortKey, sortDir, onSort,
}: {
  title: string
  accent: string
  rows: PlayerRow[]
  sortKey: SortKey
  sortDir: SortDir
  onSort: (k: SortKey) => void
}) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  const toggleRow = (guid: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev)
      if (next.has(guid)) next.delete(guid)
      else next.add(guid)
      return next
    })
  }

  const sorted = [...rows].sort((a, b) => {
    const av = a[sortKey] as number
    const bv = b[sortKey] as number
    return sortDir === 'desc' ? bv - av : av - bv
  })

  const totals: Record<SortKey, number> = {} as Record<SortKey, number>
  for (const col of COLS) {
    if (col.key === 'eff' || col.key === 'unified_eff' || col.key === 'kdr' || col.key === 'time_played_pct') {
      totals[col.key] = rows.length ? rows.reduce((s, r) => s + (r[col.key] as number), 0) / rows.length : 0
    } else {
      totals[col.key] = rows.reduce((s, r) => s + ((r[col.key] || 0) as number), 0)
    }
  }

  return (
    <div className="w-full">
      <h2 className={`mb-3 text-lg font-bold tracking-wide ${accent}`}>{title}</h2>
      <div className="overflow-x-auto rounded-xl border border-zinc-800 shadow-xl bg-zinc-950/50">
        <table className="w-full min-w-[950px] border-collapse text-left whitespace-nowrap table-fixed">
          <thead>
            <tr className="border-b border-zinc-800/80 bg-zinc-900/60">
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-zinc-500 w-[260px]">Name</th>
              {COLS.map(col => (
                <th
                  key={col.key}
                  title={col.title}
                  onClick={() => onSort(col.key)}
                  style={{ width: col.width }}
                  className={`py-3 text-center text-xs font-semibold uppercase tracking-wider cursor-pointer select-none transition-colors px-1 ${
                    sortKey === col.key ? 'text-violet-400' : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  <span className="flex items-center justify-center gap-1">
                    {col.label}
                    {sortKey === col.key ? (
                      <span className="text-violet-400 opacity-80">{sortDir === 'desc' ? '↓' : '↑'}</span>
                    ) : (
                      <span className="opacity-20">↕</span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/50">
            {sorted.map(r => (
              <Fragment key={r.player_guid}>
                <tr className="hover:bg-zinc-800/40 transition-colors group cursor-pointer" onClick={() => toggleRow(r.player_guid)}>
                  <td className="px-4 py-2 font-medium flex items-center gap-4">
                    <span className="text-zinc-600 group-hover:text-zinc-400 transition-colors select-none w-3 inline-block">
                      {expandedRows.has(r.player_guid) ? '▼\uFE0E' : '▶\uFE0E'}
                    </span>
                    <Link
                      to={`/player/${encodeURIComponent(r.player_guid)}`}
                      onClick={e => e.stopPropagation()}
                      className="hover:brightness-150 transition-all opacity-90 hover:opacity-100"
                      title={r.name_raw || undefined}
                      style={{ textDecoration: 'none' }}
                    >
                      <QuakeName name={r.name_display} />
                    </Link>
                  </td>
                  {COLS.map(col => {
                    const val = (r[col.key] || 0) as number
                    return (
                      <td key={col.key} style={{ width: col.width }} className={`py-2 text-center font-mono text-[13px] px-1 overflow-hidden text-ellipsis ${colColor(col.key, val, r)}`}>
                        {formatVal(col.key, val)}
                      </td>
                    )
                  })}
                </tr>
                {expandedRows.has(r.player_guid) && (
                  <tr>
                    <td colSpan={COLS.length + 1} className="p-0 border-b border-zinc-700 bg-zinc-950">
                      <PlayerMatchDetails row={r} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {rows.length > 0 && (
              <tr className="bg-zinc-900/80 font-semibold border-t border-zinc-700">
                <td className="px-4 py-3 text-zinc-300 text-sm">Total</td>
                {COLS.map(col => (
                  <td key={col.key} style={{ width: col.width }} className={`py-3 text-center font-mono text-zinc-300 text-[13px] px-1 overflow-hidden text-ellipsis`}>
                    {formatVal(col.key, totals[col.key])}
                  </td>
                ))}
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function MatchDetail() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<MatchDetail | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [sortKey, setSortKey] = useState<SortKey>('unified_eff')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [activeTab, setActiveTab] = useState<'total' | 'round1' | 'round2'>('total')

  useEffect(() => {
    if (!id) return
    fetchMatch(Number(id)).then(setData).catch(() => setErr('Match not found'))
  }, [id])

  const handleSort = useCallback((key: SortKey) => {
    setSortKey(prev => {
      if (prev === key) {
        setSortDir(d => d === 'desc' ? 'asc' : 'desc')
      } else {
        const col = COLS.find(c => c.key === key)
        setSortDir(col?.defaultDesc === false ? 'asc' : 'desc')
      }
      return key
    })
  }, [])

  if (err || !data) {
    return (
      <div className="p-8 text-center animate-in fade-in duration-500">
        <p className="text-rose-400 font-medium">{err || 'Loading Match Data...'}</p>
        <Link to="/matches" className="mt-4 inline-block text-violet-400 hover:text-violet-300 underline">
          Return to Matches
        </Link>
      </div>
    )
  }

  const { match, axis, allies, axis_round1, allies_round1, axis_round2, allies_round2, round1_alpha_side, round2_alpha_side } = data
  const allPlayers = [...axis, ...allies]

  const r1_alpha_side = round1_alpha_side ?? 1
  const r2_alpha_side = round2_alpha_side ?? 2

  let alphaRows = r1_alpha_side === 1 ? axis : allies
  let betaRows = r1_alpha_side === 1 ? allies : axis
  let alphaSide = r1_alpha_side
  let betaSide = r1_alpha_side === 1 ? 2 : 1

  if (activeTab === 'round1' && axis_round1 && allies_round1 && axis_round1.length > 0) {
    alphaRows = r1_alpha_side === 1 ? axis_round1 : allies_round1
    betaRows = r1_alpha_side === 1 ? allies_round1 : axis_round1
    alphaSide = r1_alpha_side
    betaSide = r1_alpha_side === 1 ? 2 : 1
  } else if (activeTab === 'round2' && axis_round2 && allies_round2 && axis_round2.length > 0) {
    alphaRows = r2_alpha_side === 1 ? axis_round2 : allies_round2
    betaRows = r2_alpha_side === 1 ? allies_round2 : axis_round2
    alphaSide = r2_alpha_side
    betaSide = r2_alpha_side === 1 ? 2 : 1
  }

  const sideLabel = (side: number) => side === 1 ? 'Axis' : 'Allies'
  const sideColor = (side: number) => side === 1 ? 'text-rose-400' : 'text-sky-400'

  const topFragger = allPlayers.length ? allPlayers.reduce((m, p) => p.kills > m.kills ? p : m, allPlayers[0]) : null
  const topMedic = allPlayers.length ? allPlayers.reduce((m, p) => p.revives > m.revives ? p : m, allPlayers[0]) : null
  const topTK = allPlayers.length ? allPlayers.reduce((m, p) => (p.team_kills||0) > (m.team_kills||0) ? p : m, allPlayers[0]) : null

  const topSpammer = allPlayers.length ? allPlayers.reduce((m, p) => (p.spam_kills||0) > (m.spam_kills||0) ? p : m, allPlayers[0]) : null
  const eligibleIpod = allPlayers.filter(p => p.time_played_pct > 30)
  const topIpod = eligibleIpod.length ? eligibleIpod.reduce((m, p) => p.deaths < m.deaths ? p : m, eligibleIpod[0]) : (allPlayers.length ? allPlayers.reduce((m, p) => p.deaths < m.deaths ? p : m, allPlayers[0]) : null)

  const duration = match.round_start_unix > 0 && match.round_end_unix > match.round_start_unix
    ? (() => {
        const s = match.round_end_unix - match.round_start_unix
        return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`
      })() : null

  const matchDate = match.round_start_unix > 0
    ? new Date(match.round_start_unix * 1000).toLocaleDateString()
    : null

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <Link to="/matches" className="text-sm text-violet-400 hover:text-violet-300 hover:underline flex items-center gap-1 mb-6 w-fit">
        ← Back to Matches
      </Link>

      <header className="mb-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-4xl font-black tracking-tight text-white mb-1">{match.mapname.toUpperCase()}</h1>
            <div className="flex items-center gap-3 text-sm flex-wrap">
            <div className={`px-2.5 py-1 text-xs font-bold rounded uppercase border ${
              match.winner_team === 1 ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' :
              match.winner_team === 2 ? 'bg-sky-500/20 text-sky-400 border-sky-500/30' :
              'bg-zinc-500/20 text-zinc-400 border-zinc-500/30'
            }`}>
              {match.winner_team === 1 ? 'Alpha Win' : 
               match.winner_team === 2 ? 'Beta Win' : 'Draw Match'}
            </div>
              {duration && <span className="text-zinc-400 font-mono bg-zinc-800/80 px-2 py-1 rounded">{duration}</span>}
              {(match.round1_duration || match.round2_duration) && (
                <div className="flex items-center gap-2 text-zinc-500 font-mono text-xs bg-zinc-900/50 px-2.5 py-1 rounded border border-zinc-800">
                  <span className="text-zinc-600 uppercase text-[9px] font-bold tracking-tighter mr-1">Set Times</span>
                  <div className="flex items-center gap-1.5">
                    <span className={`text-[10px] font-bold ${match.round1_duration && match.round2_duration && match.round1_duration < match.round2_duration ? 'text-emerald-400' : 'text-zinc-500'}`}>
                      <span className="opacity-50 mr-0.5">β:</span>
                      {match.round1_duration ? `${Math.floor(match.round1_duration/60)}:${String(match.round1_duration%60).padStart(2,'0')}` : '—'}
                    </span>
                    <span className="opacity-30">/</span>
                    <span className={`text-[10px] font-bold ${match.round1_duration && match.round2_duration && match.round2_duration < match.round1_duration ? 'text-emerald-400' : 'text-zinc-500'}`}>
                      <span className="opacity-50 mr-0.5">α:</span>
                      {match.round2_duration ? `${Math.floor(match.round2_duration/60)}:${String(match.round2_duration%60).padStart(2,'0')}` : '—'}
                    </span>
                  </div>
                </div>
              )}
              {matchDate && <span className="text-zinc-500 font-mono text-xs">{matchDate}</span>}
            </div>
          </div>
        </div>
      </header>

      {/* Awards */}
      {allPlayers.length > 0 && (
        <div className="bg-zinc-800/40 rounded-xl p-4 md:p-6 border border-white/5 space-y-4 mb-8">
          <h2 className="text-xl font-bold text-white mb-4 shadow-sm">Match Awards</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <AwardCard 
              emoji="🏆" 
              title="MVP" 
              value={match.mvp_name ? <QuakeName name={match.mvp_name} /> : "N/A"} 
              subtext="Highest overall contribution" 
              empty={!match.mvp_name}
            />
            <AwardCard 
              emoji="⚔️" 
              title="Top Killer" 
              value={topFragger ? <QuakeName name={topFragger.name_display} /> : "N/A"} 
              subtext={topFragger ? `${topFragger.kills} kills` : "0 kills"} 
              empty={!topFragger || topFragger.kills === 0}
            />
            <AwardCard 
              emoji="💉" 
              title="Top Medic" 
              value={topMedic ? <QuakeName name={topMedic.name_display} /> : "N/A"} 
              subtext={topMedic ? `${topMedic.revives} revives` : "0 revives"} 
              empty={!topMedic || topMedic.revives === 0}
            />
            <AwardCard 
              emoji="💥" 
              title="Spammer" 
              value={topSpammer ? <QuakeName name={topSpammer.name_display} /> : "N/A"} 
              subtext={topSpammer ? `${topSpammer.spam_kills} spamkills` : "0 spamkills"} 
              empty={!topSpammer || topSpammer.spam_kills === 0}
            />
            <AwardCard 
              emoji="🎧" 
              title="iPod" 
              value={topIpod ? <QuakeName name={topIpod.name_display} /> : "N/A"} 
              subtext={topIpod ? `${topIpod.deaths} deaths (Fewest)` : "N/A"} 
              empty={!topIpod}
            />
            <AwardCard 
              emoji="🔥" 
              title="Friendly Fire" 
              value={topTK && (topTK.team_kills || 0) > 0 ? <QuakeName name={topTK.name_display} /> : "Clean"} 
              subtext={topTK ? `${topTK.team_kills || 0} Team Kills` : "0 Team Kills"} 
              empty={!topTK || (topTK.team_kills || 0) === 0}
            />
          </div>
        </div>
      )}

      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-2 bg-zinc-900/50 p-1 w-fit rounded-lg border border-zinc-800 mx-auto">
          <button onClick={() => setActiveTab('total')} className={`px-5 py-2 text-sm font-semibold rounded-md transition-colors ${activeTab === 'total' ? 'bg-violet-500/20 text-violet-300 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'}`}>Total Score</button>
          <button onClick={() => setActiveTab('round1')} disabled={!axis_round1?.length} className={`px-5 py-2 text-sm font-semibold rounded-md transition-colors ${activeTab === 'round1' ? 'bg-violet-500/20 text-violet-300 shadow-sm' : 'text-zinc-500 hover:text-zinc-300 disabled:opacity-30 disabled:cursor-not-allowed'}`}>Round 1</button>
          <button onClick={() => setActiveTab('round2')} disabled={!axis_round2?.length} className={`px-5 py-2 text-sm font-semibold rounded-md transition-colors ${activeTab === 'round2' ? 'bg-violet-500/20 text-violet-300 shadow-sm' : 'text-zinc-500 hover:text-zinc-300 disabled:opacity-30 disabled:cursor-not-allowed'}`}>Round 2</button>
        </div>

        <ScoreTable 
          title={`Alpha ${activeTab !== 'total' ? `(${sideLabel(alphaSide)})` : ''}`} 
          accent={activeTab === 'total' ? 'text-white' : sideColor(alphaSide)} 
          rows={alphaRows} sortKey={sortKey} sortDir={sortDir} onSort={handleSort} 
        />
        <ScoreTable 
          title={`Beta ${activeTab !== 'total' ? `(${sideLabel(betaSide)})` : ''}`} 
          accent={activeTab === 'total' ? 'text-white' : sideColor(betaSide)} 
          rows={betaRows} sortKey={sortKey} sortDir={sortDir} onSort={handleSort} 
        />
      </div>
    </div>
  )
}
