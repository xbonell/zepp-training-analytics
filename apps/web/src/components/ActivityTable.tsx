import type { ActivitySummary } from '../api/client'

interface ActivityTableProps {
  activities: ActivitySummary[]
  compact?: boolean
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

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function ActivityTable({
  activities,
  compact = false,
}: ActivityTableProps) {
  return (
    <div className="activity-table-wrap">
      <table className="activity-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Sport</th>
            <th>Duration</th>
            <th>Distance</th>
            {!compact && <th>Avg / max HR</th>}
            <th>Splat</th>
          </tr>
        </thead>
        <tbody>
          {activities.map((activity) => (
            <tr key={activity.activity_id}>
              <td data-label="Date">{formatDate(activity.started_at)}</td>
              <td data-label="Sport">Sport {activity.sport_type}</td>
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
              <td data-label="Splat">
                {Number.isFinite(activity.splat_minutes_estimate)
                  ? `${Math.round(activity.splat_minutes_estimate)} min`
                  : '—'}{' '}
                <small>local estimate</small>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
