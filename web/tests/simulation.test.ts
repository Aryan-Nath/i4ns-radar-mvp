import assert from 'node:assert/strict'
import test from 'node:test'
import { buildChartRows, buildEvents, getFrame, shiftDate, targetLabel, VARIABLES } from '../src/simulation.ts'
import type { Day } from '../src/simulation.ts'

const day = '2024-12-04'
const [first, miss, alert, end] = ['17:00', '18:00', '19:00', '20:00'].map(hour => `${day}T${hour}`)
const targets = [end, '2024-12-04T21:00', '2024-12-04T22:00', '2024-12-04T23:00', '2024-12-05T00:00', '2024-12-05T01:00']
const vars = <T,>(build: (variable: (typeof VARIABLES)[number]) => T) =>
  Object.fromEntries(VARIABLES.map(key => [key, build(key)])) as Record<(typeof VARIABLES)[number], T>

const example: Day = {
  date: day, station: '44009', timezone: 'America/New_York',
  units: { wind: 'mph', temp: '°C', rh: '%', sea: '°C', pres: 'hPa' },
  bounds_rule: { source: 'test', persist_hours: 2, half_width: vars(() => 10), wind_note: 'test' },
  hours: [first, miss, alert, end].map((hour, index) => ({
    hour,
    vars: vars(key => ({
      forecast: 20, lo: 10, hi: 30,
      actual: key === 'wind' ? [21, 34, 35, 37][index] : null,
      in_bounds: key === 'wind' ? index === 0 : null,
      nn_updated: 999,
    })),
  })),
  flag: { time: alert, variables: ['wind'], values: { wind: 35 }, bounds: { wind: [10, 30] } },
  nn_paths: {
    [alert]: { hours: targets, vars: vars(() => [36, 35, 34, 33, 32, 31]) },
  },
}

test('before confirmation, chart and event log reveal only elapsed observations and no update', () => {
  const frame = getFrame(example, 1)
  assert.equal(frame.status, 'Deviation observed')
  assert.equal(frame.flag, null)
  assert.equal(frame.path, undefined)
  assert.deepEqual(buildChartRows(example, frame, 'wind').map(row => row.actual), [21, 34, null, null])
  assert.ok(buildChartRows(example, frame, 'wind').every(row => row.update === null))
  assert.ok(buildEvents(example, frame).every(event => event.time <= miss && event.kind !== 'alert'))
})

test('confirmation exposes the model issuance and all six targets, including next day', () => {
  const frame = getFrame(example, 2)
  const rows = buildChartRows(example, frame, 'wind')
  assert.equal(frame.flag?.time, alert)
  assert.equal(frame.path?.origin, alert)
  assert.deepEqual(rows.filter(row => row.update !== null).map(row => row.time), targets)
  assert.equal(rows.at(-1)?.baseline, null)
  assert.equal(rows.at(-1)?.actual, null)
  assert.equal(targetLabel(targets[5], day), '01:00 +1d')
  assert.deepEqual(buildEvents(example, frame).slice(-2).map(event => event.kind), ['alert', 'update'])
})

test('the last issued path stays visible when no new update exists, and can verify a target hour', () => {
  const frame = getFrame(example, 3)
  assert.equal(frame.path?.origin, alert)
  assert.equal(frame.priorPath?.vars.wind[frame.priorLead], 36)
  assert.equal(buildChartRows(example, frame, 'wind').find(row => row.time === end)?.actual, 37)
})

test('a neutral day and missing measurements have no fabricated series or alert events', () => {
  const neutral = { ...example, flag: null, nn_paths: {} }
  const frame = getFrame(neutral, 0)
  assert.equal(frame.status, 'Within bounds')
  assert.ok(buildChartRows(neutral, frame, 'sea').every(row => row.actual === null))
  assert.deepEqual(buildEvents(neutral, frame).map(event => event.kind), ['baseline', 'observation'])
  assert.equal(shiftDate('2024-03-01', -1), '2024-02-29')
  assert.equal(shiftDate('', 1), null)
  assert.equal(shiftDate('9999-12-31', 1), null)
})
