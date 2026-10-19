import type { ToolTraceEvent } from "../types";

const LABELS: Record<string, string> = {
  search_products: "Search products",
  lookup_stock: "Lookup stock",
};

export function toolLabel(name: string): string {
  return LABELS[name] ?? name.replace(/_/g, " ");
}

export function argsLine(args: Record<string, unknown>): string {
  const parts = Object.entries(args).map(
    ([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`,
  );
  return parts.length ? parts.join(" · ") : "no args";
}

/** MCP results arrive either as a parsed object or a JSON string. */
export function parseResult(result: unknown): unknown {
  if (typeof result === "string") {
    try {
      return JSON.parse(result);
    } catch {
      return result;
    }
  }
  return result;
}

export function resultSummary(event: ToolTraceEvent): string {
  if (!event.ok) return event.error ?? "Tool call failed";
  const data = parseResult(event.result);
  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>;
    if (event.name === "search_products") {
      const n =
        typeof obj.count === "number"
          ? obj.count
          : Array.isArray(obj.results)
            ? obj.results.length
            : 0;
      return `${n} ${n === 1 ? "product" : "products"}`;
    }
    if (event.name === "lookup_stock") {
      if (obj.found === false) return "SKU not found";
      const qty = obj.quantity;
      const wh = obj.warehouse;
      const head = obj.in_stock === false ? "Out of stock" : `${qty} in stock`;
      return wh ? `${head} · ${String(wh)}` : head;
    }
  }
  return "Done";
}

export function prettyJson(value: unknown): string {
  return JSON.stringify(parseResult(value), null, 2) ?? "null";
}
