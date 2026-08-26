import {
  dateRangeForPreset,
  type DateRange,
  type PeriodPreset,
} from './period'

const presets: { value: PeriodPreset; label: string }[] = [
  { value: '7d', label: '7 days' },
  { value: '30d', label: '30 days' },
  { value: '90d', label: '90 days' },
  { value: 'ytd', label: 'YTD' },
  { value: 'all', label: 'All' },
]

interface PeriodPresetsProps {
  selected?: PeriodPreset
  onSelect: (preset: PeriodPreset, range: DateRange) => void
}

export function PeriodPresets({
  selected,
  onSelect,
}: PeriodPresetsProps) {
  return (
    <fieldset className="period-presets">
      <legend>Period</legend>
      {presets.map((preset) => (
        <button
          key={preset.value}
          type="button"
          aria-pressed={selected === preset.value}
          onClick={() =>
            onSelect(preset.value, dateRangeForPreset(preset.value))
          }
        >
          {preset.label}
        </button>
      ))}
    </fieldset>
  )
}
