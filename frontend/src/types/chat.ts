export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result?: string;
  status: "started" | "completed" | "error";
}

export interface RunEvent {
  event: string;
  run_id?: string;
  session_id?: string;
  content?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  result?: string;
  metrics?: Record<string, number>;
  // Agno nests tool info under a `tool` object
  tool?: {
    tool_name?: string;
    tool_args?: Record<string, unknown>;
    result?: string;
  };
}
