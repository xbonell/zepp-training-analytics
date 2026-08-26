export type PeriodPreset = '7d' | '30d' | '90d' | 'ytd' | 'all'

export interface DateRange {
  from?: string
  to?: string
}

function formatDate(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function dateRangeForPreset(
  preset: PeriodPreset,
  today = new Date(),
): DateRange {
  if (preset === 'all') return {}

  const from = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  if (preset === 'ytd') {
    from.setMonth(0, 1)
  } else {
    const days = Number.parseInt(preset, 10)
    from.setDate(from.getDate() - (days - 1))
  }
  return { from: formatDate(from), to: formatDate(today) }
}
