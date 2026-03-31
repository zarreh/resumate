"use client";

import { useChat } from "@/hooks/useChat";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";

interface ChatPanelProps {
  sessionId?: string;
}

export default function ChatPanel({ sessionId }: ChatPanelProps) {
  const { messages, isLoading, error, sendMessage, clearMessages } =
    useChat(sessionId);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">ResuMate Chat</h2>
        {messages.length > 0 && (
          <Button
            variant="ghost"
            size="icon"
            onClick={clearMessages}
            className="h-7 w-7"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {/* Messages */}
      <MessageList messages={messages} isLoading={isLoading} />

      {/* Error */}
      {error && (
        <div className="px-4 py-2 text-xs text-destructive">{error}</div>
      )}

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  );
}
