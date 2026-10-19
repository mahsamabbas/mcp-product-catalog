import type { ToolTraceEvent } from "../types";
import { formatMs } from "../lib/format";
import { argsLine, prettyJson, resultSummary, toolLabel } from "../lib/tools";

export function ToolCard({ event }: { event: ToolTraceEvent }) {
  return (
    <article className={`cp-tool ${event.ok ? "" : "cp-tool--err"}`}>
      <div className="cp-tool-head">
        <span className="cp-badge">MCP</span>
        <strong>{toolLabel(event.name)}</strong>
        <span className="cp-ms">{formatMs(event.ms)}</span>
      </div>
      <code className="cp-args">{argsLine(event.args)}</code>
      <p className="cp-summary">{resultSummary(event)}</p>
      <details>
        <summary>Raw JSON</summary>
        <pre>
          {prettyJson({ args: event.args, result: event.result, error: event.error })}
        </pre>
      </details>
    </article>
  );
}
