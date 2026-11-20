import type { Day } from './simulation'

export class DayError extends Error {
  constructor(readonly status: number, message: string) {
    super(message)
  }
}

export async function loadDay(date: string, signal: AbortSignal): Promise<Day> {
  let response: Response
  try {
    response = await fetch(`/api/day?${new URLSearchParams({ date })}`, { signal })
  } catch {
    throw new DayError(0, 'Could not reach FastAPI. Check that the local server is running and try again.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    if (response.status === 404) {
      throw new DayError(404, 'This date has no usable morning buoy observation or falls outside the historical data. Try a nearby date or load the demo day.')
    }
    if (response.status === 422) {
      throw new DayError(422, 'Choose a valid calendar date and try again.')
    }
    throw new DayError(response.status, typeof detail === 'string' ? detail
      : 'FastAPI could not load this day. Check the server terminal for details and try again.')
  }
  const day: Day | null = await response.json().catch(() => null)
  if (!day || !Array.isArray(day.hours)) {
    throw new DayError(502, 'FastAPI returned an unexpected response. Check the server terminal and try again.')
  }
  if (!day.hours.length) {
    throw new DayError(404, 'The API returned no hourly observations for this date.')
  }
  return day
}
