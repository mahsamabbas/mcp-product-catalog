import type { ToolTraceEvent } from "../types";
import { formatMs } from "../lib/format";
import { argsLine, resultSummary, toolLabel } from "../lib/tools";

interface Props {
  events: ToolTraceEvent[];
  productCount: number | null;
  open: boolean;
  onClose: () => void;
}

export function Inspector({ events, productCount, open, onClose }: Props) {
  return (
    <>
      <div
        className={`cp-scrim ${open ? "cp-scrim--open" : ""}`}
        onClick={onClose}
        aria-hidden
      />
      <aside className={`cp-inspector ${open ? "cp-inspector--open" : ""}`}>
        <div className="cp-inspector-head">
          <div>
            <h2>MCP Inspector</h2>
            <p>
              {productCount === null ? "Catalog —" : `${productCount} products in catalog`}
            </p>
          </div>
          <button type="button" className="cp-btn-outline cp-close" onClick={onClose}>
            Close
          </button>
        </div>
        {events.length === 0 ? (
          <p className="cp-inspector-empty">Tool calls will land here.</p>
        ) : (
          <ol className="cp-timeline">
            {events.map((e, i) => (
              <li key={i} className="cp-row">
                <span className="cp-row-idx">{String(i + 1).padStart(2, "0")}</span>
                <div>
                  <div className="cp-row-top">
                    <strong>{toolLabel(e.name)}</strong>
                    <span className={e.ok ? "cp-ok" : "cp-fail"}>
                      {e.ok ? "ok" : "error"} · {formatMs(e.ms)}
                    </span>
                  </div>
                  <code>{argsLine(e.args)}</code>
                  <p>{resultSummary(e)}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </aside>
    </>
  );
}
