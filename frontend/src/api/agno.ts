import type { RunEvent } from "../types/chat";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchTeams(): Promise<
  { name: string; team_id: string }[]
> {
  const response = await fetch(`${API_URL}/teams`);
  if (!response.ok) throw new Error("Failed to fetch teams");
  return response.json();
}

export async function* streamTeamRun(
  teamId: string,
  message: string,
  sessionId?: string,
): AsyncGenerator<RunEvent> {
  const formData = new FormData();
  formData.append("message", message);
  formData.append("stream", "true");
  if (sessionId) {
    formData.append("session_id", sessionId);
  }

  const url = `${API_URL}/teams/${encodeURIComponent(teamId)}/runs`;

  const response = await fetch(url, { method: "POST", body: formData });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Run failed: ${response.status} ${text}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";
  // Keep event name across chunks — event: and data: may arrive separately
  let currentEvent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by double newline
    const blocks = buffer.split("\n\n");
    // Last element is incomplete — keep in buffer
    buffer = blocks.pop() || "";

    for (const block of blocks) {
      const lines = block.split("\n");
      let eventData = "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          eventData = line.slice(6);
        }
      }

      if (eventData) {
        try {
          const parsed: RunEvent = JSON.parse(eventData);
          parsed.event = parsed.event || currentEvent;
          yield parsed;
        } catch {
          // Skip malformed JSON
        }
      }
    }
  }
}
