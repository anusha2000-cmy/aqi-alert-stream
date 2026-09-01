import { categoryClass, formatObservedTime, formatPolledTime, pollKey } from "../lib/format";
import type { AQIReading } from "../types";

interface ReadingsTableProps {
  readings: AQIReading[];
}

export function ReadingsTable({ readings }: ReadingsTableProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Last 10 readings</h2>
      </div>
      {readings.length === 0 ? (
        <p className="empty-state">No readings yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>AQI</th>
                <th>Category</th>
                <th>PM2.5</th>
                <th>Observed</th>
                <th>Polled</th>
              </tr>
            </thead>
            <tbody>
              {readings.map((reading) => (
                <tr key={pollKey(reading)}>
                  <td>{reading.aqi}</td>
                  <td>
                    <span className={`category-badge ${categoryClass(reading.category)}`}>
                      {reading.category}
                    </span>
                  </td>
                  <td>{reading.pm25 ?? "—"}</td>
                  <td>{formatObservedTime(reading.timestamp)}</td>
                  <td>{formatPolledTime(reading.polled_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
