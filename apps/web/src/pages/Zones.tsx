import { useEffect, useState } from 'react'
import { fetchZones, type ZoneId, type ZonesResponse } from '../api/client'

const OTF_ZONES: Array<{
  id: Exclude<ZoneId, 'below'>
  percent: string
  purpose: string
}> = [
  { id: 'z1', percent: '50–60%', purpose: 'Warm up' },
  { id: 'z2', percent: '61–70%', purpose: 'Easy' },
  { id: 'z3', percent: '71–83%', purpose: 'Challenging' },
  { id: 'z4', percent: '84–91%', purpose: 'Orange' },
  { id: 'z5', percent: '92–100%', purpose: 'All out' },
]

function bpmRange(
  boundary: readonly [number, number] | undefined,
  isLast: boolean,
) {
  if (!boundary) return '—'
  const minimum = Math.ceil(boundary[0])
  const maximum = isLast
    ? Math.round(boundary[1])
    : Math.ceil(boundary[1]) - 1
  return `${minimum}–${maximum} bpm`
}

export function Zones() {
  const [zones, setZones] = useState<ZonesResponse>()
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    fetchZones(controller.signal)
      .then(setZones)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof Error ? reason.message : 'Unable to load settings',
          )
        }
      })
    return () => controller.abort()
  }, [])

  if (error && !zones) {
    return <PageMessage title="Zone settings unavailable" detail={error} />
  }

  if (!zones) {
    return (
      <PageMessage
        title="Loading zone settings"
        detail="Reading your heart-rate zones…"
      />
    )
  }

  const activeLabel =
    zones.source === 'override'
      ? 'Override HRmax'
      : zones.source === 'suggested'
        ? 'Suggested HRmax'
        : 'Active HRmax'

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Heart-rate profile</p>
          <h1>Heart-rate zones</h1>
        </div>
        <p className="status">
          <span aria-hidden="true" />
          OTF five-zone model
        </p>
      </div>

      <section className="zones-summary" aria-label="HRmax summary">
        <div>
          <span>{activeLabel}</span>
          <strong>{zones.hrmax === null ? 'Not set' : `${zones.hrmax} bpm`}</strong>
          <small>
            {zones.source === 'suggested'
              ? 'Estimated from local activity samples'
              : zones.source === 'override'
                ? 'Using your profile override'
                : 'Add an override or sync HR samples'}
          </small>
        </div>
        {zones.age_formula_refs && (
          <>
            <div>
              <span>Fox · 220 − age</span>
              <strong>{zones.age_formula_refs.fox_220_minus_age} bpm</strong>
              <small>Age {zones.age_formula_refs.age} reference</small>
            </div>
            <div>
              <span>Tanaka · 208 − 0.7 × age</span>
              <strong>
                {Math.round(zones.age_formula_refs.tanaka_208_minus_0_7_age)} bpm
              </strong>
              <small>Reference only</small>
            </div>
          </>
        )}
      </section>

      <section className="data-section" aria-labelledby="otf-zones-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Live boundary preview</p>
            <h2 id="otf-zones-title">OTF zone bands</h2>
          </div>
          <small>% of active HRmax</small>
        </div>
        <div className="zones-table-wrap">
          <table className="zones-table">
            <thead>
              <tr>
                <th>Zone</th>
                <th>Range</th>
                <th>BPM preview</th>
                <th>Effort</th>
              </tr>
            </thead>
            <tbody>
              {OTF_ZONES.map((zone) => (
                <tr key={zone.id}>
                  <td>
                    <i
                      aria-hidden="true"
                      className={`zone-${zone.id}`}
                    />
                    <strong>{zone.id.toUpperCase()}</strong>
                  </td>
                  <td>{zone.percent}</td>
                  <td>{bpmRange(zones.boundaries[zone.id], zone.id === 'z5')}</td>
                  <td>{zone.purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}

function PageMessage({ title, detail }: { title: string; detail: string }) {
  return (
    <section className="empty-state" aria-live="polite">
      <p className="eyebrow">Heart-rate profile</p>
      <h1>{title}</h1>
      <p>{detail}</p>
    </section>
  )
}
