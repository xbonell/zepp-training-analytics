import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'
import { ThemeProvider } from './theme/ThemeProvider'

describe('application shell', () => {
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
})
