import { useCallback, useState } from "react";
import { apiSSE } from "../api/client";
import type { ChatMessage } from "../api/types";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);

  const send = useCallback(async (text: string) => {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setStreaming(true);

    let assistantText = "";
    const toolCalls: { name: string; result: string }[] = [];

    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", toolCalls: [] },
    ]);

    await apiSSE("/api/chat", { message: text }, {
      onText(chunk) {
        assistantText += chunk;
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: assistantText,
            toolCalls: [...toolCalls],
          };
          return updated;
        });
      },
      onToolCall(name) {
        toolCalls.push({ name, result: "" });
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: assistantText,
            toolCalls: [...toolCalls],
          };
          return updated;
        });
      },
      onToolResult(name, result) {
        const tc = toolCalls.find((t) => t.name === name && !t.result);
        if (tc) tc.result = result;
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: assistantText,
            toolCalls: [...toolCalls],
          };
          return updated;
        });
      },
      onDone() {
        setStreaming(false);
      },
    }).catch(() => {
      setStreaming(false);
    });
  }, []);

  const clear = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, streaming, send, clear };
}
