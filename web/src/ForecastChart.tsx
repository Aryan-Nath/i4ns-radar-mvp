import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { buildChartRows, formatValue, LABELS, targetLabel } from './simulation'
import type { Day, Frame, Variable } from './simulation'

const SERIES = [
  ['actual', 'NOAA observations'],
  ['baseline', 'Baseline forecast'],
  ['band', 'Forecast bounds'],
  ['update', 'Neural update'],
  ['alert', 'Confirmed deviation'],
] as const

export function ForecastChart({ day, frame, variable }: { day: Day; frame: Frame; variable: Variable }) {
  const unit = day.units[variable]
  const rows = buildChartRows(day, frame, variable)
  const tickIntervals = Math.min(4, rows.length - 1)
  const ticks = tickIntervals
    ? Array.from({ length: tickIntervals + 1 }, (_, i) => rows[Math.round(i * (rows.length - 1) / tickIntervals)].time)
    : [rows[0].time]
  const values = new Map(rows.map(row => [row.time, row]))
  const selectedLabel = targetLabel(frame.current.hour, day.date)
  const last = rows[rows.length - 1]
  const horizon = last.time.slice(0, 10) !== day.date ? ' · +1d marks the following day' : ''

  return (
    <section className="panel chart-panel" aria-labelledby="chart-heading">
      <div className="panel-heading chart-heading">
        <div>
          <h2 id="chart-heading">Forecast comparison</h2>
          <p>{LABELS[variable]} <span aria-hidden="true">·</span> {unit}</p>
        </div>
        <span className="mini-label">At {selectedLabel}</span>
      </div>
      <ul className="legend" aria-label="Chart legend">
        {SERIES.map(([key, label]) => <li key={key}><span className={`swatch ${key}`} />{label}</li>)}
      </ul>
      <div className="chart-plot" aria-label={`${LABELS[variable]} forecast and observations in ${unit}`}>
        <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 680, height: 290 }}>
          <ComposedChart data={rows} margin={{ top: 13, right: 12, bottom: 2, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--grid)" strokeDasharray="4 4" />
            <XAxis dataKey="time" ticks={ticks} interval="preserveStartEnd" minTickGap={10}
              tickFormatter={time => targetLabel(time, day.date)} tickLine={false}
              axisLine={{ stroke: 'var(--grid)' }} padding={{ left: 7, right: horizon ? 25 : 13 }}
              tick={{ fill: 'var(--muted)', fontSize: 11 }} tickMargin={9} />
            <YAxis width={48} tickLine={false} axisLine={false}
              tick={{ fill: 'var(--muted)', fontSize: 11 }} tickCount={6}
              domain={['auto', 'auto']} />
            <Tooltip cursor={{ stroke: 'var(--muted)', strokeDasharray: '3 4' }}
              content={({ active, label }) => {
                if (!active || typeof label !== 'string') return null
                const row = values.get(label)
                if (!row) return null
                return <div className="chart-tooltip">
                  <strong>{targetLabel(label, day.date)} · {LABELS[variable]}</strong>
                  <dl>
                    <div><dt>Observation</dt><dd>{formatValue(row.actual, unit)}</dd></div>
                    <div><dt>Baseline</dt><dd>{formatValue(row.baseline, unit)}</dd></div>
                    <div><dt>Bounds</dt><dd>{row.band ? `${formatValue(row.band[0])} to ${formatValue(row.band[1], unit)}` : '—'}</dd></div>
                    <div><dt>Neural update</dt><dd>{formatValue(row.update, unit)}</dd></div>
                  </dl>
                  {frame.flag?.time === label && <span className="warning-text">Deviation confirmed</span>}
                  {label > frame.current.hour && label.slice(0, 10) === day.date && <span>Observation pending</span>}
                </div>
              }} />
            <Area dataKey="band" stroke="none" fill="var(--band)" isAnimationActive={false} />
            <Line dataKey="baseline" stroke="var(--baseline)" strokeDasharray="6 5" strokeWidth={1.6}
              dot={false} activeDot={false} isAnimationActive={false} />
            <ReferenceLine x={frame.current.hour} stroke="var(--muted)" strokeDasharray="2 5" />
            {frame.flag && <ReferenceLine x={frame.flag.time} stroke="var(--alert)" strokeDasharray="5 4" strokeWidth={2} />}
            <Line dataKey="actual" stroke="var(--observed)" strokeWidth={2.2}
              dot={{ r: 3, fill: 'var(--observed)', strokeWidth: 0 }} isAnimationActive={false} />
            <Line dataKey="update" stroke="var(--cyan)" strokeWidth={2.5}
              dot={{ r: 3, fill: 'var(--cyan)', strokeWidth: 0 }} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-caption">Local time ({day.timezone}){horizon}</p>
    </section>
  )
}
