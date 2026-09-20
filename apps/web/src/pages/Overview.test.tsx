import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchOverview, fetchProfile } from '../api/client'
import { Overview } from './Overview'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, fetchOverview: vi.fn(), fetchProfile: vi.fn() }
})

const overview = {
  activity_count: 2,
  duration_s: 5400,
  zone_mix: { below: 0, z1: 600, z2: 1800, z3: 1800, z4: 900, z5: 300 },
  splat_minutes_estimate: 20,
  peak_hr_bpm: 181,
  recent: [
    {
      activity_id: 'run-1',
      sport_type: 1,
      sport_label: 'Outdoor Running',
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
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date(2026, 7, 26, 12))
    vi.mocked(fetchOverview).mockResolvedValue(overview)
    vi.mocked(fetchProfile).mockResolvedValue({
      sex: null,
      birth_date: null,
      resting_hr: null,
      hrmax_override: null,
      theme_preference: 'system',
      display_timezone: 'Europe/Madrid',
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows totals, zone mix, recent activity, and estimate labeling', async () => {
    render(<Overview />)

    expect(
      await screen.findByRole('heading', { name: 'Training overview' }),
    ).toBeVisible()
    expect(screen.getByText('2')).toBeVisible()
    expect(screen.getByText('1h 30m')).toBeVisible()
    expect(screen.getAllByText('Splat').length).toBeGreaterThan(0)
    expect(screen.getByText('Peak HR')).toBeVisible()
    expect(screen.getByText('181 bpm')).toBeVisible()
    expect(
      screen.getByRole('img', { name: /heart-rate zone mix/i }),
    ).toBeVisible()
    expect(screen.getByText('10.0 km')).toBeVisible()
    expect(screen.getAllByText('Z2').length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: '7 days' })).toBeNull()
  })

  it('loads unfiltered overview data', async () => {
    render(<Overview />)
    await screen.findByRole('heading', { name: 'Training overview' })

    expect(fetchOverview).toHaveBeenCalledWith({}, expect.any(AbortSignal))
  })

  it('shows a useful empty state', async () => {
    vi.mocked(fetchOverview).mockResolvedValue({
      ...overview,
      activity_count: 0,
      peak_hr_bpm: null,
      recent: [],
    })

    render(<Overview />)

    expect(await screen.findByText('No sessions synced')).toBeVisible()
    expect(screen.getByText('Peak HR')).toBeVisible()
    expect(screen.getByText('—')).toBeVisible()
  })
})
