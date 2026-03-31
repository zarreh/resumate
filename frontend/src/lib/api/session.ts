/** API client for session and job description endpoints. */

import { apiClient } from "../api";
import type {
  JobDescriptionResponse,
  MatchResponse,
  SessionResponse,
} from "@/types/session";

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------

export async function parseJobDescription(
  text: string
): Promise<JobDescriptionResponse> {
  return apiClient<JobDescriptionResponse>("/api/v1/jobs/parse", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function listJobHistory(): Promise<JobDescriptionResponse[]> {
  return apiClient<JobDescriptionResponse[]>("/api/v1/jobs/history");
}

export async function getJobDescription(
  id: string
): Promise<JobDescriptionResponse> {
  return apiClient<JobDescriptionResponse>(`/api/v1/jobs/${id}`);
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

export async function startSession(text: string): Promise<SessionResponse> {
  return apiClient<SessionResponse>("/api/v1/sessions/start", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function getSession(id: string): Promise<SessionResponse> {
  return apiClient<SessionResponse>(`/api/v1/sessions/${id}`);
}

export async function approveGate(
  sessionId: string,
  gate: string,
  selectedEntryIds: string[] = [],
  contextText?: string
): Promise<SessionResponse> {
  return apiClient<SessionResponse>(
    `/api/v1/sessions/${sessionId}/approve`,
    {
      method: "POST",
      body: JSON.stringify({
        gate,
        selected_entry_ids: selectedEntryIds,
        context_text: contextText ?? null,
      }),
    }
  );
}

export async function getMatch(sessionId: string): Promise<MatchResponse> {
  return apiClient<MatchResponse>(`/api/v1/sessions/${sessionId}/match`);
}
