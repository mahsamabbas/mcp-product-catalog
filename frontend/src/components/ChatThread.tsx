import { useEffect, useRef } from "react";
import type { ThreadMessage } from "../types";
import { SuggestionChips } from "./SuggestionChips";
import { ToolCard } from "./ToolCard";

interface Props {
  messages: ThreadMessage[];
  busy: boolean;
  error: string | null;
  onPick: (text: string) => void;
}

export function ChatThread({ messages, busy, error, onPick }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, busy, error]);

  if (messages.length === 0 && !busy) {
    return (
      <section className="cp-thread cp-thread--empty">
        <div className="cp-empty">
          <h2>Ask the catalog.</h2>
          <p>Every answer shows the tool calls behind it.</p>
          <SuggestionChips onPick={onPick} disabled={busy} />
          {error && (
            <p className="cp-banner" role="alert">
              {error}
            </p>
          )}
        </div>
      </section>
    );
  }

  return (
    <section className="cp-thread" aria-live="polite">
      {messages.map((m) => {
        if (m.kind === "tools") {
          return (
            <div key={m.id} className="cp-tools">
              {m.events.map((e, i) => (
                <ToolCard key={i} event={e} />
              ))}
            </div>
          );
        }
        return (
          <div key={m.id} className={`cp-bubble cp-bubble--${m.kind}`}>
            {m.content}
          </div>
        );
      })}
      {busy && (
        <div className="cp-bubble cp-bubble--assistant cp-thinking">
          Working the catalog<span>.</span>
          <span>.</span>
          <span>.</span>
        </div>
      )}
      {error && (
        <p className="cp-banner" role="alert">
          {error}
        </p>
      )}
      <div ref={endRef} />
    </section>
  );
}
