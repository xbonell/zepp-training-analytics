import { useState, type FormEvent } from 'react'
import type { ActivityFilters } from '../api/client'
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
        <span>Sport type</span>
        <select
          value={sportType}
          onChange={(event) => setSportType(event.target.value)}
        >
          <option value="">All sports</option>
          <option value="1">Sport 1</option>
          <option value="2">Sport 2</option>
          <option value="3">Sport 3</option>
          <option value="4">Sport 4</option>
          <option value="5">Sport 5</option>
        </select>
      </label>
      <button type="submit">Apply filters</button>
    </form>
  )
}
