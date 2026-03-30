export type WSEventType =
  | "agent_start"
  | "agent_end"
  | "thinking"
  | "stream_start"
  | "stream_token"
  | "stream_end"
  | "progress"
  | "approval_gate"
  | "error";

export interface WSEvent {
  type: WSEventType;
  agent?: string | null;
  message?: string | null;
  section?: string | null;
  token?: string | null;
  current?: number | null;
  total?: number | null;
  label?: string | null;
  gate?: string | null;
  data?: Record<string, unknown> | null;
  recoverable?: boolean | null;
}

export interface Progress {
  current: number;
  total: number;
  label: string | null;
}
