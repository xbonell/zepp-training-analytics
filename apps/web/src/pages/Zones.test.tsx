import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  fetchProfile,
  fetchZones,
  updateProfile,
  type Profile,
  type ZonesResponse,
} from '../api/client'
import { Zones } from './Zones'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    fetchProfile: vi.fn(),
    fetchZones: vi.fn(),
    updateProfile: vi.fn(),
  }
})

const profile: Profile = {
  sex: 'female',
  birth_date: '1990-05-17',
  resting_hr: 52,
  hrmax_override: null,
  theme_preference: 'dark',
  display_timezone: 'Europe/Madrid',
}

const zones: ZonesResponse = {
  hrmax: 190,
  source: 'suggested',
  boundaries: {
    below: [0, 95],
    z1: [95, 116],
    z2: [116, 135],
    z3: [135, 160],
    z4: [160, 175],
    z5: [175, 190],
  },
  colors: {
    below: 'gray',
    z1: 'gray',
    z2: 'blue',
    z3: 'green',
    z4: 'orange',
    z5: 'red',
  },
  age_formula_refs: {
    age: 36,
    fox_220_minus_age: 184,
    tanaka_208_minus_0_7_age: 182.8,
  },
}

describe('Zones settings page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchProfile).mockResolvedValue(profile)
    vi.mocked(fetchZones).mockResolvedValue(zones)
    vi.mocked(updateProfile).mockResolvedValue(profile)
  })

  it('shows OTF ranges, active HRmax, age references, colors, and BPM preview', async () => {
    render(<Zones />)

    expect(
      await screen.findByRole('heading', { name: 'Heart-rate zones' }),
    ).toBeVisible()
    expect(screen.getByText('Suggested HRmax')).toBeVisible()
    expect(screen.getByText('190 bpm')).toBeVisible()
    expect(screen.getByText(/Fox · 220 − age/i)).toBeVisible()
    expect(screen.getByText(/184 bpm/)).toBeVisible()
    expect(screen.getByText(/Tanaka · 208 − 0.7 × age/i)).toBeVisible()

    const z4Row = screen.getByRole('row', { name: /Z4/ })
    expect(z4Row).toHaveTextContent('84–91%')
    expect(z4Row).toHaveTextContent('160–174 bpm')
    expect(z4Row.querySelector('[data-color="orange"]')).toBeInTheDocument()
  })

  it('saves editable profile fields while preserving profile preferences', async () => {
    const user = userEvent.setup()
    render(<Zones />)
    await screen.findByRole('heading', { name: 'Heart-rate zones' })

    await user.clear(screen.getByLabelText('HRmax override'))
    await user.type(screen.getByLabelText('HRmax override'), '188')
    await user.clear(screen.getByLabelText('Resting heart rate'))
    await user.type(screen.getByLabelText('Resting heart rate'), '54')
    await user.selectOptions(screen.getByLabelText('Sex'), 'male')
    await user.click(screen.getByRole('button', { name: 'Save profile' }))

    await waitFor(() => {
      expect(updateProfile).toHaveBeenCalledWith({
        ...profile,
        sex: 'male',
        resting_hr: 54,
        hrmax_override: 188,
      })
    })
    expect(await screen.findByText('Profile saved.')).toBeVisible()
    expect(fetchZones).toHaveBeenCalledTimes(2)
  })

  it('supports clearing an existing HRmax override', async () => {
    vi.mocked(fetchProfile).mockResolvedValue({
      ...profile,
      hrmax_override: 188,
    })
    const user = userEvent.setup()
    render(<Zones />)
    await screen.findByRole('heading', { name: 'Heart-rate zones' })

    await user.clear(screen.getByLabelText('HRmax override'))
    await user.click(screen.getByRole('button', { name: 'Save profile' }))

    await waitFor(() => {
      expect(updateProfile).toHaveBeenCalledWith({
        ...profile,
        hrmax_override: null,
      })
    })
  })
})
