import { Pause, Play, RotateCcw, SkipBack, SkipForward } from 'lucide-react'
import { useEffect, useState } from 'react'
import { hourLabel } from './simulation'
import type { Day, Frame } from './simulation'

export function usePlayback(max: number) {
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)

  useEffect(() => {
    if (!playing || index >= max) return
    const timer = window.setTimeout(() => {
      setIndex(index + 1)
      if (index + 1 === max) setPlaying(false)
    }, 1000 / speed)
    return () => window.clearTimeout(timer)
  }, [index, max, playing, speed])

  function select(next: number) {
    setPlaying(false)
    setIndex(Math.max(0, Math.min(max, next)))
  }

  function toggle() {
    if (max === 0) return
    if (!playing && index === max) setIndex(0)
    setPlaying(!playing)
  }

  return { index, playing, speed, setSpeed, select, toggle }
}

export function Playback({ day, frame, playback }: {
  day: Day; frame: Frame; playback: ReturnType<typeof usePlayback>
}) {
  const { index, playing, speed, setSpeed, select, toggle } = playback
  const max = day.hours.length - 1
  const alertIndex = frame.flag ? day.hours.findIndex(row => row.hour === frame.flag?.time) : -1
  const time = hourLabel(frame.current.hour)

  return (
    <section className="panel playback" aria-labelledby="playback-heading">
      <div className="panel-heading playback-heading">
        <div>
          <h2 id="playback-heading">Simulation timeline</h2>
          <p>Replay hourly observations in Eastern time.</p>
        </div>
        <div className="playback-clock">
          <time>{time}</time><span>{index === max ? 'End of day' : 'Simulation time'}</span>
        </div>
      </div>
      <div className="slider-shell">
        <input
          type="range" min={0} max={max} value={index}
          aria-label="Simulation hour" aria-valuetext={time}
          style={{ '--progress': `${max ? index / max * 100 : 0}%` } as React.CSSProperties}
          onChange={event => select(Number(event.target.value))}
        />
        <div className="slider-ticks" aria-hidden="true">
          {day.hours.filter((_, i) => i === max || i % Math.ceil(max / 4 || 1) === 0)
            .map(row => <span key={row.hour}>{hourLabel(row.hour)}</span>)}
        </div>
      </div>
      <div className="playback-controls">
        <div className="button-group">
          <button className="button primary play" onClick={toggle} disabled={max === 0}>
            {playing ? <Pause size={16} /> : <Play size={16} />}
            {playing ? 'Pause' : 'Play'}
          </button>
          <button className="button icon-button" title="Step backward" aria-label="Step backward" disabled={index === 0} onClick={() => select(index - 1)}>
            <SkipBack size={16} />
          </button>
          <button className="button icon-button" title="Step forward" aria-label="Step forward" disabled={index === max} onClick={() => select(index + 1)}>
            <SkipForward size={16} />
          </button>
          <button className="button reset" onClick={() => select(0)}>
            <RotateCcw size={15} /> Reset
          </button>
        </div>
        <div className="button-group">
          {alertIndex >= 0 && <button className="button alert-link" onClick={() => select(alertIndex)}>Jump to alert</button>}
          <label className="speed">Speed
            <select aria-label="Playback speed" value={speed} onChange={event => setSpeed(Number(event.target.value))}>
              <option value={1}>1×</option><option value={2}>2×</option><option value={4}>4×</option>
            </select>
          </label>
        </div>
      </div>
    </section>
  )
}
