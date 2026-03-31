/** TypeScript types for the Chat feature. */

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCallInfo[];
  timestamp: Date;
}

export interface ToolCallInfo {
  name: string;
  args: Record<string, unknown>;
}

export interface ChatMessageRequest {
  message: string;
  session_id?: string;
  history?: { role: string; content: string }[];
}

export interface ChatMessageResponse {
  message: string;
  tool_calls_made: ToolCallInfo[];
}
