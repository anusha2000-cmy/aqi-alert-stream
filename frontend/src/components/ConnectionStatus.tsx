import type { ConnectionState } from "../types";

interface ConnectionStatusProps {
  state: ConnectionState;
  error: string | null;
}

export function ConnectionStatus({ state, error }: ConnectionStatusProps) {
  return (
    <div className={`connection connection-${state}`}>
      <span className="connection-dot" />
      <span>{state}</span>
      {error ? <span className="connection-error">{error}</span> : null}
    </div>
  );
}
