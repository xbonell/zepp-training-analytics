import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchOverview } from '../api/client'
import { Overview } from './Overview'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, fetchOverview: vi.fn() }
})

const overview = {
  activity_count: 2,
  duration_s: 5400,
  zone_mix: { below: 0, z1: 600, z2: 1800, z3: 1800, z4: 900, z5: 300 },
  splat_minutes_estimate: 20,
  recent: [
    {
      activity_id: 'run-1',
      sport_type: 1,
      started_at: '2026-08-24T07:30:00Z',
      duration_s: 3600,
      distance_m: 10000,
      avg_hr: 151,
      max_hr: 181,
      time_in_zone: {
        below: 0,
        z1: 300,
        z2: 1200,
        z3: 1200,
        z4: 700,
        z5: 200,
      },
      splat_minutes_estimate: 15,
    },
  ],
}

describe('Overview page', () => {
  beforeEach(() => {
    vi.mocked(fetchOverview).mockResolvedValue(overview)
  })

  it('shows totals, zone mix, recent activity, and estimate labeling', async () => {
    render(<Overview />)

    expect(
      await screen.findByRole('heading', { name: 'Training overview' }),
    ).toBeVisible()
    expect(screen.getByText('2')).toBeVisible()
    expect(screen.getByText('1h 30m')).toBeVisible()
    expect(screen.getByText('Local splat estimate')).toBeVisible()
    expect(
      screen.getByRole('img', { name: /heart-rate zone mix/i }),
    ).toBeVisible()
    expect(screen.getByText('10.0 km')).toBeVisible()
  })

  it('shows a useful empty state', async () => {
    vi.mocked(fetchOverview).mockResolvedValue({
      ...overview,
      activity_count: 0,
      recent: [],
    })

    render(<Overview />)

    expect(await screen.findByText('No sessions synced')).toBeVisible()
  })
})
