import { CalendarDays, ChevronLeft, ChevronRight, CircleAlert, Clock3, LoaderCircle, Radio, Waves } from 'lucide-react'
import { useEffect, useState } from 'react'
import { ActivityLog } from './ActivityLog'
import { DayError, loadDay } from './api'
import { ForecastChart } from './ForecastChart'
import { About, AlertDetails, Measurements, NeuralForecast } from './ForecastDetails'
import { Playback, usePlayback } from './Playback'
import { EXAMPLE_DATE, getFrame, hourLabel, shiftDate, variableList } from './simulation'
import type { Day, Frame, Variable } from './simulation'

const dateFormat = new Intl.DateTimeFormat('en-US', {
  timeZone: 'UTC', month: 'short', day: 'numeric', year: 'numeric',
})

type DayRequest = { date: string }
type Result = { request: DayRequest } & ({ day: Day } | { error: Error })

export function App() {
  const [request, setRequest] = useState<DayRequest>({ date: EXAMPLE_DATE })
  const [result, setResult] = useState<Result>()
  const { date } = request
  const previousDate = shiftDate(date, -1)
  const nextDate = shiftDate(date, 1)
  const current = result?.request === request ? result : undefined
  const day = current && 'day' in current ? current.day : undefined
  const error = current && 'error' in current ? current.error : undefined
  const unavailable = error instanceof DayError && error.status === 404

  useEffect(() => {
    if (!request.date) return
    const controller = new AbortController()
    loadDay(request.date, controller.signal).then(
      day => { if (!controller.signal.aborted) setResult({ request, day }) },
      error => { if (!controller.signal.aborted) setResult({ request, error }) },
    )
    return () => controller.abort()
  }, [request])

  function chooseDate(date: string) {
    setRequest({ date })
  }

  return (
    <>
      <header className="site-header">
        <div className="shell header-inner">
          <div className="brand">
            <span className="brand-mark"><Radio size={22} aria-hidden="true" /></span>
            <span className="brand-name">i4NS</span>
            <span className="brand-project">Environmental Research</span>
          </div>
          <span className="prototype"><span /> Historical Simulation <span className="prototype-divider">/</span> Research Prototype</span>
        </div>
      </header>
      <main className="shell dashboard">
        <div className="intro">
          <div>
            <h1>Environmental Forecast Monitor</h1>
            <p>Monitoring environmental conditions and evaluating short-term forecast updates.</p>
          </div>
          <div className="date-controls">
            <label htmlFor="historic-date">Historical date</label>
            <div className="date-row">
              <button className="button icon-button" title="Previous day" aria-label="Previous day" disabled={!previousDate} onClick={() => previousDate && chooseDate(previousDate)}><ChevronLeft size={17} /></button>
              <input id="historic-date" type="date" value={date} onChange={event => chooseDate(event.target.value)} />
              <button className="button icon-button" title="Next day" aria-label="Next day" disabled={!nextDate} onClick={() => nextDate && chooseDate(nextDate)}><ChevronRight size={17} /></button>
              <button className="button demo-button" onClick={() => chooseDate(EXAMPLE_DATE)}>Demo day</button>
            </div>
          </div>
        </div>
        {day ? <Simulation day={day} /> : <>
          <section className="panel load-state" aria-live="polite">
            {error ? <>
              <CircleAlert className="warning-text" size={26} aria-hidden="true" />
              <h2>{unavailable ? 'No observations available' : 'Could not load the simulation'}</h2>
              <p>{error.message}</p>
              <button className="button" onClick={() => chooseDate(unavailable ? EXAMPLE_DATE : date)}>
                {unavailable ? 'Load demo day' : 'Try again'}
              </button>
            </> : date ? <>
              <LoaderCircle className="spinner" size={26} aria-hidden="true" />
              <h2>Loading historical day</h2>
              <p>Retrieving NOAA observations and forecast data.</p>
            </> : <>
              <CalendarDays size={26} aria-hidden="true" />
              <h2>Select a historical date</h2>
              <button className="button" onClick={() => chooseDate(EXAMPLE_DATE)}>Load demo day</button>
            </>}
          </section>
          <About />
        </>}
        <footer className="footer">
          <span>i4NS · Innovation for National Security</span>
          <span>NOAA NDBC · Station 44009</span>
        </footer>
      </main>
    </>
  )
}

function Summary({ day, frame }: { day: Day; frame: Frame }) {
  const statusClass = frame.path ? 'update' : frame.flag || frame.status === 'Deviation observed' ? 'warning' : 'neutral'
  const date = dateFormat.format(new Date(`${day.date}T12:00:00Z`))
  const missing = frame.status === 'Observations unavailable'

  return (
    <section className="overview" aria-label="Simulation overview">
      <div>
        <span className="overview-icon"><Waves size={18} aria-hidden="true" /></span>
        <div><span>Observation station</span><strong>NOAA Buoy {day.station}</strong><small>Off Delaware Bay</small></div>
      </div>
      <div>
        <span className="overview-icon"><CalendarDays size={18} aria-hidden="true" /></span>
        <div><span>Simulation date</span><strong>{date}</strong><small>{day.timezone}</small></div>
      </div>
      <div>
        <span className="overview-icon"><Clock3 size={18} aria-hidden="true" /></span>
        <div><span>Forecast status</span><strong className={`status-text ${statusClass}`}><i />{frame.status}</strong><small>
          {frame.flag ? `${hourLabel(frame.flag.time)} ET · ${variableList(frame.flag.variables)}`
            : missing ? 'No forecast comparison for this hour'
            : frame.current.hour === day.hours.at(-1)?.hour ? 'No deviation confirmed today'
            : 'No confirmed deviation yet'}
        </small></div>
      </div>
    </section>
  )
}

function Simulation({ day }: { day: Day }) {
  const playback = usePlayback(day.hours.length - 1)
  const [variable, setVariable] = useState<Variable>('wind')
  const frame = getFrame(day, playback.index)
  return <>
    <Summary day={day} frame={frame} />
    <Playback day={day} frame={frame} playback={playback} />
    <AlertDetails day={day} frame={frame} />
    <Measurements day={day} frame={frame} variable={variable} onSelect={setVariable} />
    <div className="analysis-grid">
      <ForecastChart day={day} frame={frame} variable={variable} />
      <ActivityLog day={day} frame={frame} onSelect={playback.select} />
    </div>
    <NeuralForecast day={day} frame={frame} />
    <About day={day} />
  </>
}
