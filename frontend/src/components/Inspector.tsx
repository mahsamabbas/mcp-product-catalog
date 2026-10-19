import { useEffect, useRef, type KeyboardEvent } from "react";
import type { ToolTraceEvent } from "../types";
import { formatMs } from "../lib/format";
import { argsLine, resultSummary, toolLabel } from "../lib/tools";

interface Props {
  events: ToolTraceEvent[];
  productCount: number | null;
  open: boolean;
  /** True when the inspector is an off-canvas drawer (narrow viewport). */
  isDrawer: boolean;
  onClose: () => void;
}

const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export function Inspector({ events, productCount, open, isDrawer, onClose }: Props) {
  const lastRowRef = useRef<HTMLLIElement>(null);
  const asideRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const hidden = isDrawer && !open;

  useEffect(() => {
    lastRowRef.current?.scrollIntoView({ block: "nearest" });
  }, [events.length]);

  // Drawer open: move focus in, Escape closes.
  useEffect(() => {
    if (!(isDrawer && open)) return;
    closeRef.current?.focus();
    function onKey(e: globalThis.KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isDrawer, open, onClose]);

  // Light focus trap while the drawer is open.
  function trap(e: KeyboardEvent) {
    if (!(isDrawer && open) || e.key !== "Tab") return;
    const nodes = asideRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE);
    if (!nodes || nodes.length === 0) return;
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  return (
    <>
      <div
        className={`cp-scrim ${open ? "cp-scrim--open" : ""}`}
        onClick={onClose}
        aria-hidden
      />
      <aside
        id="cp-inspector"
        ref={asideRef}
        className={`cp-inspector ${open ? "cp-inspector--open" : ""}`}
        aria-label="MCP Inspector"
        aria-hidden={hidden || undefined}
        inert={hidden}
        onKeyDown={trap}
      >
        <div className="cp-inspector-head">
          <div>
            <h2>MCP Inspector</h2>
            <p>
              {productCount === null ? "Catalog —" : `${productCount} products in catalog`}
            </p>
          </div>
          <button
            ref={closeRef}
            type="button"
            className="cp-btn-outline cp-close"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        {events.length === 0 ? (
          <p className="cp-inspector-empty">Tool calls will land here.</p>
        ) : (
          <ol className="cp-timeline">
            {events.map((e, i) => (
              <li
                key={i}
                ref={i === events.length - 1 ? lastRowRef : undefined}
                className="cp-row"
              >
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
