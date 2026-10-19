import { describe, expect, it } from "vitest";

import { formatMoney, formatMs } from "./format";

describe("formatMoney", () => {
  it("formats USD", () => {
    expect(formatMoney(49, "USD")).toMatch(/\$49/);
  });
});

describe("formatMs", () => {
  it("shows ms", () => {
    expect(formatMs(12)).toBe("12 ms");
  });
});
