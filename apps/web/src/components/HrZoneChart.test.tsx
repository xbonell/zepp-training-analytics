import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { HrZoneChart } from './HrZoneChart'

const series = [
  { elapsed_s: 0, hr_bpm: 100, zone: 'z2' as const },
  { elapsed_s: 60, hr_bpm: 140, zone: 'z4' as const },
  { elapsed_s: 120, hr_bpm: 150, zone: 'z5' as const },
]

const boundaries = {
  below: [0, 100] as const,
  z1: [100, 120] as const,
  z2: [120, 140] as const,
  z3: [140, 160] as const,
  z4: [160, 180] as const,
  z5: [180, 200] as const,
}

describe('HR zone chart', () => {
  it('plots samples and zone boundaries on one linear BPM scale', () => {
    render(<HrZoneChart series={series} boundaries={boundaries} />)

    const chart = screen.getByRole('img', {
      name: 'Heart rate from 100 to 150 beats per minute over 2 minutes',
    })
    expect(chart.querySelector('polyline')).toHaveAttribute(
      'points',
      '54.0,146.0 467.0,95.6 880.0,83.0',
    )
    expect(chart.querySelectorAll('[data-zone]')).toHaveLength(6)
    const belowHeight = Number(
      chart.querySelector('[data-zone="below"]')?.getAttribute('height'),
    )
    const z4Height = Number(
      chart.querySelector('[data-zone="z4"]')?.getAttribute('height'),
    )
    expect(belowHeight).toBeCloseTo(126)
    expect(z4Height).toBeCloseTo(25.2)
  })

  it('shows an empty state when there are no samples', () => {
    render(<HrZoneChart series={[]} boundaries={boundaries} />)

    expect(screen.getByText('No heart-rate samples recorded.')).toBeVisible()
  })
})
