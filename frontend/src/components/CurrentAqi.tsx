import { useEffect, useState } from "react";
import { categoryClass, formatObservedTime, formatPollAgeSeconds, formatPolledTime } from "../lib/format";
import type { AQIReading } from "../types";

interface CurrentAqiProps {
  reading: AQIReading | null;
}

function useNowTick(active: boolean) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!active) {
      return;
    }

    const timer = window.setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => window.clearInterval(timer);
  }, [active]);

  return now;
}

export function CurrentAqi({ reading }: CurrentAqiProps) {
  useNowTick(Boolean(reading?.polled_at));

  if (!reading) {
    return (
      <section className="panel current-aqi">
        <p className="eyebrow">Current AQI</p>
        <p className="empty-state">Waiting for first reading…</p>
      </section>
    );
  }

  return (
    <section className={`panel current-aqi ${categoryClass(reading.category)}`}>
      <p className="eyebrow">{reading.city}</p>
      <div className="current-aqi-value">{reading.aqi}</div>
      <div className={`category-badge ${categoryClass(reading.category)}`}>
        {reading.category}
      </div>
      <dl className="meta-grid">
        <div>
          <dt>PM2.5</dt>
          <dd>{reading.pm25 ?? "—"}</dd>
        </div>
        <div>
          <dt>Observed</dt>
          <dd>{formatObservedTime(reading.timestamp)}</dd>
        </div>
        <div>
          <dt>Polled</dt>
          <dd>{formatPolledTime(reading.polled_at)}</dd>
        </div>
        <div>
          <dt>Last poll</dt>
          <dd>{formatPollAgeSeconds(reading.polled_at)}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{reading.stale ? "Stale" : "Live"}</dd>
        </div>
      </dl>
    </section>
  );
}
