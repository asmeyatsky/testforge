import { useRef, useEffect, useState, type FormEvent } from "react";
import { useChat } from "../hooks/useChat";

export function ChatPanel() {
  const { messages, streaming, send, clear } = useChat();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    send(text);
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-2xl font-bold">Chat</h2>
        <button
          className="text-xs text-gray-500 hover:text-gray-700"
          onClick={clear}
        >
          Clear
        </button>
      </div>
      <p className="text-sm text-gray-500 mb-4">
        AI-powered assistant that can analyse, generate, execute, repair, and
        discuss your tests. Requires an Anthropic or Gemini API key in Settings.
      </p>

      <div className="flex-1 overflow-auto bg-white border rounded-lg p-4 mb-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-gray-400 text-sm text-center mt-8">
            Ask TestForge to analyse your code, generate tests, find gaps, and
            more. Configure an API key in Settings (gear icon) first.
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`${msg.role === "user" ? "text-right" : "text-left"}`}
          >
            <div
              className={`inline-block max-w-[80%] px-4 py-2 rounded-lg text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              {msg.content}
            </div>
            {msg.toolCalls && msg.toolCalls.length > 0 && (
              <div className="mt-1 space-y-1">
                {msg.toolCalls.map((tc, j) => (
                  <div
                    key={j}
                    className="inline-block max-w-[80%] text-left bg-gray-50 border rounded px-3 py-2 text-xs"
                  >
                    <span className="font-semibold text-blue-600">
                      {tc.name}
                    </span>
                    {tc.result && (
                      <pre className="mt-1 text-gray-600 whitespace-pre-wrap max-h-32 overflow-auto">
                        {tc.result}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {streaming && (
          <div className="text-gray-400 text-sm animate-pulse">Thinking...</div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          className="border rounded px-3 py-2 flex-1 text-sm"
          placeholder="Ask TestForge..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={streaming}
        />
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          disabled={streaming || !input.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}
