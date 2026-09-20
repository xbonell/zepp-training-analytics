import {
  zoneIds,
  type ActivitySummary,
  type ZoneId,
  type ZoneTotals,
} from '../api/client'

interface ActivityTableProps {
  activities: ActivitySummary[]
  compact?: boolean
  timeZone?: string
}

function formatDuration(seconds?: number | null) {
  if (seconds == null) return '—'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.round((seconds % 3600) / 60)
  return hours ? `${hours}h ${minutes}m` : `${minutes} min`
}

function formatDistance(metres?: number | null) {
  return metres == null ? '—' : `${(metres / 1000).toFixed(1)} km`
}

function formatDate(value: string, timeZone: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone,
  }).format(new Date(value))
}

function dominantZone(zones: ZoneTotals): ZoneId | undefined {
  const total = zoneIds.reduce((sum, zone) => sum + zones[zone], 0)
  if (total === 0) return undefined
  return zoneIds.reduce((dominant, zone) =>
    zones[zone] > zones[dominant] ? zone : dominant,
  )
}

function ZoneChip({ zones }: { zones: ZoneTotals }) {
  const zone = dominantZone(zones)
  return zone ? (
    <span className={`zone-chip zone-${zone}`}>{zone.toUpperCase()}</span>
  ) : (
    '—'
  )
}

export function ActivityTable({
  activities,
  compact = false,
  timeZone = 'Europe/Madrid',
}: ActivityTableProps) {
  return (
    <div className="activity-table-wrap">
      <table className="activity-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Activity</th>
            <th>Duration</th>
            <th>Distance</th>
            {!compact && <th>Avg / max HR</th>}
            <th>Zone</th>
            <th>Splat</th>
          </tr>
        </thead>
        <tbody>
          {activities.map((activity) => (
            <tr key={activity.activity_id}>
              <td data-label="Date">
                <a
                  className="activity-link"
                  href={`#activities/${encodeURIComponent(activity.activity_id)}`}
                >
                  {formatDate(activity.started_at, timeZone)}
                </a>
              </td>
              <td data-label="Activity">{activity.sport_label}</td>
              <td data-label="Duration">
                {formatDuration(activity.duration_s)}
              </td>
              <td data-label="Distance">
                {formatDistance(activity.distance_m)}
              </td>
              {!compact && (
                <td data-label="Avg / max HR">
                  {activity.avg_hr == null
                    ? '—'
                    : `${Math.round(activity.avg_hr)} bpm`}
                  {' / '}
                  {activity.max_hr == null
                    ? '—'
                    : `${Math.round(activity.max_hr)} bpm`}
                </td>
              )}
              <td data-label="Zone">
                <ZoneChip zones={activity.time_in_zone} />
              </td>
              <td data-label="Splat">
                {Number.isFinite(activity.splat_minutes_estimate)
                  ? `${Math.round(activity.splat_minutes_estimate)}`
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
