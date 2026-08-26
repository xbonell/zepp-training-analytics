import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ThemeProvider, ThemeToggle } from './ThemeProvider'

const mediaListeners = new Set<(event: MediaQueryListEvent) => void>()

function setSystemDark(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    value: vi.fn().mockImplementation(() => ({
      matches,
      media: '(prefers-color-scheme: dark)',
      onchange: null,
      addEventListener: (_type: string, listener: (event: MediaQueryListEvent) => void) =>
        mediaListeners.add(listener),
      removeEventListener: (_type: string, listener: (event: MediaQueryListEvent) => void) =>
        mediaListeners.delete(listener),
      dispatchEvent: vi.fn(),
    })),
  })
}

describe('theme controls', () => {
  beforeEach(() => {
    localStorage.clear()
    mediaListeners.clear()
    document.documentElement.removeAttribute('data-theme')
    setSystemDark(true)
  })

  it('uses the operating system theme by default', () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    )

    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
    expect(screen.getByRole('button', { name: /theme: system/i })).toBeVisible()
  })

  it('cycles and persists light, dark, and system preferences', async () => {
    const user = userEvent.setup()
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    )
    const toggle = screen.getByRole('button', { name: /theme: system/i })

    await user.click(toggle)
    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
    expect(localStorage.getItem('zepp-training-theme')).toBe('light')

    await user.click(toggle)
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
    expect(localStorage.getItem('zepp-training-theme')).toBe('dark')

    await user.click(toggle)
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
    expect(localStorage.getItem('zepp-training-theme')).toBe('system')
  })

  it('restores a saved preference without requiring an API', () => {
    localStorage.setItem('zepp-training-theme', 'light')

    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    )

    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
  })
})
