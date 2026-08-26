import { type FormEvent, useEffect, useState } from 'react'
import {
  fetchProfile,
  fetchZones,
  type Profile,
  type ZoneId,
  type ZonesResponse,
  updateProfile,
} from '../api/client'

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

type FormState = {
  hrmaxOverride: string
  restingHr: string
  birthDate: string
  sex: string
}

function profileForm(profile: Profile): FormState {
  return {
    hrmaxOverride: profile.hrmax_override?.toString() ?? '',
    restingHr: profile.resting_hr?.toString() ?? '',
    birthDate: profile.birth_date ?? '',
    sex: profile.sex ?? '',
  }
}

function optionalNumber(value: string) {
  return value === '' ? null : Number(value)
}

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
  const [profile, setProfile] = useState<Profile>()
  const [zones, setZones] = useState<ZonesResponse>()
  const [form, setForm] = useState<FormState>()
  const [error, setError] = useState('')
  const [saveMessage, setSaveMessage] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      fetchProfile(controller.signal),
      fetchZones(controller.signal),
    ])
      .then(([loadedProfile, loadedZones]) => {
        setProfile(loadedProfile)
        setForm(profileForm(loadedProfile))
        setZones(loadedZones)
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

  function changeField(field: keyof FormState, value: string) {
    setSaveMessage('')
    setForm((current) => (current ? { ...current, [field]: value } : current))
  }

  async function save(event: FormEvent) {
    event.preventDefault()
    if (!profile || !form) return

    setSaving(true)
    setError('')
    setSaveMessage('')
    const nextProfile: Profile = {
      ...profile,
      hrmax_override: optionalNumber(form.hrmaxOverride),
      resting_hr: optionalNumber(form.restingHr),
      birth_date: form.birthDate || null,
      sex: form.sex || null,
    }

    try {
      const savedProfile = await updateProfile(nextProfile)
      const refreshedZones = await fetchZones()
      setProfile(savedProfile)
      setForm(profileForm(savedProfile))
      setZones(refreshedZones)
      setSaveMessage('Profile saved.')
    } catch (reason: unknown) {
      setError(
        reason instanceof Error ? reason.message : 'Unable to save settings',
      )
    } finally {
      setSaving(false)
    }
  }

  if (error && (!profile || !zones || !form)) {
    return <PageMessage title="Zone settings unavailable" detail={error} />
  }

  if (!profile || !zones || !form) {
    return (
      <PageMessage
        title="Loading zone settings"
        detail="Reading your local training profile…"
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

      <section className="data-section" aria-labelledby="profile-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Local settings</p>
            <h2 id="profile-title">Training profile</h2>
          </div>
          <small>Stored on this device</small>
        </div>
        <form className="profile-form" onSubmit={save}>
          <label>
            <span>HRmax override</span>
            <input
              aria-label="HRmax override"
              type="number"
              min="1"
              step="0.1"
              inputMode="decimal"
              placeholder={zones.hrmax?.toString() ?? 'BPM'}
              value={form.hrmaxOverride}
              onChange={(event) =>
                changeField('hrmaxOverride', event.currentTarget.value)
              }
            />
          </label>
          <label>
            <span>Resting heart rate</span>
            <input
              aria-label="Resting heart rate"
              type="number"
              min="1"
              inputMode="numeric"
              placeholder="BPM"
              value={form.restingHr}
              onChange={(event) =>
                changeField('restingHr', event.currentTarget.value)
              }
            />
          </label>
          <label>
            <span>Birth date</span>
            <input
              aria-label="Birth date"
              type="date"
              value={form.birthDate}
              onChange={(event) =>
                changeField('birthDate', event.currentTarget.value)
              }
            />
          </label>
          <label>
            <span>Sex</span>
            <select
              aria-label="Sex"
              value={form.sex}
              onChange={(event) => changeField('sex', event.currentTarget.value)}
            >
              <option value="">Not specified</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </select>
          </label>
          <div className="profile-form__actions">
            <button type="submit" disabled={saving}>
              {saving ? 'Saving…' : 'Save profile'}
            </button>
            <p aria-live="polite">{saveMessage || error}</p>
          </div>
        </form>
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
