import { StatusPill } from "./StatusPill";

interface Props {
  live: boolean | null;
  canClear: boolean;
  onClear: () => void;
  onToggleInspector: () => void;
}

export function BrandHeader({ live, canClear, onClear, onToggleInspector }: Props) {
  return (
    <header className="cp-header">
      <div className="cp-brand">
        <h1>CatalogPilot</h1>
        <p>Ask the catalog. Watch the tools.</p>
      </div>
      <div className="cp-header-actions">
        <StatusPill live={live} />
        <button
          type="button"
          className="cp-btn-outline cp-inspector-toggle"
          onClick={onToggleInspector}
        >
          Inspector
        </button>
        <button
          type="button"
          className="cp-btn-outline"
          onClick={onClear}
          disabled={!canClear}
        >
          Clear chat
        </button>
      </div>
    </header>
  );
}
