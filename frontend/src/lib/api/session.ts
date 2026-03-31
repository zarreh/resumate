/** API client for session and job description endpoints. */

import { apiClient } from "../api";
import type {
  ATSScoreResponse,
  CoverLetterResponse,
  GenerateResponse,
  JobDescriptionResponse,
  MatchResponse,
  ReviewResponse,
  SessionListItem,
  SessionResponse,
} from "@/types/session";

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------

export async function parseJobDescription(
  params: { text?: string; url?: string }
): Promise<JobDescriptionResponse> {
  return apiClient<JobDescriptionResponse>("/api/v1/jobs/parse", {
    method: "POST",
    body: JSON.stringify(params),
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

export async function startSession(
  params: { text?: string; url?: string }
): Promise<SessionResponse> {
  return apiClient<SessionResponse>("/api/v1/sessions/start", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function listSessions(): Promise<SessionListItem[]> {
  return apiClient<SessionListItem[]>("/api/v1/sessions/");
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

// ---------------------------------------------------------------------------
// Resume generation
// ---------------------------------------------------------------------------

export async function generateResume(
  sessionId: string,
  mode: "full" | "calibration" = "full",
  styleFeedback = "",
  stylePreference: "conservative" | "moderate" | "aggressive" = "moderate"
): Promise<GenerateResponse> {
  return apiClient<GenerateResponse>(
    `/api/v1/sessions/${sessionId}/generate`,
    {
      method: "POST",
      body: JSON.stringify({
        mode,
        style_feedback: styleFeedback,
        style_preference: stylePreference,
      }),
    }
  );
}

// ---------------------------------------------------------------------------
// Bullet feedback
// ---------------------------------------------------------------------------

export interface BulletDecision {
  bullet_id: string;
  decision: "approved" | "rejected" | "edited";
  feedback_text?: string;
  edited_text?: string;
}

export interface FeedbackResponse {
  resume: Record<string, unknown>;
  revised_bullet_ids: string[];
}

export async function submitFeedback(
  sessionId: string,
  decisions: BulletDecision[]
): Promise<FeedbackResponse> {
  return apiClient<FeedbackResponse>(
    `/api/v1/sessions/${sessionId}/feedback`,
    {
      method: "POST",
      body: JSON.stringify({ decisions }),
    }
  );
}

// ---------------------------------------------------------------------------
// Resume review
// ---------------------------------------------------------------------------

export async function reviewResume(
  sessionId: string
): Promise<ReviewResponse> {
  return apiClient<ReviewResponse>(
    `/api/v1/sessions/${sessionId}/review`,
    { method: "POST" }
  );
}

// ---------------------------------------------------------------------------
// ATS Scoring
// ---------------------------------------------------------------------------

export async function getATSScore(
  sessionId: string
): Promise<ATSScoreResponse> {
  return apiClient<ATSScoreResponse>(
    `/api/v1/sessions/${sessionId}/ats-score`,
    { method: "POST" }
  );
}

// ---------------------------------------------------------------------------
// Cover Letter
// ---------------------------------------------------------------------------

export async function generateCoverLetter(
  sessionId: string
): Promise<CoverLetterResponse> {
  return apiClient<CoverLetterResponse>(
    `/api/v1/sessions/${sessionId}/cover-letter`,
    { method: "POST" }
  );
}

export async function getCoverLetter(
  sessionId: string
): Promise<CoverLetterResponse | null> {
  return apiClient<CoverLetterResponse | null>(
    `/api/v1/sessions/${sessionId}/cover-letter`
  );
}

// ---------------------------------------------------------------------------
// Session Completion
// ---------------------------------------------------------------------------

export interface CompleteResponse {
  session_id: string;
  decision_id: string;
  message: string;
}

export async function completeSession(
  sessionId: string
): Promise<CompleteResponse> {
  return apiClient<CompleteResponse>(
    `/api/v1/sessions/${sessionId}/complete`,
    { method: "POST" }
  );
}

// ---------------------------------------------------------------------------
// Fork Session
// ---------------------------------------------------------------------------

export async function forkSession(
  sessionId: string
): Promise<SessionResponse> {
  return apiClient<SessionResponse>(
    `/api/v1/sessions/${sessionId}/fork`,
    { method: "POST" }
  );
}
