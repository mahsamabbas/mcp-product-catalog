import type { HistoryMessage, ThreadMessage } from "../types";

/**
 * Session epoch: bump on "Clear chat" so in-flight requests started under an
 * older epoch can detect they are stale and must not touch state.
 */
export interface Epoch {
  current: () => number;
  bump: () => number;
  isCurrent: (token: number) => boolean;
}

export function createEpoch(): Epoch {
  let n = 0;
  return {
    current: () => n,
    bump: () => ++n,
    isCurrent: (token) => token === n,
  };
}

/** Chat history sent to the API: user/assistant turns only. */
export function buildHistory(messages: ThreadMessage[]): HistoryMessage[] {
  const out: HistoryMessage[] = [];
  for (const m of messages) {
    if (m.kind === "user" || m.kind === "assistant") {
      out.push({ role: m.kind, content: m.content });
    }
  }
  return out;
}

/** Drop the optimistic user bubble for a failed send. */
export function removeMessage(messages: ThreadMessage[], id: string): ThreadMessage[] {
  return messages.filter((m) => m.id !== id);
}
