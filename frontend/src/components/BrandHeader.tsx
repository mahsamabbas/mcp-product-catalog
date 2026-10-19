import type { Ref } from "react";
import { StatusPill } from "./StatusPill";

interface Props {
  live: boolean | null;
  canClear: boolean;
  onClear: () => void;
  onToggleInspector: () => void;
  inspectorOpen: boolean;
  toggleRef?: Ref<HTMLButtonElement>;
}

export function BrandHeader({
  live,
  canClear,
  onClear,
  onToggleInspector,
  inspectorOpen,
  toggleRef,
}: Props) {
  return (
    <header className="cp-header">
      <div className="cp-brand">
        <h1>CatalogPilot</h1>
        <p>Ask the catalog. Watch the tools.</p>
      </div>
      <div className="cp-header-actions">
        <StatusPill live={live} />
        <button
          ref={toggleRef}
          type="button"
          className="cp-btn-outline cp-inspector-toggle"
          aria-expanded={inspectorOpen}
          aria-controls="cp-inspector"
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
