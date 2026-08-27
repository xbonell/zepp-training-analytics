import { type FormEvent, useEffect, useState } from 'react'
import {
  fetchConnection,
  fetchProfile,
  fetchSyncJob,
  startSyncJob,
  updateConnection,
  type ConnectionView,
  type SyncJobView,
} from '../api/client'

export function Settings() {
  const [connection, setConnection] = useState<ConnectionView>()
  const [syncJob, setSyncJob] = useState<SyncJobView>()
  const [userId, setUserId] = useState('')
  const [appToken, setAppToken] = useState('')
  const [error, setError] = useState('')
  const [connectionMessage, setConnectionMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      fetchConnection(controller.signal),
      fetchSyncJob(controller.signal),
      fetchProfile(controller.signal),
    ])
      .then(([loadedConnection, loadedSyncJob]) => {
        setConnection(loadedConnection)
        setSyncJob(loadedSyncJob)
        setUserId(loadedConnection.user_id ?? '')
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof Error ? reason.message : 'Unable to load settings',
          )
        }
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (syncJob?.status !== 'running') return

    const interval = window.setInterval(() => {
      fetchSyncJob()
        .then(setSyncJob)
        .catch(() => undefined)
    }, 2000)

    return () => window.clearInterval(interval)
  }, [syncJob?.status])

  async function saveConnection(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setConnectionMessage('')

    const body: { user_id: string | null; app_token?: string } = {
      user_id: userId || null,
    }
    if (appToken) body.app_token = appToken

    try {
      const saved = await updateConnection(body)
      setConnection(saved)
      setUserId(saved.user_id ?? '')
      setAppToken('')
      setConnectionMessage('Connection saved.')
    } catch (reason: unknown) {
      setError(
        reason instanceof Error ? reason.message : 'Unable to save connection',
      )
    } finally {
      setSaving(false)
    }
  }

  async function handleSync() {
    setSyncing(true)
    setError('')
    try {
      const job = await startSyncJob()
      setSyncJob(job)
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Unable to start sync')
    } finally {
      setSyncing(false)
    }
  }

  if (error && (!connection || !syncJob)) {
    return <PageMessage title="Settings unavailable" detail={error} />
  }

  if (!connection || !syncJob) {
    return (
      <PageMessage
        title="Loading settings"
        detail="Reading connection and sync status…"
      />
    )
  }

  const tokenDisplay =
    connection.token_set && connection.token_hint
      ? `••••${connection.token_hint}`
      : connection.token_set
        ? '••••••••'
        : 'Not set'

  const syncRunning = syncJob.status === 'running'

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Self-hosted</p>
          <h1>Settings</h1>
        </div>
        <p className="status">
          <span aria-hidden="true" />
          Connection &amp; sync
        </p>
      </div>

      <section className="data-section" aria-labelledby="connection-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Zepp API</p>
            <h2 id="connection-title">Connection</h2>
          </div>
          <small>Stored on this device</small>
        </div>
        <form className="profile-form" onSubmit={saveConnection}>
          <label>
            <span>User ID</span>
            <input
              aria-label="User ID"
              type="text"
              value={userId}
              onChange={(event) => {
                setConnectionMessage('')
                setUserId(event.currentTarget.value)
              }}
            />
          </label>
          <label>
            <span>Credential</span>
            <input
              aria-label="App token"
              type="password"
              placeholder="Leave blank to keep"
              value={appToken}
              onChange={(event) => {
                setConnectionMessage('')
                setAppToken(event.currentTarget.value)
              }}
            />
            <small>Current: {tokenDisplay}</small>
          </label>
          <div className="profile-form__actions">
            <button type="submit" disabled={saving}>
              {saving ? 'Saving…' : 'Save connection'}
            </button>
            <p aria-live="polite">{connectionMessage || error}</p>
          </div>
        </form>
      </section>

      <section className="data-section" aria-labelledby="sync-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Data import</p>
            <h2 id="sync-title">Sync</h2>
          </div>
          <small>Pull activities from Zepp</small>
        </div>
        <div className="profile-form">
          <p>
            Status: <strong>{syncJob.status}</strong>
            {syncJob.message && <> — {syncJob.message}</>}
            {syncJob.error && <> — {syncJob.error}</>}
          </p>
          <div className="profile-form__actions">
            <button
              type="button"
              disabled={syncRunning || syncing}
              onClick={handleSync}
            >
              Sync now
            </button>
          </div>
        </div>
      </section>

      <section className="data-section" aria-labelledby="profile-stub-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Coming soon</p>
            <h2 id="profile-stub-title">Profile</h2>
          </div>
        </div>
      </section>
    </>
  )
}

function PageMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <section className="empty-state" aria-live="polite">
      <p className="eyebrow">Self-hosted</p>
      <h1>{title}</h1>
      <p>{detail}</p>
    </section>
  )
}
