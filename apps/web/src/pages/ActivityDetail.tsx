import { useEffect, useState } from 'react'
import {
  fetchActivityDetail,
  fetchProfile,
  fetchZones,
  zoneIds,
  type ActivityDetail as ActivityDetailData,
  type ZoneBoundaries,
} from '../api/client'
import { HrZoneChart } from '../components/HrZoneChart'

interface ActivityDetailProps {
  activityId: string
}

interface LoadState {
  activityId?: string
  activity?: ActivityDetailData
  boundaries?: ZoneBoundaries
  timeZone?: string
  zonesUnavailable?: boolean
  error?: string
}

function formatClock(seconds: number) {
  const rounded = Math.max(0, Math.round(seconds))
  const hours = Math.floor(rounded / 3600)
  const minutes = Math.floor((rounded % 3600) / 60)
  const remainder = rounded % 60
  return hours
    ? `${hours}:${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
    : `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
}

function formatDate(value: string, timeZone: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'long',
    timeStyle: 'short',
    timeZone,
  }).format(new Date(value))
}

export function ActivityDetail({ activityId }: ActivityDetailProps) {
  const [loadState, setLoadState] = useState<LoadState>({})

  useEffect(() => {
    const controller = new AbortController()
    Promise.allSettled([
      fetchActivityDetail(activityId, controller.signal),
      fetchZones(controller.signal),
      fetchProfile(controller.signal),
    ])
      .then(([activityResult, zonesResult, profileResult]) => {
        if (controller.signal.aborted) return
        if (activityResult.status === 'rejected') {
          const reason: unknown = activityResult.reason
          setLoadState({
            activityId,
            error:
              reason instanceof Error ? reason.message : 'Unable to load data',
          })
          return
        }
        setLoadState({
          activityId,
          activity: activityResult.value,
          boundaries:
            zonesResult.status === 'fulfilled'
              ? zonesResult.value.boundaries
              : {},
          timeZone:
            profileResult.status === 'fulfilled'
              ? profileResult.value.display_timezone
              : 'Europe/Madrid',
          zonesUnavailable: zonesResult.status === 'rejected',
        })
      })
    return () => controller.abort()
  }, [activityId])

  const error =
    loadState.activityId === activityId ? loadState.error : undefined
  const activity =
    loadState.activityId === activityId ? loadState.activity : undefined
  const boundaries =
    loadState.activityId === activityId ? loadState.boundaries : undefined
  const timeZone =
    loadState.activityId === activityId
      ? (loadState.timeZone ?? 'Europe/Madrid')
      : 'Europe/Madrid'
  const zonesUnavailable =
    loadState.activityId === activityId && loadState.zonesUnavailable

  if (error) {
    return (
      <section className="inline-message">
        <p className="eyebrow">Session archive</p>
        <h1>Activity unavailable</h1>
        <p>{error}</p>
        <a className="detail-back-link" href="#activities">
          ← Back to activities
        </a>
      </section>
    )
  }

  if (!activity) {
    return <p className="loading-message">Reading local activity detail…</p>
  }

  const totalZoneSeconds = zoneIds.reduce(
    (sum, zone) => sum + activity.time_in_zone[zone],
    0,
  )

  return (
    <>
      <a className="detail-back-link" href="#activities">
        ← All activities
      </a>
      <div className="page-heading detail-heading">
        <div>
          <p className="eyebrow">{activity.sport_label}</p>
          <h1>Activity detail</h1>
        </div>
        <p className="detail-date">{formatDate(activity.started_at, timeZone)}</p>
      </div>

      <section className="metrics detail-metrics" aria-label="Activity metrics">
        <div>
          <span>Duration</span>
          <strong>{formatClock(activity.duration_s)}</strong>
        </div>
        <div>
          <span>Average HR</span>
          <strong>
            {activity.avg_hr == null ? '—' : `${Math.round(activity.avg_hr)} bpm`}
          </strong>
        </div>
        <div>
          <span>Max HR</span>
          <strong>
            {activity.max_hr == null ? '—' : `${Math.round(activity.max_hr)} bpm`}
          </strong>
        </div>
        <div>
          <span>Splat minutes</span>
          <strong>{Math.round(activity.splat_minutes_estimate)} min</strong>
          <small>local estimate</small>
        </div>
      </section>

      <section className="data-section chart-section">
        <div className="section-heading">
          <h2>Heart rate</h2>
          <small>{activity.hr_series.length} samples</small>
        </div>
        {zonesUnavailable && (
          <p className="inline-note">Zone boundaries unavailable.</p>
        )}
        <HrZoneChart series={activity.hr_series} boundaries={boundaries ?? {}} />
      </section>

      <section className="data-section zone-breakdown">
        <div className="section-heading">
          <h2>Time in zone</h2>
          <small>{formatClock(totalZoneSeconds)} classified</small>
        </div>
        <ul>
          {zoneIds.map((zone) => {
            const seconds = activity.time_in_zone[zone]
            const percent =
              totalZoneSeconds === 0 ? 0 : (seconds / totalZoneSeconds) * 100
            return (
              <li key={zone}>
                <span className={`zone-chip zone-${zone}`}>
                  {zone.toUpperCase()}
                </span>
                <div className="zone-breakdown__track" aria-hidden="true">
                  <span
                    className={`zone-${zone}`}
                    style={{ width: `${percent}%` }}
                  />
                </div>
                <strong>{formatClock(seconds)}</strong>
                <small>{Math.round(percent)}%</small>
              </li>
            )
          })}
        </ul>
      </section>
    </>
  )
}
