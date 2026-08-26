import {
  type HeartRatePoint,
  type ZoneBoundaries,
  type ZoneId,
} from '../api/client'

interface HrZoneChartProps {
  series: HeartRatePoint[]
  boundaries: ZoneBoundaries
}

const width = 900
const height = 320
const plot = { left: 54, top: 20, width: 826, height: 252 }
const chartZones: ZoneId[] = ['z5', 'z4', 'z3', 'z2', 'z1', 'below']

function durationLabel(seconds: number) {
  if (seconds < 60) return `${seconds} seconds`
  const minutes = Math.round(seconds / 60)
  return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`
}

export function HrZoneChart({ series, boundaries }: HrZoneChartProps) {
  if (series.length === 0) {
    return <p className="chart-empty">No heart-rate samples recorded.</p>
  }

  const heartRates = series.map((point) => point.hr_bpm)
  const minHr = Math.min(...heartRates)
  const maxHr = Math.max(...heartRates)
  const lastElapsed = Math.max(...series.map((point) => point.elapsed_s))
  const boundaryValues = Object.values(boundaries).flatMap((boundary) =>
    boundary ? [...boundary] : [],
  )
  const domainMin = Math.min(minHr, ...boundaryValues)
  const domainMax = Math.max(maxHr, ...boundaryValues)
  const hrSpan = Math.max(domainMax - domainMin, 1)
  const timeSpan = Math.max(lastElapsed, 1)
  const yForBpm = (bpm: number) =>
    plot.top + ((domainMax - bpm) / hrSpan) * plot.height
  const points = series
    .map((point) => {
      const x = plot.left + (point.elapsed_s / timeSpan) * plot.width
      const y = yForBpm(point.hr_bpm)
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  return (
    <div className="hr-chart">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`Heart rate from ${minHr} to ${maxHr} beats per minute over ${durationLabel(lastElapsed)}`}
      >
        {chartZones.map((zone) => {
          const boundary = boundaries[zone]
          if (!boundary) return null
          const [first, second] = boundary
          const lo = Math.min(first, second)
          const hi = Math.max(first, second)
          return (
            <rect
              key={zone}
              className={`hr-chart__band zone-${zone}`}
              data-zone={zone}
              x={plot.left}
              y={yForBpm(hi)}
              width={plot.width}
              height={yForBpm(lo) - yForBpm(hi)}
            />
          )
        })}
        {chartZones.map((zone) => {
          const boundary = boundaries[zone]
          if (!boundary) return null
          const hi = Math.max(...boundary)
          return (
            <text
              key={`${zone}-label`}
              className="hr-chart__zone-label"
              x={plot.left + 8}
              y={yForBpm(hi) + 15}
            >
              {zone.toUpperCase()}
            </text>
          )
        })}
        <polyline className="hr-chart__line" points={points} />
        <text className="hr-chart__axis-label" x={plot.left} y={height - 18}>
          0:00
        </text>
        <text
          className="hr-chart__axis-label"
          x={plot.left + plot.width}
          y={height - 18}
          textAnchor="end"
        >
          {Math.floor(lastElapsed / 60)}:
          {String(lastElapsed % 60).padStart(2, '0')}
        </text>
        <text
          className="hr-chart__axis-label"
          x={plot.left + plot.width}
          y={14}
          textAnchor="end"
        >
          Range {minHr}–{maxHr} bpm
        </text>
      </svg>
    </div>
  )
}
