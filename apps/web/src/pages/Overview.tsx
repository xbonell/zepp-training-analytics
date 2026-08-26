import { useEffect, useState } from 'react'
import {
  fetchOverview,
  type OverviewFilters,
  type OverviewResponse,
} from '../api/client'
import { ActivityTable } from '../components/ActivityTable'
import {
  type DateRange,
  type PeriodPreset,
} from '../components/period'
import { PeriodPresets } from '../components/PeriodPresets'
import { ZoneMixBar } from '../components/ZoneMixBar'

function formatTotalDuration(seconds: number) {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.round((seconds % 3600) / 60)
  return hours ? `${hours}h ${minutes}m` : `${minutes} min`
}

export function Overview() {
  const [overview, setOverview] = useState<OverviewResponse>()
  const [error, setError] = useState('')
  const [filters, setFilters] = useState<OverviewFilters>({})
  const [period, setPeriod] = useState<PeriodPreset>('all')

  useEffect(() => {
    const controller = new AbortController()
    fetchOverview(filters, controller.signal)
      .then(setOverview)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Unable to load data')
        }
      })
    return () => controller.abort()
  }, [filters])

  function selectPeriod(nextPeriod: PeriodPreset, range: DateRange) {
    setError('')
    setPeriod(nextPeriod)
    setFilters(range)
  }

  if (error) {
    return <PageMessage title="Overview unavailable" detail={error} />
  }

  if (!overview) {
    return <PageMessage title="Loading overview" detail="Reading local activity data…" />
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Dashboard / {periodLabel(period)}</p>
          <h1>Training overview</h1>
        </div>
        <p className="status">
          <span aria-hidden="true" />
          Local activity data
        </p>
      </div>

      <PeriodPresets selected={period} onSelect={selectPeriod} />

      <section className="metrics" aria-label="Training totals">
        <div>
          <span>Activities</span>
          <strong>{overview.activity_count}</strong>
        </div>
        <div>
          <span>Duration</span>
          <strong>{formatTotalDuration(overview.duration_s)}</strong>
        </div>
        <div>
          <span>Local splat estimate</span>
          <strong>{Math.round(overview.splat_minutes_estimate)} min</strong>
        </div>
      </section>

      {overview.activity_count === 0 ? (
        <section className="empty-state" aria-labelledby="empty-state-title">
          <p className="eyebrow">No sessions synced</p>
          <h2 id="empty-state-title">Start with your latest workout.</h2>
          <p>
            Training load, heart-rate zones, and activity trends will appear
            once the API returns activity data.
          </p>
        </section>
      ) : (
        <>
          <section className="data-section" aria-labelledby="zone-mix-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Intensity distribution</p>
                <h2 id="zone-mix-title">Zone mix</h2>
              </div>
              <small>Below · Z1–Z5</small>
            </div>
            <ZoneMixBar zones={overview.zone_mix} />
          </section>

          <section className="data-section" aria-labelledby="recent-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Latest sessions</p>
                <h2 id="recent-title">Recent activity</h2>
              </div>
              <a href="#activities">View all</a>
            </div>
            <ActivityTable activities={overview.recent} compact />
          </section>
        </>
      )}
    </>
  )
}

function periodLabel(period: PeriodPreset) {
  return {
    '7d': '7 days',
    '30d': '30 days',
    '90d': '90 days',
    ytd: 'year to date',
    all: 'all time',
  }[period]
}

function PageMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <section className="empty-state" aria-live="polite">
      <p className="eyebrow">Training overview</p>
      <h1>{title}</h1>
      <p>{detail}</p>
    </section>
  )
}
