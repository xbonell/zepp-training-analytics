import { zoneIds, type ZoneTotals } from '../api/client'

const zoneLabels: Record<(typeof zoneIds)[number], string> = {
  below: 'Below',
  z1: 'Z1',
  z2: 'Z2',
  z3: 'Z3',
  z4: 'Z4',
  z5: 'Z5',
}

interface ZoneMixBarProps {
  zones: ZoneTotals
}

export function ZoneMixBar({ zones }: ZoneMixBarProps) {
  const total = zoneIds.reduce((sum, zone) => sum + (zones[zone] ?? 0), 0)

  return (
    <div className="zone-mix">
      <div
        className="zone-mix__bar"
        role="img"
        aria-label="Heart-rate zone mix"
      >
        {zoneIds.map((zone) => (
          <span
            className={`zone-${zone}`}
            key={zone}
            style={{ width: `${total ? (zones[zone] / total) * 100 : 0}%` }}
          />
        ))}
      </div>
      <div className="zone-mix__legend">
        {zoneIds.map((zone) => (
          <span key={zone}>
            <i className={`zone-${zone}`} aria-hidden="true" />
            {zoneLabels[zone]}{' '}
            <strong>{total ? Math.round((zones[zone] / total) * 100) : 0}%</strong>
          </span>
        ))}
      </div>
    </div>
  )
}
