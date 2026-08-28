import { useEffect, useState } from 'react'
import {
  fetchActivities,
  fetchProfile,
  type ActivityFilters,
  type ActivitySummary,
} from '../api/client'
import { ActivityTable } from '../components/ActivityTable'
import { PeriodSelector } from '../components/PeriodSelector'

export function Activities() {
  const [filters, setFilters] = useState<ActivityFilters>({})
  const [activities, setActivities] = useState<ActivitySummary[]>()
  const [error, setError] = useState('')
  const [timeZone, setTimeZone] = useState('Europe/Madrid')

  useEffect(() => {
    const controller = new AbortController()
    fetchProfile(controller.signal)
      .then((profile) => setTimeZone(profile.display_timezone))
      .catch(() => undefined)
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    fetchActivities(filters, controller.signal)
      .then(setActivities)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Unable to load data')
        }
      })
    return () => controller.abort()
  }, [filters])

  function applyFilters(nextFilters: ActivityFilters) {
    setError('')
    setActivities(undefined)
    setFilters(nextFilters)
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Session archive</p>
          <h1>Activities</h1>
        </div>
        <p className="status">
          <span aria-hidden="true" />
          {activities ? `${activities.length} matching` : 'Loading'}
        </p>
      </div>

      <PeriodSelector onApply={applyFilters} />

      <section className="data-section" aria-live="polite">
        {error ? (
          <div className="inline-message">
            <h2>Activities unavailable</h2>
            <p>{error}</p>
          </div>
        ) : !activities ? (
          <p className="loading-message">Reading local activity data…</p>
        ) : activities.length === 0 ? (
          <div className="inline-message">
            <h2>No matching activities</h2>
            <p>Try a wider period or clear the activity type filter.</p>
          </div>
        ) : (
          <ActivityTable activities={activities} timeZone={timeZone} />
        )}
      </section>
    </>
  )
}
