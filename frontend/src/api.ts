export type MatchSummary = {
  id: number
  match_id: string
  mapname: string
  winner_team: number
  round_start_unix: number
  round_end_unix: number
}

export type PlayerRow = {
  player_guid: string
  name_display: string
  name_raw: string | null
  team: number
  eff: number
  kdr: number
  kills: number
  deaths: number
  damage_given: number
  damage_received: number
  headshots: number
  gibs: number
  revives: number
  team_medpacks: number
}

export type MatchDetail = {
  match: MatchSummary
  axis: PlayerRow[]
  allies: PlayerRow[]
}

export async function fetchMatches(): Promise<MatchSummary[]> {
  const r = await fetch('/api/matches')
  if (!r.ok) throw new Error('failed to load matches')
  return r.json()
}

export async function fetchMatch(id: number): Promise<MatchDetail> {
  const r = await fetch(`/api/matches/${id}`)
  if (!r.ok) throw new Error('match not found')
  return r.json()
}

export type PlayerProfile = {
  guid: string
  display_name: string
  current_rating: number
  rating_history: { match_id: number; rating: number; delta: number; recorded_at: string }[]
  top_weapons: { name: string; hits: number; shots: number; kills: number; accuracy_pct: number | null }[]
}

export async function fetchPlayer(guid: string): Promise<PlayerProfile> {
  const r = await fetch(`/api/players/${encodeURIComponent(guid)}`)
  if (!r.ok) throw new Error('player not found')
  return r.json()
}
