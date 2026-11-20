import { Activity, CircleAlert, Cloud, Droplets, Gauge, Thermometer, Waves, Wind } from 'lucide-react'
import { formatValue, hourLabel, LABELS, targetLabel, VARIABLES } from './simulation'
import type { Day, Frame, Variable } from './simulation'

const ICONS = { wind: Wind, temp: Thermometer, rh: Droplets, sea: Waves, pres: Gauge }

export function Measurements({ day, frame, variable, onSelect }: {
  day: Day; frame: Frame; variable: Variable; onSelect: (value: Variable) => void
}) {
  return (
    <section className="measurements" aria-labelledby="measurements-heading">
      <div className="section-heading">
        <h2 id="measurements-heading">Environmental measurements</h2>
        <p>Select a variable to change the chart.</p>
      </div>
      <div className="measurement-grid" role="group" aria-label="Chart variable">
        {VARIABLES.map(key => {
          const row = frame.current.vars[key]
          const unit = day.units[key]
          const difference = row.actual != null && row.forecast != null ? row.actual - row.forecast : null
          const source = frame.priorPath
          const prediction = source?.vars[key][frame.priorLead]
          const Icon = ICONS[key]
          const status = row.actual === null ? 'No observation'
            : row.forecast === null ? 'No baseline'
            : row.in_bounds === false ? 'Outside bounds' : 'Within bounds'

          return (
            <button key={key} className="panel measurement" aria-pressed={variable === key} onClick={() => onSelect(key)}>
              <span className="measure-name"><Icon size={17} aria-hidden="true" /> {LABELS[key]}</span>
              <span className="measure-observation">
                {formatValue(row.actual)} <small>{unit}</small>
              </span>
              <span className={`measure-status${row.in_bounds === false ? ' warning-text' : ''}`}>{status}</span>
              <span className="measure-comparison">
                <span><span>Baseline</span><strong>{formatValue(row.forecast, unit)}</strong></span>
                <span><span>Difference</span><strong>{difference !== null && difference >= 0.05 ? '+' : ''}
                  {formatValue(difference, unit === '%' ? 'pp' : unit)}</strong></span>
                {source && <span><span>Neural · {hourLabel(source.origin)}</span><strong>{formatValue(prediction, unit)}</strong></span>}
              </span>
            </button>
          )
        })}
      </div>
    </section>
  )
}

export function AlertDetails({ day, frame }: { day: Day; frame: Frame }) {
  const flag = frame.flag
  if (!flag) return null
  const flagRow = day.hours.find(row => row.hour === flag.time)
  return (
    <section className="panel alert-panel" aria-labelledby="alert-heading">
      <div className="alert-heading">
        <span className="alert-icon"><CircleAlert size={21} aria-hidden="true" /></span>
        <div>
          <h2 id="alert-heading">Forecast deviation detected</h2>
          <p>Confirmed at {hourLabel(flag.time)} ET after {day.bounds_rule.persist_hours} consecutive hours meeting the deviation criteria.</p>
        </div>
      </div>
      <ul className="alert-values">
        {flag.variables.map(variable => {
          const unit = day.units[variable]
          const range = flag.bounds[variable]
          return <li key={variable}>
            <strong>{LABELS[variable]}</strong>
            <span>Observed <b>{formatValue(flag.values[variable], unit)}</b></span>
            <span>Baseline <b>{formatValue(flagRow?.vars[variable].forecast, unit)}</b></span>
            {range && <span>Bounds <b>{formatValue(range[0])} to {formatValue(range[1], unit)}</b></span>}
          </li>
        })}
      </ul>
      {flag.variables.includes('wind') && <p className="alert-note">
        Wind also has a minimum-speed condition. The observed or baseline speed must reach it for a miss to count.
      </p>}
    </section>
  )
}

export function NeuralForecast({ day, frame }: { day: Day; frame: Frame }) {
  const path = frame.path
  const baseline = new Map(day.hours.map(row => [row.hour, row.vars]))
  return (
    <section className="panel neural-panel" aria-labelledby="neural-heading">
      <div className="panel-heading">
        <div>
          <h2 id="neural-heading"><Activity size={19} aria-hidden="true" /> Neural forecast updates</h2>
          <p>{path ? `Active since ${hourLabel(frame.paths[0].origin)} ET · Latest issue ${hourLabel(path.origin)} ET`
            : frame.flag ? 'Deviation confirmed. A model forecast is unavailable at this hour.'
            : 'A new forecast can be issued after the system confirms a deviation.'}</p>
        </div>
        {path && <span className="mini-label">Next {path.hours.length} hours</span>}
      </div>
      {path && <>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Neural forecast comparison table">
          <table>
            <thead><tr>
              <th scope="col">Target</th>
              {VARIABLES.map(variable => <th scope="col" key={variable}>{LABELS[variable]} <span>({day.units[variable]})</span></th>)}
            </tr></thead>
            <tbody>{path.hours.map((time, lead) => <tr key={time}>
              <th scope="row">{targetLabel(time, day.date)} <span>+{lead + 1}h</span></th>
              {VARIABLES.map(variable => <td key={variable}>
                <strong>{formatValue(path.vars[variable][lead])}</strong>
                <span>Baseline {formatValue(baseline.get(time)?.[variable].forecast)}</span>
              </td>)}
            </tr>)}</tbody>
          </table>
        </div>
        {path.hours.some(time => !baseline.has(time)) &&
          <p className="chart-caption">The displayed baseline ends at {hourLabel(day.hours[day.hours.length - 1].hour)}. The model horizon continues into the following day when applicable.</p>}
      </>}
    </section>
  )
}

export function About({ day }: { day?: Day }) {
  return (
    <details className="panel about">
      <summary><Cloud size={18} aria-hidden="true" /> About this research prototype</summary>
      <div className="about-body">
        <p><strong>Observations.</strong> The simulation replays historical hourly NOAA National Data Buoy Center measurements from station 44009 off Delaware Bay. Relative humidity is derived from air temperature and dew point.</p>
        <p><strong>Baseline and alert.</strong> The stand-in forecast starts from the 08:00 observation and follows the typical monthly hourly pattern calculated from 2023 buoy data. The system confirms a deviation when the same variable meets its rule for {day?.bounds_rule.persist_hours ?? 2} consecutive hours. Wind has a minimum-speed condition, and the other bounds are empirical.</p>
        {day && <p className="muted">Threshold source · {day.bounds_rule.source}. {day.bounds_rule.wind_note}.</p>}
        <p><strong>Model and scope.</strong> A PyTorch neural network uses six hours of recent observations and the baseline to forecast the next one to six hours of the five environmental variables. The dashboard simulates a daily forecast using archived data. Live operations are outside its scope. Radar detection range, propagation loss, and coverage are outside the model’s scope. The long-term research goal is more responsive radar-performance estimation as atmospheric conditions change.</p>
      </div>
    </details>
  )
}
