import { Activity, CircleAlert, CircleDot, Radio, TriangleAlert, Waves } from 'lucide-react'
import { useLayoutEffect, useRef } from 'react'
import { buildEvents, hourLabel } from './simulation'
import type { Day, Frame } from './simulation'

const ICONS = { baseline: Radio, observation: Waves, deviation: TriangleAlert, alert: CircleAlert, update: Activity }

export function ActivityLog({ day, frame, onSelect }: {
  day: Day; frame: Frame; onSelect: (index: number) => void
}) {
  const events = buildEvents(day, frame)
  const scroller = useRef<HTMLOListElement>(null)

  useLayoutEffect(() => {
    const list = scroller.current
    if (list) list.scrollTop = list.scrollHeight
  }, [frame.current.hour])

  return (
    <aside className="panel activity-panel" aria-labelledby="activity-heading">
      <div className="panel-heading">
        <div>
          <h2 id="activity-heading">Activity log</h2>
          <p>Events through {hourLabel(frame.current.hour)} ET</p>
        </div>
        <CircleDot className="activity-indicator" size={17} aria-hidden="true" />
      </div>
      <ol className="events" ref={scroller}>
        {events.map(event => {
          const Icon = ICONS[event.kind]
          return <li key={`${event.time}-${event.kind}`}>
            <button className="event" onClick={() => onSelect(event.index)}>
              <span className={`event-icon ${event.kind}`}><Icon size={15} aria-hidden="true" /></span>
              <span className="event-text"><strong>{event.title}</strong><small>{event.detail}</small></span>
              <time dateTime={event.time}>{hourLabel(event.time)}</time>
            </button>
          </li>
        })}
      </ol>
    </aside>
  )
}
