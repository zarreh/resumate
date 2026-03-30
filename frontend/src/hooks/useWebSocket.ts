"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Progress, WSEvent } from "@/types/ws_events";
import { getAccessToken } from "@/lib/api";

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
  .replace(/^http/, "ws");

const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECT_ATTEMPTS = 5;

interface UseWebSocketReturn {
  events: WSEvent[];
  isConnected: boolean;
  currentAgent: string | null;
  streamingText: string;
  progress: Progress | null;
  lastError: string | null;
  sendMessage: (data: string) => void;
}

export function useWebSocket(
  sessionId: string | null,
): UseWebSocketReturn {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState("");
  const [progress, setProgress] = useState<Progress | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleEvent = useCallback((event: WSEvent) => {
    setEvents((prev) => [...prev, event]);

    switch (event.type) {
      case "agent_start":
        setCurrentAgent(event.agent ?? null);
        break;
      case "agent_end":
        setCurrentAgent(null);
        break;
      case "stream_start":
        setStreamingText("");
        break;
      case "stream_token":
        if (event.token) {
          setStreamingText((prev) => prev + event.token);
        }
        break;
      case "stream_end":
        // streaming text stays for consumers to read; reset on next stream_start
        break;
      case "progress":
        if (event.current != null && event.total != null) {
          setProgress({
            current: event.current,
            total: event.total,
            label: event.label ?? null,
          });
        }
        break;
      case "error":
        setLastError(event.message ?? "Unknown error");
        break;
      default:
        break;
    }
  }, []);

  useEffect(() => {
    if (!sessionId) return;

    function connect() {
      const token = getAccessToken();
      if (!token) return;

      const url = `${WS_BASE}/api/v1/sessions/${sessionId}/stream?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setLastError(null);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (msg) => {
        try {
          const event: WSEvent = JSON.parse(msg.data);
          handleEvent(event);
        } catch {
          // non-JSON message — ignore
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;

        // Auto-reconnect with back-off
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1;
          reconnectTimer.current = setTimeout(
            connect,
            RECONNECT_DELAY_MS * reconnectAttempts.current,
          );
        }
      };

      ws.onerror = () => {
        // onclose will fire after onerror — reconnection is handled there
      };
    }

    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [sessionId, handleEvent]);

  const sendMessage = useCallback((data: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  return {
    events,
    isConnected,
    currentAgent,
    streamingText,
    progress,
    lastError,
    sendMessage,
  };
}
