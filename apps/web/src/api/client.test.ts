import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  fetchActivities,
  fetchActivityDetail,
  fetchOverview,
  fetchProfile,
  fetchZones,
  updateProfile,
} from './client'

describe('API client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('encodes selected overview dates', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ activity_count: 0 }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchOverview({ from: '2026-08-20', to: '2026-08-26' })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/overview?from=2026-08-20&to=2026-08-26',
      { signal: undefined },
    )
  })

  it('encodes only selected activity filters', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchActivities({ from: '2026-08-01', sportType: 1 })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/activities?from=2026-08-01&sport_type=1',
      { signal: undefined },
    )
  })

  it('encodes activity IDs in detail requests', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ activity_id: 'run/1' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchActivityDetail('run/1')

    expect(fetchMock).toHaveBeenCalledWith('/api/activities/run%2F1', {
      signal: undefined,
    })
  })

  it('fetches BPM zone boundaries', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ boundaries: { z4: [168, 184] } }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchZones()

    expect(fetchMock).toHaveBeenCalledWith('/api/zones', { signal: undefined })
  })

  it('fetches the training profile', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ theme_preference: 'system' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchProfile()

    expect(fetchMock).toHaveBeenCalledWith('/api/settings/profile', {
      signal: undefined,
    })
  })

  it('saves the complete training profile as JSON', async () => {
    const profile = {
      sex: 'female',
      birth_date: '1990-05-17',
      resting_hr: 52,
      hrmax_override: 188,
      theme_preference: 'dark' as const,
      display_timezone: 'Europe/Madrid',
    }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(profile),
    })
    vi.stubGlobal('fetch', fetchMock)

    await updateProfile(profile)

    expect(fetchMock).toHaveBeenCalledWith('/api/settings/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    })
  })

  it('surfaces API errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 503 }),
    )

    await expect(fetchOverview()).rejects.toThrow('API request failed (503)')
  })
})
