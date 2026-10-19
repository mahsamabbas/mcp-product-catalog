import { describe, expect, it } from "vitest";
import { buildHistory, createEpoch, removeMessage } from "./session";
import type { ThreadMessage } from "../types";

describe("session epoch", () => {
  it("marks in-flight work stale after clear (bump)", () => {
    const epoch = createEpoch();
    const token = epoch.current(); // request starts
    expect(epoch.isCurrent(token)).toBe(true);
    epoch.bump(); // user clears chat while busy
    expect(epoch.isCurrent(token)).toBe(false); // late response must be dropped
    expect(epoch.isCurrent(epoch.current())).toBe(true);
  });

  it("late response is discarded and thread stays empty", () => {
    const epoch = createEpoch();
    let messages: ThreadMessage[] = [{ id: "m1", kind: "user", content: "hi" }];
    const token = epoch.current();
    // clear
    epoch.bump();
    messages = [];
    // late resolve
    if (epoch.isCurrent(token)) {
      messages = [...messages, { id: "m2", kind: "assistant", content: "late" }];
    }
    expect(messages).toEqual([]);
  });
});

describe("history", () => {
  const msgs: ThreadMessage[] = [
    { id: "1", kind: "user", content: "a" },
    { id: "2", kind: "tools", events: [] },
    { id: "3", kind: "assistant", content: "b" },
    { id: "4", kind: "user", content: "pending" },
  ];
  it("excludes tool groups", () => {
    expect(buildHistory(msgs)).toEqual([
      { role: "user", content: "a" },
      { role: "assistant", content: "b" },
      { role: "user", content: "pending" },
    ]);
  });
  it("failed send leaves no orphan user turn", () => {
    expect(buildHistory(removeMessage(msgs, "4"))).toEqual([
      { role: "user", content: "a" },
      { role: "assistant", content: "b" },
    ]);
  });
});
