import { useCallback, useRef, useState } from "react";

import { streamTeamRun } from "../api/agno";
import type { ChatMessage, ToolCall } from "../types/chat";

interface UseChatOptions {
  teamId: string;
}

export function useChat({ teamId }: UseChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const sessionIdRef = useRef<string | undefined>(undefined);

  const sendMessage = useCallback(
    async (content: string) => {
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        timestamp: new Date(),
      };

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
        toolCalls: [],
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsLoading(true);

      try {
        const stream = streamTeamRun(
          teamId,
          content,
          sessionIdRef.current,
        );

        for await (const event of stream) {
          // Normalize: TeamRunContent -> RunContent, etc.
          const eventType = event.event.replace(/^Team/, "");

          // Extract tool info — Agno nests it under event.tool
          const tool = event.tool as
            | { tool_name?: string; tool_args?: Record<string, unknown>; result?: string }
            | undefined;

          console.log("[useChat] eventType:", eventType, "content:", event.content?.slice(0, 50));

          switch (eventType) {
            case "RunStarted":
              sessionIdRef.current = event.session_id;
              break;

            case "RunContent":
              if (event.content) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last?.role === "assistant") {
                    return [
                      ...updated.slice(0, -1),
                      { ...last, content: last.content + event.content },
                    ];
                  }
                  return updated;
                });
              }
              break;

            case "ToolCallStarted": {
              const toolName = tool?.tool_name || event.tool_name || "unknown";
              const toolArgs = tool?.tool_args || event.tool_args || {};
              const toolCall: ToolCall = {
                name: toolName,
                args: toolArgs,
                status: "started",
              };
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === "assistant") {
                  return [
                    ...updated.slice(0, -1),
                    {
                      ...last,
                      toolCalls: [...(last.toolCalls || []), toolCall],
                    },
                  ];
                }
                return updated;
              });
              break;
            }

            case "ToolCallCompleted": {
              const completedName = tool?.tool_name || event.tool_name;
              const completedResult = tool?.result || event.result || event.content;
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === "assistant" && last.toolCalls) {
                  const newToolCalls = last.toolCalls.map((t) =>
                    t.name === completedName && t.status === "started"
                      ? { ...t, status: "completed" as const, result: completedResult }
                      : t,
                  );
                  return [
                    ...updated.slice(0, -1),
                    { ...last, toolCalls: newToolCalls },
                  ];
                }
                return updated;
              });
              break;
            }

            case "RunCompleted":
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === "assistant") {
                  return [
                    ...updated.slice(0, -1),
                    {
                      ...last,
                      isStreaming: false,
                      // Only use completed content if we didn't stream anything
                      content: last.content || event.content || "",
                    },
                  ];
                }
                return updated;
              });
              break;

            case "RunError":
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === "assistant") {
                  return [
                    ...updated.slice(0, -1),
                    {
                      ...last,
                      content: `Error: ${event.content || "Unknown error"}`,
                      isStreaming: false,
                    },
                  ];
                }
                return updated;
              });
              break;
          }
        }
      } catch (error) {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant") {
            return [
              ...updated.slice(0, -1),
              {
                ...last,
                content: `Connection error: ${error instanceof Error ? error.message : "Unknown"}`,
                isStreaming: false,
              },
            ];
          }
          return updated;
        });
      } finally {
        setIsLoading(false);
      }
    },
    [teamId],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    sessionIdRef.current = undefined;
  }, []);

  return { messages, isLoading, sendMessage, clearMessages };
}
