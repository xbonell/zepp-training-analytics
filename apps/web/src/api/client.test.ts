import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchActivities, fetchOverview } from './client'

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

  it('surfaces API errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 503 }),
    )

    await expect(fetchOverview()).rejects.toThrow('API request failed (503)')
  })
})
