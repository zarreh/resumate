export interface SessionFeedbackSummary {
  session_id: string;
  role_title: string | null;
  company_name: string | null;
  approved: number;
  rejected: number;
  edited: number;
  total: number;
  created_at: string;
}

export interface FeedbackMetrics {
  total_decisions: number;
  approved_count: number;
  rejected_count: number;
  edited_count: number;
  approval_rate: number;
  rejection_rate: number;
  edit_rate: number;
  sessions_with_feedback: number;
  per_session: SessionFeedbackSummary[];
}
