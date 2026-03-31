"use client";

import { useCallback, useState } from "react";
import { sendChatMessage } from "@/lib/api/chat";
import type { ChatMessage, ToolCallInfo } from "@/types/chat";

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (text: string) => Promise<void>;
  clearMessages: () => void;
}

let _nextId = 0;
function nextId(): string {
  _nextId += 1;
  return `msg-${_nextId}`;
}

export function useChat(sessionId?: string): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim()) return;

      const userMsg: ChatMessage = {
        id: nextId(),
        role: "user",
        content: text,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      try {
        // Build history from existing messages (exclude the current one)
        const history = messages.map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const response = await sendChatMessage(text, sessionId, history);

        const toolCalls: ToolCallInfo[] = response.tool_calls_made.map(
          (tc) => ({
            name: tc.name,
            args: tc.args as Record<string, unknown>,
          })
        );

        const assistantMsg: ChatMessage = {
          id: nextId(),
          role: "assistant",
          content: response.message,
          toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to send message";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [messages, sessionId]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, isLoading, error, sendMessage, clearMessages };
}
