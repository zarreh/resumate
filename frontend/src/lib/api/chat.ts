/** API client for chat endpoints. */

import { apiClient } from "../api";
import type { ChatMessageResponse } from "@/types/chat";

export async function sendChatMessage(
  message: string,
  sessionId?: string,
  history?: { role: string; content: string }[]
): Promise<ChatMessageResponse> {
  return apiClient<ChatMessageResponse>("/api/v1/chat/message", {
    method: "POST",
    body: JSON.stringify({
      message,
      session_id: sessionId ?? null,
      history: history ?? [],
    }),
  });
}
