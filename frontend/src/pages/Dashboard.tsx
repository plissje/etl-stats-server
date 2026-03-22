import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchMatches, type MatchSummary } from '../api'

export function Dashboard() {
  const [rows, setRows] = useState<MatchSummary[]>([])
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    fetchMatches()
      .then(setRows)
      .catch((e) => setErr(String(e)))
  }, [])

  if (err) {
    return (
      <div className="p-8 text-center text-red-400">
        {err}
        <p className="mt-2 text-sm text-zinc-500">Is the API running on port 8000?</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight text-zinc-100">Recent matches</h1>
      <p className="mb-8 text-sm text-zinc-500">ET:Legacy gather stats</p>
      {!rows.length ? (
        <p className="text-zinc-500">No matches yet. POST a payload to <code className="text-zinc-400">/api/submit-stats</code>.</p>
      ) : (
        <ul className="divide-y divide-zinc-800 rounded-lg border border-zinc-800 bg-zinc-900/40">
          {rows.map((m) => (
            <li key={m.id}>
              <Link
                to={`/match/${m.id}`}
                className="flex flex-wrap items-baseline justify-between gap-2 px-4 py-3 transition hover:bg-zinc-800/50"
              >
                <span className="font-medium text-zinc-200">{m.mapname || '(unknown map)'}</span>
                <span className="text-sm text-zinc-500">
                  winner team {m.winner_team} · id {m.match_id}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
