import { type FormEvent, type KeyboardEvent, useRef, useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  function handleInput() {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
    }
  }

  return (
    <div className="bg-zinc-900 pb-6 pt-2 px-4">
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
        <div className="relative bg-zinc-800 rounded-2xl border border-zinc-700/60 shadow-lg focus-within:border-zinc-600 transition-colors">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder="Message Argus..."
            disabled={disabled}
            rows={1}
            className="w-full bg-transparent text-zinc-100 placeholder-zinc-500 outline-none resize-none text-[0.9375rem] leading-6 px-5 pt-4 pb-12 max-h-[200px]"
          />
          <div className="absolute bottom-3 right-3 flex items-center gap-2">
            <button
              type="submit"
              disabled={disabled || !input.trim()}
              className="w-8 h-8 rounded-lg bg-zinc-100 hover:bg-white disabled:bg-zinc-700 disabled:text-zinc-500 text-zinc-900 transition-colors flex items-center justify-center"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
            </button>
          </div>
        </div>
        <p className="text-center text-[0.6875rem] text-zinc-600 mt-2.5">
          Argus uses local models via Ollama. Responses may take a moment.
        </p>
      </form>
    </div>
  );
}
