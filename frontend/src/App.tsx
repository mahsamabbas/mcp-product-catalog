import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getCatalogSummary, getHealth, postChat } from "./api";
import { BrandHeader } from "./components/BrandHeader";
import { ChatThread } from "./components/ChatThread";
import { Composer } from "./components/Composer";
import { Inspector } from "./components/Inspector";
import { buildHistory, createEpoch, removeMessage } from "./lib/session";
import type {
  HealthResponse,
  SendResult,
  ThreadMessage,
  ToolTraceEvent,
} from "./types";

const DRAWER_QUERY = "(max-width: 860px)";

function useIsDrawer(): boolean {
  const [match, setMatch] = useState(() => window.matchMedia(DRAWER_QUERY).matches);
  useEffect(() => {
    const mq = window.matchMedia(DRAWER_QUERY);
    const on = () => setMatch(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return match;
}

function App() {
  const [messages, setMessages] = useState<ThreadMessage[]>([]);
  const [inspectorEvents, setInspectorEvents] = useState<ToolTraceEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null | false>(null);
  const [productCount, setProductCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drawer, setDrawer] = useState(false);
  const isDrawer = useIsDrawer();
  const seq = useRef(0);
  const nextId = () => `m${++seq.current}`;
  const epoch = useRef(createEpoch());
  const abort = useRef<AbortController | null>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);

  const refreshStatus = useCallback(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(false));
    getCatalogSummary()
      .then((s) => setProductCount(s.product_count))
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  const send = useCallback(
    async (text: string): Promise<SendResult> => {
      if (busy) return "failed";
      const token = epoch.current.current();
      const history = buildHistory(messages);
      const pendingId = nextId();
      const controller = new AbortController();
      abort.current = controller;
      setError(null);
      setBusy(true);
      setMessages((prev) => [...prev, { id: pendingId, kind: "user", content: text }]);
      try {
        const res = await postChat({ message: text, history }, controller.signal);
        if (!epoch.current.isCurrent(token)) return "stale";
        setMessages((prev) => [
          ...prev,
          ...(res.tool_trace.length
            ? [{ id: nextId(), kind: "tools" as const, events: res.tool_trace }]
            : []),
          { id: nextId(), kind: "assistant" as const, content: res.answer },
        ]);
        setInspectorEvents((prev) => [...prev, ...res.tool_trace]);
        refreshStatus();
        return "ok";
      } catch (e) {
        if (!epoch.current.isCurrent(token)) return "stale";
        // Failed turn: drop the optimistic bubble; composer restores the text.
        setMessages((prev) => removeMessage(prev, pendingId));
        setError(
          e instanceof ApiError
            ? e.message
            : "Can't reach the CatalogPilot API. Is it running on :8009?",
        );
        if (e instanceof ApiError && e.status === 503) setHealth(false);
        refreshStatus();
        return "failed";
      } finally {
        if (epoch.current.isCurrent(token)) {
          setBusy(false);
          abort.current = null;
        }
      }
    },
    [busy, messages, refreshStatus],
  );

  function clear() {
    epoch.current.bump();
    abort.current?.abort();
    abort.current = null;
    setBusy(false);
    setMessages([]);
    setInspectorEvents([]);
    setError(null);
  }

  const closeDrawer = useCallback(() => {
    setDrawer(false);
    toggleRef.current?.focus();
  }, []);

  const live = health === null ? null : health !== false && health.mcp && health.ollama;

  return (
    <div className="cp-app">
      <BrandHeader
        live={live}
        canClear={messages.length > 0 || !!error || busy}
        onClear={clear}
        onToggleInspector={() => setDrawer((d) => !d)}
        inspectorOpen={drawer}
        toggleRef={toggleRef}
      />
      <main className="cp-main">
        <ChatThread messages={messages} busy={busy} error={error} onPick={send} />
        <Inspector
          events={inspectorEvents}
          productCount={productCount}
          open={drawer}
          isDrawer={isDrawer}
          onClose={closeDrawer}
        />
      </main>
      <Composer busy={busy} onSend={send} />
    </div>
  );
}

export default App
