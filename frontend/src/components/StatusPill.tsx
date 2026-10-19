interface Props {
  live: boolean | null;
}

export function StatusPill({ live }: Props) {
  if (live === null) {
    return <span className="cp-status cp-status--idle">Checking…</span>;
  }
  return live ? (
    <span className="cp-status cp-status--live" role="status">
      <i aria-hidden /> MCP live
    </span>
  ) : (
    <span className="cp-status cp-status--off" role="status">
      <i aria-hidden /> offline
    </span>
  );
}
