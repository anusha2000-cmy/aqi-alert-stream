import { useState } from "react";
import { AlertFeed } from "./components/AlertFeed";
import { CityInput } from "./components/CityInput";
import { ConnectionStatus } from "./components/ConnectionStatus";
import { CurrentAqi } from "./components/CurrentAqi";
import { ReadingsTable } from "./components/ReadingsTable";
import { loadSavedCity, useAqiSocket } from "./hooks/useAqiSocket";

export default function App() {
  const savedCity = loadSavedCity();
  const [cityInput, setCityInput] = useState(savedCity);
  const [subscribedCity, setSubscribedCity] = useState(savedCity);
  const { connectionState, error, location, current, history, alerts } =
    useAqiSocket(subscribedCity);

  return (
    <main className="app">
      <header className="app-header">
        <div>
          <p className="eyebrow">AQI Alert Stream</p>
          <h1>Live air quality dashboard</h1>
        </div>
        <div className="header-controls">
          <CityInput
            city={cityInput}
            subscribedCity={subscribedCity}
            location={location}
            onCityChange={setCityInput}
            onSubscribe={() => setSubscribedCity(cityInput.trim())}
          />
          <ConnectionStatus state={connectionState} error={error} />
        </div>
      </header>

      <div className="dashboard-grid">
        <CurrentAqi reading={current} />
        <ReadingsTable readings={history} />
        <AlertFeed alerts={alerts} />
      </div>
    </main>
  );
}
