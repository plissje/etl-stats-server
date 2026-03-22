import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchMatch, type MatchDetail, type PlayerRow } from '../api'

function ScoreTable({ title, accent, rows }: { title: string; accent: string; rows: PlayerRow[] }) {
  return (
    <div className="min-w-0 flex-1">
      <h2 className={`mb-3 text-lg font-semibold ${accent}`}>{title}</h2>
      <div className="overflow-x-auto rounded-lg border border-zinc-800">
        <table className="w-full min-w-[720px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900/80 text-xs uppercase tracking-wide text-zinc-500">
              <th className="px-2 py-2">Name</th>
              <th className="px-2 py-2 text-right">EFF</th>
              <th className="px-2 py-2 text-right">KDR</th>
              <th className="px-2 py-2 text-right">K</th>
              <th className="px-2 py-2 text-right">D</th>
              <th className="px-2 py-2 text-right">DG</th>
              <th className="px-2 py-2 text-right">DR</th>
              <th className="px-2 py-2 text-right">HS</th>
              <th className="px-2 py-2 text-right">Gib</th>
              <th className="px-2 py-2 text-right">REV</th>
              <th className="px-2 py-2 text-right">TMP</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.player_guid} className="border-b border-zinc-800/80 hover:bg-zinc-800/30">
                <td className="px-2 py-1.5">
                  <Link
                    to={`/player/${encodeURIComponent(r.player_guid)}`}
                    className="text-violet-400 hover:underline"
                    title={r.name_raw || undefined}
                  >
                    {r.name_display}
                  </Link>
                </td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.eff.toFixed(1)}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.kdr.toFixed(2)}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.kills}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.deaths}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.damage_given}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.damage_received}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.headshots}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.gibs}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.revives}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums">{r.team_medpacks}</td>
              </tr>
            ))}
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

  useEffect(() => {
    if (!id) return
    fetchMatch(Number(id))
      .then(setData)
      .catch(() => setErr('Match not found'))
  }, [id])

  if (err || !data) {
    return (
      <div className="p-8 text-center">
        <p className="text-red-400">{err || 'Loading…'}</p>
        <Link to="/" className="mt-4 inline-block text-violet-400">
          Back
        </Link>
      </div>
    )
  }

  const { match, axis, allies } = data

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Link to="/" className="text-sm text-violet-400 hover:underline">
        ← Matches
      </Link>
      <header className="mt-4 mb-8">
        <h1 className="text-2xl font-semibold text-zinc-100">{match.mapname}</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Match {match.match_id} · Winner team {match.winner_team} (1 = Axis / Alpha, 2 = Allies / Beta)
        </p>
      </header>
      <div className="flex flex-col gap-10 lg:flex-row">
        <ScoreTable title="Alpha — Axis (team 1)" accent="text-rose-400" rows={axis} />
        <ScoreTable title="Beta — Allies (team 2)" accent="text-sky-400" rows={allies} />
      </div>
    </div>
  )
}
