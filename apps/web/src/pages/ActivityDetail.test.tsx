import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchActivityDetail, fetchProfile, fetchZones } from '../api/client'
import { ActivityDetail } from './ActivityDetail'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    fetchActivityDetail: vi.fn(),
    fetchProfile: vi.fn(),
    fetchZones: vi.fn(),
  }
})

const detail = {
  activity_id: 'run-1',
  sport_type: 1,
  sport_label: 'Outdoor Running',
  started_at: '2026-08-22T23:30:00Z',
  duration_s: 120,
  distance_m: 800,
  avg_hr: 130,
  max_hr: 150,
  time_in_zone: { below: 0, z1: 0, z2: 60, z3: 0, z4: 60, z5: 0 },
  splat_minutes_estimate: 1,
  hr_series: [
    { elapsed_s: 0, hr_bpm: 100, zone: 'z2' as const },
    { elapsed_s: 60, hr_bpm: 140, zone: 'z4' as const },
    { elapsed_s: 120, hr_bpm: 150, zone: 'z5' as const },
  ],
}

const zones = {
  hrmax: 200,
  source: 'override' as const,
  boundaries: {
    below: [0, 100] as [number, number],
    z1: [100, 122] as [number, number],
    z2: [122, 142] as [number, number],
    z3: [142, 168] as [number, number],
    z4: [168, 184] as [number, number],
    z5: [184, 200] as [number, number],
  },
  colors: {
    below: 'gray',
    z1: 'gray',
    z2: 'blue',
    z3: 'green',
    z4: 'orange',
    z5: 'red',
  },
  age_formula_refs: null,
}

describe('Activity detail page', () => {
  beforeEach(() => {
    vi.mocked(fetchActivityDetail).mockResolvedValue(detail)
    vi.mocked(fetchZones).mockResolvedValue(zones)
    vi.mocked(fetchProfile).mockResolvedValue({
      sex: null,
      birth_date: null,
      resting_hr: null,
      hrmax_override: null,
      theme_preference: 'system',
      display_timezone: 'Europe/Madrid',
    })
  })

  it('loads the activity chart and local zone estimates', async () => {
    render(<ActivityDetail activityId="run-1" />)

    expect(
      await screen.findByRole('heading', { name: 'Activity detail' }),
    ).toBeVisible()
    expect(fetchActivityDetail).toHaveBeenCalledWith(
      'run-1',
      expect.any(AbortSignal),
    )
    expect(fetchZones).toHaveBeenCalledWith(expect.any(AbortSignal))
    expect(screen.getByText(/August 23, 2026/i)).toBeVisible()
    expect(screen.getByRole('img', { name: /heart rate from 100 to 150/i })).toBeVisible()
    expect(screen.getByText('1 min')).toBeVisible()
    expect(screen.getByText('local estimate')).toBeVisible()
    expect(screen.getAllByText('Z4')).toHaveLength(2)
    expect(screen.getAllByText('01:00')).toHaveLength(2)
  })

  it('shows API failures', async () => {
    vi.mocked(fetchActivityDetail).mockRejectedValueOnce(new Error('Not found'))

    render(<ActivityDetail activityId="missing" />)

    expect(await screen.findByText('Activity unavailable')).toBeVisible()
    expect(screen.getByText('Not found')).toBeVisible()
  })

  it('still displays activity detail when zones fail', async () => {
    vi.mocked(fetchZones).mockRejectedValueOnce(new Error('Zones unavailable'))

    render(<ActivityDetail activityId="run-1" />)

    expect(
      await screen.findByRole('heading', { name: 'Activity detail' }),
    ).toBeVisible()
    expect(screen.getByText('Zone boundaries unavailable.')).toBeVisible()
  })
})
