export type ChatRole = "user" | "assistant";

export interface HistoryMessage {
  role: ChatRole;
  content: string;
}

export interface ToolTraceEvent {
  name: string;
  args: Record<string, unknown>;
  result: unknown;
  ms: number;
  ok: boolean;
  error: string | null;
}

export interface ChatRequest {
  message: string;
  history: HistoryMessage[];
}

export interface ChatResponse {
  answer: string;
  tool_trace: ToolTraceEvent[];
}

export interface HealthResponse {
  ollama: boolean;
  mcp: boolean;
  catalog_count: number | null;
}

export interface CatalogSummary {
  product_count: number;
  categories: Record<string, number>;
  sample_skus: string[];
}

export interface UserMsg {
  id: string;
  kind: "user";
  content: string;
}

export interface AssistantMsg {
  id: string;
  kind: "assistant";
  content: string;
}

export interface ToolGroupMsg {
  id: string;
  kind: "tools";
  events: ToolTraceEvent[];
}

export type ThreadMessage = UserMsg | AssistantMsg | ToolGroupMsg;

/** Outcome of a send: "stale" means the chat was cleared mid-flight. */
export type SendResult = "ok" | "failed" | "stale";
