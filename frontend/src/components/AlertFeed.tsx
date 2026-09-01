import { categoryClass, formatPolledTime } from "../lib/format";
import type { Alert } from "../types";

interface AlertFeedProps {
  alerts: Alert[];
}

export function AlertFeed({ alerts }: AlertFeedProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Alert feed</h2>
      </div>
      {alerts.length === 0 ? (
        <p className="empty-state">No alerts yet.</p>
      ) : (
        <ul className="alert-feed">
          {alerts.map((alert) => (
            <li key={alert.id} className={`alert-item alert-${alert.level}`}>
              <div className="alert-item-header">
                <span className={`alert-level alert-${alert.level}`}>
                  {alert.level}
                </span>
                <span className="alert-time">{formatPolledTime(alert.timestamp)}</span>
              </div>
              <p className="alert-message">{alert.message}</p>
              <span className={`category-badge ${categoryClass(alert.category)}`}>
                AQI {alert.aqi} · {alert.category}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
