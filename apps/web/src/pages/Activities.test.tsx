import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchActivities, fetchProfile, fetchSports } from '../api/client'
import { Activities } from './Activities'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    fetchActivities: vi.fn(),
    fetchProfile: vi.fn(),
    fetchSports: vi.fn(),
  }
})

const activity = {
  activity_id: 'ride-1',
  sport_type: 9,
  sport_label: 'Outdoor Cycling',
  started_at: '2026-08-22T23:30:00Z',
  duration_s: 2700,
  distance_m: 18400,
  avg_hr: 142,
  max_hr: 176,
  time_in_zone: { below: 0, z1: 300, z2: 900, z3: 900, z4: 500, z5: 100 },
  splat_minutes_estimate: 10,
}

describe('Activities page', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date(2026, 7, 26, 12))
    vi.mocked(fetchActivities).mockResolvedValue([activity])
    vi.mocked(fetchSports).mockResolvedValue([
      { sport_type: 1, label: 'Outdoor Running' },
      { sport_type: 9, label: 'Outdoor Cycling' },
    ])
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

  it('loads and displays activity data', async () => {
    render(<Activities />)

    expect(
      await screen.findByRole('heading', { name: 'Activities' }),
    ).toBeVisible()
    expect(screen.getAllByText('Outdoor Cycling').length).toBeGreaterThan(0)
    expect(screen.getByText('18.4 km')).toBeVisible()
    expect(screen.getByText(/142 bpm/)).toBeVisible()
    expect(screen.getByText(/10 min/)).toBeVisible()
    expect(screen.getByText('local estimate')).toBeVisible()
    expect(screen.getByText('Z2')).toBeVisible()
    expect(screen.getByRole('link', { name: /aug 23, 2026/i })).toHaveAttribute(
      'href',
      '#activities/ride-1',
    )
  })

  it('requests activities for an applied period and sport', async () => {
    const user = userEvent.setup()
    render(<Activities />)
    await screen.findByText('18.4 km')
    await screen.findByRole('option', { name: 'Outdoor Cycling' })

    await user.type(screen.getByLabelText('From'), '2026-08-01')
    await user.type(screen.getByLabelText('To'), '2026-08-26')
    await user.selectOptions(
      screen.getByLabelText('Sport type'),
      'Outdoor Cycling',
    )
    await user.click(screen.getByRole('button', { name: 'Apply filters' }))

    await waitFor(() => {
      expect(fetchActivities).toHaveBeenLastCalledWith(
        { from: '2026-08-01', to: '2026-08-26', sportType: 9 },
        expect.any(AbortSignal),
      )
    })
  })

  it('shares period presets with the overview filters', async () => {
    const user = userEvent.setup()
    render(<Activities />)
    await screen.findByText('18.4 km')

    await user.click(screen.getByRole('button', { name: '30 days' }))

    await waitFor(() => {
      expect(fetchActivities).toHaveBeenLastCalledWith(
        { from: '2026-07-28', to: '2026-08-26' },
        expect.any(AbortSignal),
      )
    })
  })
})
