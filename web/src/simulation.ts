export const VARIABLES = ['wind', 'temp', 'rh', 'sea', 'pres'] as const
export type Variable = (typeof VARIABLES)[number]
export const LABELS: Record<Variable, string> = {
  wind: 'Wind speed',
  temp: 'Air temperature',
  rh: 'Relative humidity',
  sea: 'Sea temperature',
  pres: 'Atmospheric pressure',
}
export const EXAMPLE_DATE = '2024-12-04'

type Measurement = {
  forecast: number | null
  lo: number | null
  hi: number | null
  actual: number | null
  in_bounds: boolean | null
  nn_updated: number | null
}
type Hour = { hour: string; vars: Record<Variable, Measurement> }
type Flag = {
  time: string
  variables: Variable[]
  values: Partial<Record<Variable, number>>
  bounds: Partial<Record<Variable, [number, number]>>
}
type ForecastPath = {
  hours: string[]
  vars: Record<Variable, (number | null)[]>
}
export type Day = {
  date: string
  station: string
  hours: Hour[]
  flag: Flag | null
  nn_paths: Record<string, ForecastPath>
  units: Record<Variable, string>
  timezone: string
  bounds_rule: {
    persist_hours: number
    half_width: Record<Variable, number>
    wind_note: string
    source: string
  }
}

export type IssuedPath = ForecastPath & { origin: string }
export type Event = {
  index: number
  time: string
  kind: 'baseline' | 'observation' | 'deviation' | 'alert' | 'update'
  title: string
  detail: string
}

export const hourLabel = (time: string) => time.slice(11, 16)
export const targetLabel = (time: string, date: string) =>
  hourLabel(time) + (time.slice(0, 10) === date ? '' : ' +1d')
export const variableList = (variables: Variable[]) =>
  variables.map(variable => LABELS[variable]).join(', ')

const numberFormat = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
  useGrouping: false,
})
export function formatValue(value: number | null | undefined, unit = '') {
  return value == null ? '—' : numberFormat.format(value) + (unit ? ` ${unit}` : '')
}

export function shiftDate(date: string, offset: number) {
  const day = new Date(`${date}T12:00:00Z`)
  if (!Number.isFinite(day.getTime())) return null
  day.setUTCDate(day.getUTCDate() + offset)
  const year = day.getUTCFullYear()
  return year >= 1 && year <= 9999 ? day.toISOString().slice(0, 10) : null
}

export function getFrame(day: Day, index: number) {
  const elapsed = day.hours.slice(0, index + 1)
  const current = elapsed[elapsed.length - 1]
  const flag = day.flag && day.flag.time <= current.hour ? day.flag : null
  const paths = flag
    ? Object.entries(day.nn_paths)
        .filter(([origin]) => origin >= flag.time && origin <= current.hour)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([origin, path]) => ({ origin, ...path }))
    : []
  const path = paths.at(-1)
  const misses = VARIABLES.filter(variable => current.vars[variable].in_bounds === false)
  const assessed = VARIABLES.some(variable => {
    const row = current.vars[variable]
    return row.in_bounds !== null && row.forecast !== null
  })
  const status = path ? 'Update active'
    : flag ? 'Deviation detected'
    : misses.length ? 'Deviation observed'
    : assessed ? 'Within bounds' : 'Observations unavailable'

  // Verifying the selected hour requires a forecast issued before its observation.
  const priorPath = paths.findLast(candidate => candidate.hours.includes(current.hour))
  const priorLead = priorPath?.hours.indexOf(current.hour) ?? -1

  return { elapsed, current, flag, paths, path, status, priorPath, priorLead }
}

export type Frame = ReturnType<typeof getFrame>

export function buildChartRows(day: Day, frame: Frame, variable: Variable) {
  const baseline = new Map(day.hours.map(row => [row.hour, row.vars[variable]]))
  const observed = new Map(frame.elapsed.map(row => [row.hour, row.vars[variable].actual]))
  const path = frame.path
  const predictions = new Map(path?.hours.map((hour, index) =>
    [hour, path.vars[variable][index]] as const))
  const times = [...new Set([...baseline.keys(), ...predictions.keys()])].sort()
  return times.map(time => {
    const row = baseline.get(time)
    return {
      time,
      baseline: row?.forecast ?? null,
      band: row?.lo != null && row.hi != null ? [row.lo, row.hi] : null,
      actual: observed.get(time) ?? null,
      update: predictions.get(time) ?? null,
    }
  })
}

export function buildEvents(day: Day, frame: Frame): Event[] {
  const first = frame.elapsed[0].hour
  const last = day.hours[day.hours.length - 1].hour
  const events: Event[] = [{
    index: 0, time: first, kind: 'baseline', title: 'Baseline forecast issued',
    detail: `Stand-in forecast for ${hourLabel(first)}–${hourLabel(last)}.`,
  }]
  const paths = new Map(frame.paths.map(path => [path.origin, path]))
  frame.elapsed.forEach((row, index) => {
    const time = row.hour
    const count = VARIABLES.filter(variable => row.vars[variable].actual !== null).length
    if (count) events.push({
      index, time, kind: 'observation', title: 'Buoy observation received',
      detail: `${count} of ${VARIABLES.length} variables reported.`,
    })
    const misses = VARIABLES.filter(variable => row.vars[variable].in_bounds === false)
    if (misses.length) events.push({
      index, time, kind: 'deviation', title: 'Deviation observed',
      detail: variableList(misses),
    })
    if (frame.flag?.time === time) events.push({
      index, time, kind: 'alert', title: 'Deviation confirmed',
      detail: variableList(frame.flag.variables),
    })
    const path = paths.get(time)
    if (path) events.push({
      index, time, kind: 'update', title: 'Neural forecast issued',
      detail: `Targets ${targetLabel(path.hours[0], day.date)}–${targetLabel(path.hours[path.hours.length - 1], day.date)}.`,
    })
  })
  return events
}
