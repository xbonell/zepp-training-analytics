import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fetchZones, type ZonesResponse } from '../api/client'
import { Zones } from './Zones'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    fetchZones: vi.fn(),
  }
})

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
    vi.mocked(fetchZones).mockResolvedValue(zones)
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
    expect(z4Row.querySelector('.zone-z4')).toBeInTheDocument()
    expect(z4Row.querySelector('i')).not.toHaveAttribute('style')
    expect(screen.queryByRole('button', { name: /save profile/i })).not.toBeInTheDocument()
  })
})
