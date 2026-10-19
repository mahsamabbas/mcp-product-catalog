import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getCatalogSummary, getHealth, postChat } from "./api";
import { BrandHeader } from "./components/BrandHeader";
import { ChatThread } from "./components/ChatThread";
import { Composer } from "./components/Composer";
import { Inspector } from "./components/Inspector";
import type {
  HealthResponse,
  HistoryMessage,
  ThreadMessage,
  ToolTraceEvent,
} from "./types";

function App() {
  const [messages, setMessages] = useState<ThreadMessage[]>([]);
  const [inspectorEvents, setInspectorEvents] = useState<ToolTraceEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null | false>(null);
  const [productCount, setProductCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drawer, setDrawer] = useState(false);
  const seq = useRef(0);
  const nextId = () => `m${++seq.current}`;

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(false));
    getCatalogSummary()
      .then((s) => setProductCount(s.product_count))
      .catch(() => setProductCount(null));
  }, []);

  const send = useCallback(
    async (text: string) => {
      if (busy) return;
      const history: HistoryMessage[] = messages
        .filter((m) => m.kind !== "tools")
        .map((m) => ({
          role: m.kind as "user" | "assistant",
          content: (m as { content: string }).content,
        }));
      setError(null);
      setBusy(true);
      setMessages((prev) => [...prev, { id: nextId(), kind: "user", content: text }]);
      try {
        const res = await postChat({ message: text, history });
        setMessages((prev) => [
          ...prev,
          ...(res.tool_trace.length
            ? [{ id: nextId(), kind: "tools" as const, events: res.tool_trace }]
            : []),
          { id: nextId(), kind: "assistant" as const, content: res.answer },
        ]);
        setInspectorEvents((prev) => [...prev, ...res.tool_trace]);
      } catch (e) {
        setError(
          e instanceof ApiError
            ? e.message
            : "Can't reach the CatalogPilot API. Is it running on :8009?",
        );
      } finally {
        setBusy(false);
      }
    },
    [busy, messages],
  );

  function clear() {
    setMessages([]);
    setInspectorEvents([]);
    setError(null);
  }

  const live = health === null ? null : health !== false && health.mcp && health.ollama;

  return (
    <div className="cp-app">
      <BrandHeader
        live={live}
        canClear={messages.length > 0 || !!error}
        onClear={clear}
        onToggleInspector={() => setDrawer((d) => !d)}
      />
      <main className="cp-main">
        <ChatThread messages={messages} busy={busy} error={error} onPick={send} />
        <Inspector
          events={inspectorEvents}
          productCount={productCount}
          open={drawer}
          onClose={() => setDrawer(false)}
        />
      </main>
      <Composer busy={busy} onSend={send} />
    </div>
  );
}

export default App
