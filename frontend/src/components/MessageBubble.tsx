import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import type { ChatMessage } from "../types/chat";
import { CodeBlock } from "./CodeBlock";
import { ToolCallCard } from "./ToolCallCard";

interface MessageBubbleProps {
  message: ChatMessage;
}

/**
 * Clean raw model output:
 * - Strip <tools>...</tools> XML blocks (tool calls rendered separately)
 * - Strip <summary>, <note> wrappers but keep inner content
 * - Normalize LaTeX: $...$ for inline, $$...$$ for block
 */
function cleanContent(raw: string): string {
  let text = raw;

  // Remove <tools>...</tools> blocks entirely
  text = text.replace(/<tools>[\s\S]*?<\/tools>/g, "");

  // Unwrap <summary>...</summary> and <note>...</note> — keep content
  text = text.replace(/<\/?summary>/g, "");
  text = text.replace(/<\/?note>/g, "");

  // Trim leftover whitespace
  text = text.trim();

  return text;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  const markdownComponents: Components = {
    code({ className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || "");
      const codeString = String(children).replace(/\n$/, "");

      if (match) {
        return <CodeBlock language={match[1]}>{codeString}</CodeBlock>;
      }

      return (
        <code
          className="bg-zinc-800 text-orange-300 px-1.5 py-0.5 rounded text-[0.8125rem] font-mono"
          {...props}
        >
          {children}
        </code>
      );
    },
    table({ children }) {
      return (
        <div className="overflow-x-auto my-4 rounded-lg border border-zinc-700/50">
          <table className="w-full text-sm">{children}</table>
        </div>
      );
    },
    th({ children }) {
      return (
        <th className="bg-zinc-800/60 px-4 py-2.5 text-left text-xs font-semibold text-zinc-300 border-b border-zinc-700/50">
          {children}
        </th>
      );
    },
    td({ children }) {
      return (
        <td className="px-4 py-2.5 text-zinc-400 border-b border-zinc-800/50">
          {children}
        </td>
      );
    },
  };

  if (isUser) {
    return (
      <div className="py-5">
        <div className="max-w-3xl mx-auto px-4">
          <div className="flex justify-end">
            <div className="max-w-[85%] bg-zinc-700/50 rounded-2xl px-5 py-3 text-[0.9375rem] leading-relaxed">
              {message.content}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const cleanedContent = cleanContent(message.content);

  return (
    <div className="py-5">
      <div className="max-w-3xl mx-auto px-4">
        <div className="flex gap-4">
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center mt-0.5">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-white">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            {message.toolCalls?.map((tc, i) => (
              <ToolCallCard key={`${tc.name}-${i}`} toolCall={tc} />
            ))}

            {cleanedContent ? (
              <div className="prose-chat text-zinc-300">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                  components={markdownComponents}
                >
                  {cleanedContent}
                </ReactMarkdown>
              </div>
            ) : null}

            {message.isStreaming && !cleanedContent && (
              <div className="flex gap-1 py-2">
                <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-zinc-400" />
                <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-zinc-400" />
                <span className="thinking-dot w-1.5 h-1.5 rounded-full bg-zinc-400" />
              </div>
            )}

            {message.isStreaming && cleanedContent && (
              <span className="inline-block w-[3px] h-[1.1em] bg-zinc-400 animate-pulse ml-0.5 align-middle" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
