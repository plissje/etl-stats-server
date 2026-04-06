export type WeaponPerformance = {
  name: string;
  hits: number;
  shots: number;
  kills: number;
  deaths: number;
  headshots: number;
  accuracy: number | null;
}

export type ClassPlayed = {
  toClass: string;
  seconds: number;
}

export type MatchSummary = {
  id: number
  match_id: string
  mapname: string
  winner_team: number
  round_start_unix: number
  round_end_unix: number
  axis_players: string[]
  allies_players: string[]
  mvp_name?: string
  mvp_guid?: string
}

export type PlayerRow = {
  player_guid: string
  name_display: string
  name_raw: string | null
  team: number
  eff: number
  unified_eff: number
  kdr: number
  kills: number
  deaths: number
  xp: number
  damage_given: number
  damage_received: number
  headshots: number
  gibs: number
  revives: number
  medkits: number
  team_medpacks: number
  spam_kills: number

  distance_travelled_meters?: number
  distance_travelled_spawn_avg?: number
  crouched_seconds?: number
  proned_seconds?: number
  leaned_seconds?: number
  classes_played?: ClassPlayed[]

  time_played_pct: number
  team_kills: number
  team_damage_given: number
  team_gibs: number
  self_kills: number
  weapon_breakdown: WeaponPerformance[] | null
}

export type MatchRivalry = {
  killer_guid: string
  killer_name: string
  victim_guid: string
  victim_name: string
  count: number
}

export type MatchDetail = {
  match: MatchSummary
  axis: PlayerRow[]
  allies: PlayerRow[]
  axis_round1?: PlayerRow[] | null
  allies_round1?: PlayerRow[] | null
  axis_round2?: PlayerRow[] | null
  allies_round2?: PlayerRow[] | null
  round1_alpha_side?: number | null
  round2_alpha_side?: number | null
  rivalry: MatchRivalry | null
}

export async function fetchMatches(mapname?: string, skip: number = 0, limit: number = 20): Promise<MatchSummary[]> {
  const params = new URLSearchParams()
  params.set('skip', skip.toString())
  params.set('limit', limit.toString())
  if (mapname) params.set('mapname', mapname)
  
  const r = await fetch(`/api/matches?${params.toString()}`)
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
  raw_name?: string
  current_rating: number
  mvp_count?: number
  rating_history: { match_id: number; rating: number; delta: number; recorded_at: string }[]
  top_weapons: WeaponPerformance[]
  nemesis?: {
    killed_most: { guid: string; count: number; name: string }[]
    killed_by_most: { guid: string; count: number; name: string }[]
  }
  aliases?: string[]
  total_matches?: number
  match_history?: {
    id: number
    mapname: string
    team: number
    winner_team: number
    kills: number
    deaths: number
    xp: number
    timestamp: number
  }[]
  lifetime_stats?: {
    kills: number
    deaths: number
    damage_given: number
    damage_received: number
    headshots: number
    gibs: number
    self_kills: number
    team_kills: number
    revives: number
    avg_eff: number
  }
  class_stats?: Record<string, number>
}

export async function fetchPlayer(guid: string, skip: number = 0, limit: number = 20): Promise<PlayerProfile> {
  const r = await fetch(`/api/players/${encodeURIComponent(guid)}?skip=${skip}&limit=${limit}`)
  if (!r.ok) throw new Error('player not found')
  return r.json()
}

export type StatsOverview = {
  total_matches: number
  total_players: number
  total_performances: number
  top_maps: { mapname: string; count: number }[]
  top_players: { name: string; guid: string; rating: number }[]
  top_mvps: { name: string; guid: string; count: number }[]
  recent_matches: { id: number; match_id: string; mapname: string; created_at: string }[]
  total_kills: number
  total_damage: number
  total_time_played_s: number
  matches_by_day: { day: string; count: number }[]
}

export async function fetchStatsOverview(): Promise<StatsOverview> {
  const r = await fetch('/api/stats/overview')
  if (!r.ok) throw new Error('failed to load overview')
  return r.json()
}

export type LeaderboardEntry = { guid: string; display_name: string; raw_name?: string; val: number }
export type PlayerIdentifier = { guid: string; name: string; slot?: number }
export type Leaderboards = {
  openskill: LeaderboardEntry[]
  medic: LeaderboardEntry[]
  sharpshooter: LeaderboardEntry[]
}

export type BalancePlayer = { guid: string; name: string; rating: number; slot?: number; role: string }
export type BalanceResponse = {
  alpha: BalancePlayer[]
  beta: BalancePlayer[]
  alpha_avg_sr: number
  beta_avg_sr: number
  diff: number
}

export type LivePlayer = { slot: number; name: string; team: string; guid: string; rating: number; main_role: string }

export async function fetchLeaderboards(): Promise<Leaderboards> {
  const r = await fetch('/api/players/leaderboards')
  if (!r.ok) throw new Error('failed to load leaderboards')
  return r.json()
}

export async function searchPlayers(q: string = ''): Promise<LeaderboardEntry[]> {
  const r = await fetch(`/api/players?q=${encodeURIComponent(q)}`)
  if (!r.ok) throw new Error('failed to search players')
  return r.json()
}

export async function balanceTeams(players: PlayerIdentifier[]): Promise<BalanceResponse> {
  const response = await fetch('/api/balancer/balance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ players })
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to balance teams')
  }
  return response.json()
}

export async function fetchLivePlayers(): Promise<LivePlayer[]> {
  const r = await fetch('/api/server/players')
  if (!r.ok) throw new Error('failed to fetch live players')
  const data = await r.json()
  return data.players
}

export async function movePlayersToTeams(moves: { slot: number, team: string }[]): Promise<{ success: boolean, details: string }> {
  const response = await fetch('/api/server/move-players', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ moves })
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to move players')
  }
  return response.json()
}
