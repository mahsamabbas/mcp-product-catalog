import { describe, expect, it } from "vitest";
import { argsLine, resultSummary, toolLabel } from "./tools";
import type { ToolTraceEvent } from "../types";

const base: ToolTraceEvent = {
  name: "search_products",
  args: {},
  result: null,
  ms: 10,
  ok: true,
  error: null,
};

describe("tool helpers", () => {
  it("labels tools", () => {
    expect(toolLabel("lookup_stock")).toBe("Lookup stock");
  });
  it("formats args", () => {
    expect(argsLine({ query: "earbuds", limit: 5 })).toBe("query=earbuds · limit=5");
    expect(argsLine({})).toBe("no args");
  });
  it("summarizes search from JSON string", () => {
    const ev = { ...base, result: JSON.stringify({ results: [], count: 3 }) };
    expect(resultSummary(ev)).toBe("3 products");
  });
  it("summarizes stock", () => {
    const ev = {
      ...base,
      name: "lookup_stock",
      result: { found: true, in_stock: true, quantity: 12, warehouse: "Austin" },
    };
    expect(resultSummary(ev)).toBe("12 in stock · Austin");
  });
  it("surfaces errors", () => {
    expect(resultSummary({ ...base, ok: false, error: "boom" })).toBe("boom");
  });
  it("guards lookup_stock without quantity", () => {
    const e = { ...base, name: "lookup_stock", result: { found: true, in_stock: true } };
    expect(resultSummary(e)).toBe("In stock");
  });
});
