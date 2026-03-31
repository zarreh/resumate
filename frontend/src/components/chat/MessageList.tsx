"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/types/chat";
import MessageBubble from "./MessageBubble";
import ThinkingIndicator from "./ThinkingIndicator";

interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

export default function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isUserScrolled = useRef(false);

  // Track if user has scrolled up
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    function handleScroll() {
      if (!container) return;
      const { scrollTop, scrollHeight, clientHeight } = container;
      isUserScrolled.current = scrollHeight - scrollTop - clientHeight > 50;
    }

    container.addEventListener("scroll", handleScroll);
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (!isUserScrolled.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground text-sm">
        Ask me anything about your career history or resume sessions.
      </div>
    );
  }

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      {isLoading && <ThinkingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
