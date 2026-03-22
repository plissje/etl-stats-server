import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fetchPlayer, type PlayerProfile as Profile } from '../api'

export function PlayerProfile() {
  const { guid } = useParams<{ guid: string }>()
  const [p, setP] = useState<Profile | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!guid) return
    fetchPlayer(guid)
      .then(setP)
      .catch(() => setErr('Player not found'))
  }, [guid])

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
      <div className="p-8 text-center">
        <p className="text-red-400">{err || 'Loading…'}</p>
        <Link to="/" className="mt-4 inline-block text-violet-400">
          Back
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <Link to="/" className="text-sm text-violet-400 hover:underline">
        ← Matches
      </Link>
      <h1 className="mt-4 text-2xl font-semibold text-zinc-100">{p.display_name}</h1>
      <p className="mt-1 font-mono text-sm text-zinc-500">{p.guid}</p>
      <p className="mt-4 text-lg text-zinc-300">
        Gather power rating: <span className="font-semibold text-violet-400">{p.current_rating.toFixed(1)}</span>
      </p>

      {chartData.length > 0 && (
        <div className="mt-8 h-64 w-full rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
          <h2 className="mb-2 text-sm font-medium text-zinc-400">Rating over time</h2>
          <ResponsiveContainer width="100%" height="90%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="i" stroke="#71717a" fontSize={12} />
              <YAxis stroke="#71717a" fontSize={12} domain={['auto', 'auto']} />
              <Tooltip
                contentStyle={{ background: '#18181b', border: '1px solid #3f3f46' }}
                labelStyle={{ color: '#a1a1aa' }}
              />
              <Line type="monotone" dataKey="rating" stroke="#a78bfa" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-10">
        <h2 className="mb-3 text-lg font-semibold text-zinc-200">Most accurate weapons (career)</h2>
        {!p.top_weapons.length ? (
          <p className="text-zinc-500">No weapon breakdown stored yet.</p>
        ) : (
          <ul className="divide-y divide-zinc-800 rounded-lg border border-zinc-800">
            {p.top_weapons.map((w) => (
              <li key={w.name} className="flex justify-between px-4 py-2 text-sm">
                <span className="text-zinc-300">{w.name}</span>
                <span className="font-mono text-zinc-500">
                  {w.accuracy_pct != null ? `${w.accuracy_pct}%` : '—'} acc · {w.kills} kills · {w.shots} shots
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
