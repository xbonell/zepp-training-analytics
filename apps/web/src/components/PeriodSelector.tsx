import { useEffect, useState, type FormEvent } from 'react'
import {
  fetchSports,
  type ActivityFilters,
  type SportTypeOption,
} from '../api/client'
import { type DateRange, type PeriodPreset } from './period'
import { PeriodPresets } from './PeriodPresets'

interface PeriodSelectorProps {
  onApply: (filters: ActivityFilters) => void
}

export function PeriodSelector({ onApply }: PeriodSelectorProps) {
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [sportType, setSportType] = useState('')
  const [period, setPeriod] = useState<PeriodPreset | undefined>('all')
  const [sports, setSports] = useState<SportTypeOption[]>([])

  useEffect(() => {
    const controller = new AbortController()
    fetchSports(controller.signal)
      .then(setSports)
      .catch(() => {
        if (!controller.signal.aborted) setSports([])
      })
    return () => controller.abort()
  }, [])

  function selectPeriod(nextPeriod: PeriodPreset, range: DateRange) {
    setPeriod(nextPeriod)
    setFrom(range.from ?? '')
    setTo(range.to ?? '')
    onApply({
      ...range,
      ...(sportType ? { sportType: Number(sportType) } : {}),
    })
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onApply({
      ...(from ? { from } : {}),
      ...(to ? { to } : {}),
      ...(sportType ? { sportType: Number(sportType) } : {}),
    })
  }

  return (
    <form className="period-selector" onSubmit={handleSubmit}>
      <PeriodPresets selected={period} onSelect={selectPeriod} />
      <label>
        <span>From</span>
        <input
          type="date"
          value={from}
          max={to || undefined}
          onChange={(event) => {
            setPeriod(undefined)
            setFrom(event.target.value)
          }}
        />
      </label>
      <label>
        <span>To</span>
        <input
          type="date"
          value={to}
          min={from || undefined}
          onChange={(event) => {
            setPeriod(undefined)
            setTo(event.target.value)
          }}
        />
      </label>
      <label>
        <span>Activity type</span>
        <select
          aria-label="Activity type"
          value={sportType}
          onChange={(event) => setSportType(event.target.value)}
        >
          <option value="">All activities</option>
          {sports.map((sport) => (
            <option key={sport.sport_type} value={sport.sport_type}>
              {sport.label}
            </option>
          ))}
        </select>
      </label>
      <button type="submit">Apply filters</button>
    </form>
  )
}
