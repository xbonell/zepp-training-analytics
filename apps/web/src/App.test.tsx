import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { ThemeProvider } from './theme/ThemeProvider'

vi.mock('./api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api/client')>()
  return {
    ...actual,
    fetchOverview: vi.fn().mockResolvedValue({
      activity_count: 0,
      duration_s: 0,
      zone_mix: { below: 0, z1: 0, z2: 0, z3: 0, z4: 0, z5: 0 },
      splat_minutes_estimate: 0,
      recent: [],
    }),
    fetchActivities: vi.fn().mockResolvedValue([]),
  }
})

describe('application shell', () => {
  beforeEach(() => {
    window.location.hash = '#overview'
  })

  it('presents the product identity and primary dashboard navigation', () => {
    render(
      <ThemeProvider>
        <App />
      </ThemeProvider>,
    )

    expect(
      screen.getByRole('link', { name: /zepp training/i }),
    ).toBeVisible()
    expect(screen.getByRole('navigation', { name: /primary/i })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Overview' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Activities' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Zones' })).toBeVisible()
  })

  it('renders the page selected by the hash route', async () => {
    window.location.hash = '#activities'

    render(
      <ThemeProvider>
        <App />
      </ThemeProvider>,
    )

    expect(
      await screen.findByRole('heading', { name: 'Activities' }),
    ).toBeVisible()
    expect(
      screen.getByRole('link', { name: 'Activities' }),
    ).toHaveAttribute('aria-current', 'page')
  })
})
