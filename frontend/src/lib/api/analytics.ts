import type { FeedbackMetrics } from "@/types/analytics";
import { apiClient } from "../api";

export async function getFeedbackMetrics(): Promise<FeedbackMetrics> {
  return apiClient<FeedbackMetrics>("/api/v1/analytics/feedback");
}
