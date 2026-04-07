import type { ToolCall } from "../types/chat";

interface ToolCallCardProps {
  toolCall: ToolCall;
}

function formatToolName(toolCall: ToolCall): string {
  if (toolCall.name === "delegate_task_to_member") {
    const memberId = toolCall.args.member_id as string | undefined;
    return memberId
      ? `Delegating to ${memberId.charAt(0).toUpperCase() + memberId.slice(1)}`
      : "Delegating to member";
  }
  return toolCall.name;
}

function formatToolDetail(toolCall: ToolCall): string | null {
  if (toolCall.name === "delegate_task_to_member") {
    return (toolCall.args.task as string) || null;
  }
  const values = Object.values(toolCall.args).map(String);
  return values.length > 0 ? values.join(", ") : null;
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const isActive = toolCall.status === "started";
  const detail = formatToolDetail(toolCall);

  return (
    <div className="my-3 flex items-start gap-2 text-xs text-zinc-500">
      <div className="mt-0.5">
        {isActive ? (
          <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" opacity="0.3" />
            <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        ) : toolCall.status === "completed" ? (
          <svg className="w-3.5 h-3.5 text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-zinc-400">
          {formatToolName(toolCall)}
        </span>
        {detail && (
          <span className="block text-zinc-600 mt-0.5 truncate">
            {detail}
          </span>
        )}
      </div>
    </div>
  );
}
