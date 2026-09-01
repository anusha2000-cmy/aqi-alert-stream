export function pollKey(reading: {
  aqi: number;
  timestamp: string;
  polled_at: string | null;
}): string {
  return reading.polled_at ?? `${reading.aqi}|${reading.timestamp}`;
}

export function formatObservedTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatPolledTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

/** @deprecated Use formatObservedTime or formatPolledTime */
export function formatTime(value: string | null | undefined): string {
  return formatPolledTime(value);
}

export function formatPollAgeSeconds(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  const seconds = Math.max(
    0,
    Math.floor((Date.now() - new Date(value).getTime()) / 1000),
  );

  if (seconds < 60) {
    return `${seconds}s ago`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}m ${remainder}s ago`;
}

export function categoryClass(category: string): string {
  switch (category) {
    case "Good":
      return "category-good";
    case "Moderate":
      return "category-moderate";
    case "Unhealthy for Sensitive Groups":
      return "category-sensitive";
    case "Unhealthy":
      return "category-unhealthy";
    case "Very Unhealthy":
      return "category-very-unhealthy";
    case "Hazardous":
      return "category-hazardous";
    default:
      return "category-unknown";
  }
}
