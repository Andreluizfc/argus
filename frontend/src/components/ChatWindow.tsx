import { useChat } from "../hooks/useChat";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";

interface ChatWindowProps {
  teamId: string;
}

export function ChatWindow({ teamId }: ChatWindowProps) {
  const { messages, isLoading, sendMessage, clearMessages } = useChat({
    teamId,
  });

  return (
    <div className="flex flex-col h-screen bg-zinc-900">
      {/* Header */}
      <header className="flex-shrink-0 flex items-center justify-between px-5 h-12 border-b border-zinc-800">
        <div className="flex items-center gap-2.5">
          <div className="w-5 h-5 rounded-md bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" className="text-white">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
            </svg>
          </div>
          <span className="text-sm font-medium text-zinc-300">Argus</span>
          <span className="text-xs text-zinc-600 font-normal">Multi-Agent Team</span>
        </div>
        <button
          onClick={clearMessages}
          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors px-2.5 py-1 rounded-md hover:bg-zinc-800"
        >
          New chat
        </button>
      </header>

      {/* Messages */}
      <MessageList messages={messages} />

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  );
}
