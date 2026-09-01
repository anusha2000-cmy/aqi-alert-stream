import type { CityLocation } from "../types";

interface CityInputProps {
  city: string;
  subscribedCity: string;
  location: CityLocation | null;
  onCityChange: (city: string) => void;
  onSubscribe: () => void;
}

function formatLocation(
  location: CityLocation | null,
  subscribedCity: string,
): string {
  if (location) {
    const parts = [location.name, location.region, location.country].filter(
      Boolean,
    );
    return parts.join(", ");
  }

  if (subscribedCity) {
    return subscribedCity;
  }

  return "No city selected";
}

export function CityInput({
  city,
  subscribedCity,
  location,
  onCityChange,
  onSubscribe,
}: CityInputProps) {
  const trimmed = city.trim();
  const canSubscribe = trimmed.length > 0 && trimmed !== subscribedCity;

  return (
    <form
      className="city-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSubscribe) {
          onSubscribe();
        }
      }}
    >
      <label className="city-input">
        <span>City</span>
        <input
          type="text"
          value={city}
          placeholder="e.g. Oakland, Seattle, London"
          onChange={(event) => onCityChange(event.target.value)}
        />
      </label>
      <button type="submit" disabled={!canSubscribe}>
        Subscribe
      </button>
      <p className="city-meta">
        Watching: <strong>{formatLocation(location, subscribedCity)}</strong>
      </p>
    </form>
  );
}
