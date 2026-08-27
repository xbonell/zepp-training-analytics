import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from '../api/client'
import { Settings } from './Settings'

vi.mock('../api/client')

describe('Settings', () => {
  beforeEach(() => {
    vi.mocked(api.fetchConnection).mockResolvedValue({
      user_id: '1',
      token_set: true,
      token_hint: 'oken',
    })
    vi.mocked(api.fetchSyncJob).mockResolvedValue({
      status: 'ok',
      started_at: null,
      finished_at: null,
      error: null,
      message: null,
    })
    vi.mocked(api.fetchProfile).mockResolvedValue({
      sex: null,
      birth_date: null,
      resting_hr: null,
      hrmax_override: null,
      theme_preference: 'system',
      display_timezone: 'Europe/Madrid',
    })
  })

  it('shows masked token and disables sync while running', async () => {
    vi.mocked(api.fetchSyncJob).mockResolvedValue({
      status: 'running',
      started_at: null,
      finished_at: null,
      error: null,
      message: null,
    })
    render(<Settings />)
    expect(await screen.findByText(/oken/i)).toBeVisible()
    expect(
      await screen.findByRole('button', { name: /sync now/i }),
    ).toBeDisabled()
  })

  it('saves connection with pasted token', async () => {
    vi.mocked(api.updateConnection).mockResolvedValue({
      user_id: '2',
      token_set: true,
      token_hint: 'zzzz',
    })
    const user = userEvent.setup()
    render(<Settings />)
    await screen.findByLabelText(/user id/i)
    await user.clear(screen.getByLabelText(/user id/i))
    await user.type(screen.getByLabelText(/user id/i), '2')
    await user.type(screen.getByLabelText(/app token/i), 'new-token-zzzz')
    await user.click(screen.getByRole('button', { name: /save connection/i }))
    await waitFor(() =>
      expect(api.updateConnection).toHaveBeenCalledWith({
        user_id: '2',
        app_token: 'new-token-zzzz',
      }),
    )
  })
})
