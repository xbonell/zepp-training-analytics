import { type FormEvent, useEffect, useState } from 'react'
import { type Profile, updateProfile } from '../api/client'

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

type ProfileFormProps = {
  profile: Profile
  hrmaxPlaceholder?: string
  onSaved: (profile: Profile) => void
}

export function ProfileForm({
  profile,
  hrmaxPlaceholder = 'BPM',
  onSaved,
}: ProfileFormProps) {
  const [form, setForm] = useState(() => profileForm(profile))
  const [error, setError] = useState('')
  const [saveMessage, setSaveMessage] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setForm(profileForm(profile))
  }, [profile])

  function changeField(field: keyof FormState, value: string) {
    setSaveMessage('')
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function save(event: FormEvent) {
    event.preventDefault()

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
      setForm(profileForm(savedProfile))
      setSaveMessage('Profile saved.')
      onSaved(savedProfile)
    } catch (reason: unknown) {
      setError(
        reason instanceof Error ? reason.message : 'Unable to save settings',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="profile-form" onSubmit={save}>
      <label>
        <span>HRmax override</span>
        <input
          aria-label="HRmax override"
          type="number"
          min="1"
          step="0.1"
          inputMode="decimal"
          placeholder={hrmaxPlaceholder}
          value={form.hrmaxOverride}
          onChange={(event) =>
            changeField('hrmaxOverride', event.currentTarget.value)
          }
        />
        <small>Leave blank to use the suggested value.</small>
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
  )
}
