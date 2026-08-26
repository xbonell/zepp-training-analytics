import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { HrZoneChart } from './HrZoneChart'

const series = [
  { elapsed_s: 0, hr_bpm: 100, zone: 'z2' as const },
  { elapsed_s: 60, hr_bpm: 140, zone: 'z4' as const },
  { elapsed_s: 120, hr_bpm: 150, zone: 'z5' as const },
]

describe('HR zone chart', () => {
  it('renders the HR series over CSS-colored zone bands', () => {
    render(<HrZoneChart series={series} />)

    const chart = screen.getByRole('img', {
      name: 'Heart rate from 100 to 150 beats per minute over 2 minutes',
    })
    expect(chart.querySelector('polyline')).toHaveAttribute(
      'points',
      expect.stringMatching(/\d+,\d+/),
    )
    expect(chart.querySelectorAll('[data-zone]')).toHaveLength(6)
    expect(chart.querySelector('[data-zone="z4"]')).toHaveClass('zone-z4')
  })

  it('shows an empty state when there are no samples', () => {
    render(<HrZoneChart series={[]} />)

    expect(screen.getByText('No heart-rate samples recorded.')).toBeVisible()
  })
})
