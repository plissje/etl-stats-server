import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { 
  TrendingUp, 
  Gamepad2, 
  Skull, 
  Target, 
  Crosshair, 
  Award, 
  History,
  Info,
  ChevronLeft,
  Users,
  Zap,
  Shield,
  Heart,
  UserX,
  Activity,
  Flame
} from 'lucide-react'
import { fetchPlayer, type PlayerProfile as Profile } from '../api'
import { QuakeName } from '../components/QuakeName'

export function PlayerProfile() {
  const navigate = useNavigate()
  const { guid } = useParams<{ guid: string }>()
  const [p, setP] = useState<Profile | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const LIMIT = 20

  useEffect(() => {
    if (!guid) return
    setErr(null)
    setHasMore(true)
    fetchPlayer(guid, 0, LIMIT)
      .then(data => {
        setP(data)
        if ((data.match_history?.length || 0) < LIMIT) {
          setHasMore(false)
        }
      })
      .catch(() => setErr('Player not found'))
  }, [guid])

  const loadMore = async () => {
    if (!guid || !p || loadingMore || !hasMore) return
    setLoadingMore(true)
    try {
      const skip = p.match_history?.length || 0
      const nextData = await fetchPlayer(guid, skip, LIMIT)
      if (nextData.match_history && nextData.match_history.length > 0) {
        setP(prev => {
          if (!prev) return nextData
          return {
            ...prev,
            match_history: [...(prev.match_history || []), ...(nextData.match_history || [])]
          }
        })
        if (nextData.match_history.length < LIMIT) {
          setHasMore(false)
        }
      } else {
        setHasMore(false)
      }
    } catch (e) {
      console.error('Failed to load more matches', e)
    } finally {
      setLoadingMore(false)
    }
  }

  const chartData = useMemo(() => {
    if (!p?.rating_history?.length) return []
    return p.rating_history.map((h, i) => ({
      i: i + 1,
      rating: h.rating,
      t: h.recorded_at.slice(0, 10),
    }))
  }, [p])

  if (err || !p) {
    return (
      <div className="p-12 text-center bg-zinc-950 min-h-screen flex flex-col items-center justify-center">
        <p className="text-zinc-600 mb-4 font-mono">{err || 'Synchronizing data...'}</p>
        <Link to="/" className="px-6 py-2 bg-zinc-900 border border-zinc-800 rounded-full text-violet-400 hover:text-violet-300 transition flex items-center gap-2">
          <ChevronLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>
      </div>
    )
  }

  const otherNames = p.aliases?.filter(a => a !== p.display_name) || []

  return (
    <div className="mx-auto max-w-6xl px-6 py-10 space-y-10 animate-in fade-in duration-700">
      {/* Header Section */}
      <div className="relative group">
        <Link to="/" className="fixed top-8 left-8 p-3 bg-zinc-900/50 backdrop-blur border border-white/5 rounded-full text-zinc-400 hover:text-white transition-all hover:scale-110 z-50">
          <ChevronLeft className="w-6 h-6" />
        </Link>
        
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-4">
            <h1 className="text-6xl font-black tracking-tighter text-white">
              <QuakeName name={p.display_name} />
            </h1>
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <div className="flex items-center gap-2 font-mono text-zinc-500 bg-zinc-900/50 px-3 py-1 rounded-full border border-white/5">
                <Info className="w-3 h-3 text-violet-500" />
                {p.guid}
              </div>
              {otherNames.length > 0 && (
                <div className="text-zinc-500 text-xs font-medium bg-white/5 px-3 py-1 rounded-full flex items-center gap-2 border border-white/5">
                  <Users className="w-3 h-3 text-zinc-600" />
                  AKA: {otherNames.join(', ')}
                </div>
              )}
            </div>
          </div>
            <div className="px-8 py-5 bg-gradient-to-b from-zinc-900/80 to-zinc-950/80 border border-white/10 rounded-3xl text-center min-w-[140px] shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition">
                < Award className="w-12 h-12 text-amber-400" />
              </div>
              <div className="text-[10px] text-zinc-500 font-black uppercase tracking-[0.2em] mb-1">Most Valuable</div>
              <div className="text-4xl font-black text-amber-400 drop-shadow-[0_0_15px_rgba(251,191,36,0.3)]">{p.mvp_count || 0}</div>
            </div>
            <div className="px-8 py-5 bg-gradient-to-b from-zinc-900/80 to-zinc-950/80 border border-white/10 rounded-3xl text-center min-w-[140px] shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition">
                <TrendingUp className="w-12 h-12 text-violet-400" />
              </div>
              <div className="text-[10px] text-zinc-500 font-black uppercase tracking-[0.2em] mb-1">Skill Rating</div>
              <div className="text-4xl font-black text-violet-400 drop-shadow-[0_0_15px_rgba(167,139,250,0.3)]">{Math.round(p.current_rating)}</div>
            </div>
            <div className="px-8 py-5 bg-gradient-to-b from-zinc-900/80 to-zinc-950/80 border border-white/10 rounded-3xl text-center min-w-[140px] shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition">
                <Gamepad2 className="w-12 h-12 text-zinc-400" />
              </div>
              <div className="text-[10px] text-zinc-500 font-black uppercase tracking-[0.2em] mb-1">Gathers</div>
              <div className="text-4xl font-black text-zinc-100">{p.total_matches || 0}</div>
            </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Column */}
        <div className="lg:col-span-2 space-y-10">
          {/* Match History with Scroller */}
          <section className="bg-zinc-900/40 border border-white/5 rounded-3xl overflow-hidden backdrop-blur-sm">
            <div className="px-8 py-5 border-b border-white/5 flex justify-between items-center bg-zinc-800/10">
              <h3 className="font-black text-zinc-100 uppercase tracking-widest text-sm flex items-center gap-3">
                <History className="w-4 h-4 text-violet-500" />
                Career Match History
              </h3>
              <span className="text-[10px] font-bold text-zinc-500 bg-white/5 px-3 py-1 rounded-full border border-white/5">
                {p.match_history?.length || 0} RECORDED
              </span>
            </div>
            <div className="max-h-[440px] overflow-y-auto custom-scrollbar">
              <table className="w-full text-left">
                <thead className="text-[10px] font-black text-zinc-500 uppercase tracking-widest bg-zinc-950/50 sticky top-0 z-10">
                  <tr>
                    <th className="px-8 py-4">Map</th>
                    <th className="px-8 py-4">Status</th>
                    <th className="px-8 py-4">Team</th>
                    <th className="px-8 py-4 text-right">K/D/XP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {p.match_history?.map(m => {
                    const won = m.team === m.winner_team;
                    return (
                      <tr 
                        key={m.id} 
                        onClick={() => navigate(`/match/${m.id}`)}
                        className="hover:bg-white/[0.03] transition-colors group/row cursor-pointer"
                      >
                        <td className="px-8 py-5 font-bold text-zinc-300 flex items-center gap-3">
                          <span className="w-1.5 h-1.5 rounded-full bg-zinc-800 group-hover/row:bg-violet-500 transition" />
                          {m.mapname}
                        </td>
                        <td className="px-8 py-5">
                          <span className={`px-2 py-0.5 rounded-[4px] text-[10px] font-black uppercase tracking-tighter ${won ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                            {won ? 'Victory' : 'Defeat'}
                          </span>
                        </td>
                        <td className="px-8 py-5 text-[10px] font-black tracking-widest">
                          <span className={m.team === 1 ? 'text-rose-400/80' : 'text-sky-400/80'}>
                            {m.team === 1 ? 'ALPHA' : 'BETA'}
                          </span>
                        </td>
                        <td className="px-8 py-5 text-right">
                          <div className="flex flex-col items-end">
                             <div className="flex items-center gap-1.5">
                                <span className="text-zinc-100 font-mono text-sm font-black">{m.kills}</span>
                                <span className="text-zinc-700 font-mono text-xs">/</span>
                                <span className="text-zinc-500 font-mono text-xs">{m.deaths}</span>
                             </div>
                             <div className="text-[10px] font-bold text-zinc-600 font-mono italic">{m.xp} XP</div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {hasMore && (
              <div className="p-6 border-t border-white/5 bg-zinc-950/20 flex justify-center">
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="px-8 py-2.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed text-zinc-300 text-xs font-black uppercase tracking-widest rounded-xl border border-white/5 transition-all hover:scale-105 active:scale-95 flex items-center gap-3 shadow-xl"
                >
                  {loadingMore ? (
                    <>
                      <div className="w-3 h-3 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                      Loading...
                    </>
                  ) : (
                    <>
                      <History className="w-3 h-3 text-violet-400" />
                      Load Older Matches
                    </>
                  )}
                </button>
              </div>
            )}
          </section>
          
          {/* Lifetime Stats Grid */}
          {p.lifetime_stats && (
            <section className="space-y-6">
              <h3 className="font-black text-white px-2 flex items-center gap-3 uppercase tracking-widest text-sm">
                 <Activity className="w-4 h-4 text-violet-500" />
                 Career Lifetime Stats
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {[
                  { label: 'Kills', val: p.lifetime_stats.kills, icon: Crosshair, color: 'text-zinc-100' },
                  { label: 'Deaths', val: p.lifetime_stats.deaths, icon: Skull, color: 'text-rose-400' },
                  { label: 'Dmg Given', val: p.lifetime_stats.damage_given.toLocaleString(), icon: Zap, color: 'text-amber-400' },
                  { label: 'Dmg Recv', val: p.lifetime_stats.damage_received.toLocaleString(), icon: Shield, color: 'text-blue-400' },
                  { label: 'Headshots', val: p.lifetime_stats.headshots, icon: Target, color: 'text-emerald-400' },
                  { label: 'Gibs', val: p.lifetime_stats.gibs, icon: Flame, color: 'text-orange-500' },
                  { label: 'Self Kills', val: p.lifetime_stats.self_kills, icon: UserX, color: 'text-zinc-500' },
                  { label: 'Team Kills', val: p.lifetime_stats.team_kills, icon: Users, color: 'text-rose-600' },
                  { label: 'Revives', val: p.lifetime_stats.revives, icon: Heart, color: 'text-red-500' },
                  { label: 'Avg Eff', val: `${p.lifetime_stats.avg_eff}%`, icon: Activity, color: 'text-violet-400' },
                ].map((s, i) => (
                  <div key={i} className="p-4 bg-zinc-900/60 border border-white/5 rounded-2xl flex flex-col items-center text-center group hover:border-white/10 transition shadow-lg shrink-0">
                    <s.icon className={`w-5 h-5 mb-2 ${s.color} opacity-60 group-hover:opacity-100 transition`} />
                    <div className="text-[9px] text-zinc-600 font-black uppercase tracking-widest mb-1">{s.label}</div>
                    <div className={`text-lg font-black ${s.color}`}>{s.val}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Weapons Grid */}
          <section className="space-y-6">
            <h3 className="font-black text-white px-2 flex items-center gap-3 uppercase tracking-widest text-sm">
               <Crosshair className="w-4 h-4 text-violet-500" />
               Weapon Combat Efficiency
            </h3>
            <div className="bg-zinc-900/40 border border-white/5 rounded-[2.5rem] overflow-hidden backdrop-blur-sm">
              <table className="w-full text-left border-collapse">
                <thead className="bg-zinc-950/50 text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em]">
                  <tr>
                    <th className="px-8 py-5">Weapon Class</th>
                    <th className="px-8 py-5">Kills</th>
                    <th className="px-8 py-5 text-right">Combat Accuracy</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {p.top_weapons.map((w: any) => {
                    const acc = w.accuracy ?? w.accuracy_pct ?? 0;
                    return (
                      <tr key={w.name} className="group/w hover:bg-white/[0.02] transition-colors">
                        <td className="px-8 py-5">
                          <div className="flex items-center gap-3">
                            <div className="w-1.5 h-1.5 rounded-full bg-violet-500/40 group-hover/w:bg-violet-400 transition-colors" />
                            <span className="text-sm font-bold text-zinc-100 uppercase tracking-wider">{w.name}</span>
                          </div>
                        </td>
                        <td className="px-8 py-5">
                          <span className="text-lg font-black text-white">{w.kills}</span>
                        </td>
                        <td className="px-8 py-5">
                          <div className="flex flex-col items-end gap-2">
                            <span className="text-sm font-black text-violet-400">{acc}%</span>
                            <div className="w-32 h-1.5 bg-zinc-800/50 rounded-full overflow-hidden border border-white/5">
                              <div 
                                className="h-full bg-gradient-to-r from-violet-600 to-violet-400 rounded-full transition-all duration-1000 shadow-[0_0_8px_rgba(139,92,246,0.3)]" 
                                style={{ width: `${acc}%` }} 
                              />
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        {/* Sidebar */}
        <div className="space-y-8">
          {/* Class Specialization */}
          {p.class_stats && (
            <section className="p-8 bg-zinc-900/40 border border-white/5 rounded-[2.5rem] backdrop-blur-sm relative overflow-hidden group">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-violet-500/20 to-transparent" />
              <h3 className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.3em] mb-8 flex items-center gap-2">
                 <Zap className="w-3 h-3 text-violet-500" />
                 Class Specialization
              </h3>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { id: 'medic', name: 'Medic', icon: '💉' },
                  { id: 'engineer', name: 'Eng', icon: '🔧' },
                  { id: 'fieldop', name: 'Field', icon: '🎒' },
                  { id: 'soldier', name: 'Soldier', icon: '🪖' },
                  { id: 'covertops', name: 'Covert', icon: '🕶️' }
                ]
                .sort((a, b) => (p.class_stats?.[b.id] || 0) - (p.class_stats?.[a.id] || 0))
                .map((c, idx) => {
                  const count = p.class_stats?.[c.id] || 0;
                  const isActive = count > 0;
                  const isFeatured = idx === 0 && isActive;
                  return (
                    <div 
                      key={c.id} 
                      className={`flex flex-col gap-1 p-3 rounded-2xl border transition-all duration-500 shadow-sm
                        ${isFeatured ? 'col-span-2 bg-violet-600/10 border-violet-500/30 scale-[1.02] -translate-y-1' : 'col-span-1'}
                        ${isActive ? 'bg-zinc-800/20 border-white/5 group/class' : 'bg-transparent border-transparent opacity-30 grayscale'}
                      `}
                    >
                      <div className="flex items-center gap-2">
                        <span className={`${isFeatured ? 'text-2xl' : 'text-lg'} transform transition-transform group-hover/class:scale-110`}>
                          {c.icon}
                        </span>
                        <span className={`${isFeatured ? 'text-[11px]' : 'text-[10px]'} font-black text-zinc-500 uppercase tracking-widest`}>
                          {c.name}
                        </span>
                        {isFeatured && (
                          <span className="ml-auto text-[9px] font-black text-violet-400 uppercase tracking-wider bg-violet-500/10 px-2 py-0.5 rounded-full border border-violet-500/20">
                            Primary Role
                          </span>
                        )}
                      </div>
                      <div className="flex items-baseline gap-1">
                        <span className={`${isFeatured ? 'text-2xl' : 'text-base'} font-black text-zinc-100`}>{count}</span>
                        <span className={`${isFeatured ? 'text-[9px]' : 'text-[8px]'} font-bold text-zinc-600 uppercase tracking-tighter`}>
                          Picks
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Rating Chart */}
          <section className="p-8 bg-zinc-900/40 border border-white/5 rounded-[2.5rem] backdrop-blur-sm relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-violet-500/20 to-transparent" />
            <h3 className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.3em] mb-8 flex items-center gap-2">
               <TrendingUp className="w-3 h-3 text-violet-500" />
               Performance Alpha
            </h3>
            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <XAxis dataKey="i" hide />
                  <YAxis hide domain={['auto', 'auto']} />
                  <Tooltip
                    contentStyle={{ background: '#09090b', border: '1px solid #27272a', borderRadius: '16px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)' }}
                    itemStyle={{ color: '#a78bfa', fontWeight: '900', fontSize: '12px' }}
                    labelStyle={{ display: 'none' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="rating" 
                    stroke="#a78bfa" 
                    strokeWidth={4} 
                    dot={false}
                    activeDot={{ fill: '#fff', stroke: '#a78bfa', strokeWidth: 2, r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* Rivals */}
          {p.nemesis && (
            <div className="space-y-6">
              <div className="p-6 bg-gradient-to-br from-emerald-500/10 to-transparent border border-emerald-500/10 rounded-[2.5rem] shadow-xl relative overflow-hidden group">
                <div className="absolute -right-4 -top-4 opacity-5 group-hover:opacity-10 transition">
                   <Target className="w-24 h-24 text-emerald-400" />
                </div>
                <h3 className="text-[10px] font-black text-emerald-500 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                   <Award className="w-3 h-3" />
                   Priority Targets
                </h3>
                <ul className="space-y-4">
                  {p.nemesis.killed_most.map(n => (
                    <li key={n.guid} className="flex justify-between items-center group/item hover:translate-x-1 transition-transform">
                      <Link to={`/player/${n.guid}`} className="text-zinc-300 text-sm font-bold group-hover/item:text-white transition line-clamp-1 flex-1">
                        <QuakeName name={n.name} />
                      </Link>
                      <span className="text-[10px] font-black text-emerald-400 bg-emerald-400/10 px-3 py-1 rounded-full border border-emerald-500/20 whitespace-nowrap ml-4 min-w-[32px] text-center">{n.count}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="p-6 bg-gradient-to-br from-rose-500/10 to-transparent border border-rose-500/10 rounded-[2.5rem] shadow-xl relative overflow-hidden group">
                 <div className="absolute -right-4 -top-4 opacity-5 group-hover:opacity-10 transition">
                   <Skull className="w-24 h-24 text-rose-400" />
                </div>
                <h3 className="text-[10px] font-black text-rose-500 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                   <Skull className="w-3 h-3" />
                   Nemesis Watch
                </h3>
                <ul className="space-y-4">
                  {p.nemesis.killed_by_most.map(n => (
                    <li key={n.guid} className="flex justify-between items-center group/item hover:translate-x-1 transition-transform">
                      <Link to={`/player/${n.guid}`} className="text-zinc-300 text-sm font-bold group-hover/item:text-white transition line-clamp-1 flex-1">
                        <QuakeName name={n.name} />
                      </Link>
                      <span className="text-[10px] font-black text-rose-400 bg-rose-400/10 px-3 py-1 rounded-full border border-rose-500/20 whitespace-nowrap ml-4 min-w-[32px] text-center">{n.count}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #27272a; border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #3f3f46; }
      `}</style>
    </div>
  )
}
