export const zoneIds = ['below', 'z1', 'z2', 'z3', 'z4', 'z5'] as const

export type ZoneId = (typeof zoneIds)[number]
export type ZoneTotals = Record<ZoneId, number>
export type ZoneBoundaries = Partial<Record<ZoneId, readonly [number, number]>>

export interface ZonesResponse {
  hrmax: number | null
  source: 'override' | 'suggested' | 'none'
  boundaries: ZoneBoundaries
  colors: Record<ZoneId, string>
  age_formula_refs: {
    age: number
    fox_220_minus_age: number
    tanaka_208_minus_0_7_age: number
  } | null
}

export interface Profile {
  sex: string | null
  birth_date: string | null
  resting_hr: number | null
  hrmax_override: number | null
  theme_preference: 'light' | 'dark' | 'system'
  display_timezone: string
}

export interface ActivitySummary {
  activity_id: string
  sport_type: number
  sport_label: string
  started_at: string
  duration_s: number
  distance_m?: number | null
  avg_hr?: number | null
  max_hr?: number | null
  time_in_zone: ZoneTotals
  splat_minutes_estimate: number
}

export interface HeartRatePoint {
  elapsed_s: number
  hr_bpm: number
  zone: ZoneId | null
}

export interface ActivityDetail extends ActivitySummary {
  hr_series: HeartRatePoint[]
}

export interface OverviewResponse {
  activity_count: number
  duration_s: number
  zone_mix: ZoneTotals
  splat_minutes_estimate: number
  peak_hr_bpm: number | null
  recent: ActivitySummary[]
}

export interface ActivityFilters {
  from?: string
  to?: string
  sportType?: number
}

export type OverviewFilters = Pick<ActivityFilters, 'from' | 'to'>

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal })
  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

function dateParams(filters: OverviewFilters) {
  const params = new URLSearchParams()
  if (filters.from) params.set('from', filters.from)
  if (filters.to) params.set('to', filters.to)
  return params
}

export interface SportTypeOption {
  sport_type: number
  label: string
}

export function fetchOverview(
  filters: OverviewFilters = {},
  signal?: AbortSignal,
): Promise<OverviewResponse> {
  const query = dateParams(filters).toString()
  return getJson(`/api/overview${query ? `?${query}` : ''}`, signal)
}

export function fetchActivities(
  filters: ActivityFilters = {},
  signal?: AbortSignal,
): Promise<ActivitySummary[]> {
  const params = dateParams(filters)
  if (filters.sportType !== undefined) {
    params.set('sport_type', String(filters.sportType))
  }
  const query = params.toString()
  return getJson(`/api/activities${query ? `?${query}` : ''}`, signal)
}

export function fetchActivityDetail(
  activityId: string,
  signal?: AbortSignal,
): Promise<ActivityDetail> {
  return getJson(`/api/activities/${encodeURIComponent(activityId)}`, signal)
}

export function fetchSports(signal?: AbortSignal): Promise<SportTypeOption[]> {
  return getJson('/api/sports', signal)
}

export function fetchZones(signal?: AbortSignal): Promise<ZonesResponse> {
  return getJson('/api/zones', signal)
}

export function fetchProfile(signal?: AbortSignal): Promise<Profile> {
  return getJson('/api/settings/profile', signal)
}

export async function updateProfile(profile: Profile): Promise<Profile> {
  const response = await fetch('/api/settings/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  })
  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`)
  }
  return response.json() as Promise<Profile>
}

export interface ConnectionView {
  user_id: string | null
  token_set: boolean
  token_hint: string | null
}

export interface SyncJobView {
  status: 'idle' | 'running' | 'ok' | 'error'
  started_at: string | null
  finished_at: string | null
  error: string | null
  message: string | null
}

export function fetchConnection(signal?: AbortSignal) {
  return getJson<ConnectionView>('/api/settings/connection', signal)
}

export async function updateConnection(body: {
  user_id: string | null
  app_token?: string | null
}): Promise<ConnectionView> {
  const response = await fetch('/api/settings/connection', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new Error(`API request failed (${response.status})`)
  return response.json()
}

export function fetchSyncJob(signal?: AbortSignal) {
  return getJson<SyncJobView>('/api/settings/sync', signal)
}

export async function startSyncJob(): Promise<SyncJobView> {
  const response = await fetch('/api/settings/sync', { method: 'POST' })
  if (response.status === 409) throw new Error('Sync already running')
  if (!response.ok) throw new Error(`API request failed (${response.status})`)
  return response.json()
}
