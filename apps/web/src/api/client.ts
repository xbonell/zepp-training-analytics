export const zoneIds = ['below', 'z1', 'z2', 'z3', 'z4', 'z5'] as const

export type ZoneId = (typeof zoneIds)[number]
export type ZoneTotals = Record<ZoneId, number>

export interface ActivitySummary {
  activity_id: string
  sport_type: number
  started_at: string
  duration_s: number
  distance_m?: number | null
  avg_hr?: number | null
  max_hr?: number | null
  time_in_zone: ZoneTotals
  splat_minutes_estimate: number
}

export interface OverviewResponse {
  activity_count: number
  duration_s: number
  zone_mix: ZoneTotals
  splat_minutes_estimate: number
  recent: ActivitySummary[]
}

export interface ActivityFilters {
  from?: string
  to?: string
  sportType?: number
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal })
  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export function fetchOverview(signal?: AbortSignal): Promise<OverviewResponse> {
  return getJson('/api/overview', signal)
}

export function fetchActivities(
  filters: ActivityFilters = {},
  signal?: AbortSignal,
): Promise<ActivitySummary[]> {
  const params = new URLSearchParams()
  if (filters.from) params.set('from', filters.from)
  if (filters.to) params.set('to', filters.to)
  if (filters.sportType !== undefined) {
    params.set('sport_type', String(filters.sportType))
  }
  const query = params.toString()
  return getJson(`/api/activities${query ? `?${query}` : ''}`, signal)
}
