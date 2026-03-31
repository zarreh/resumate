"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle,
  XCircle,
  Pencil,
  BarChart3,
  Building2,
  Briefcase,
} from "lucide-react";
import { getFeedbackMetrics } from "@/lib/api/analytics";
import type { FeedbackMetrics } from "@/types/analytics";

export default function QualityDashboardPage() {
  const [metrics, setMetrics] = useState<FeedbackMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMetrics = useCallback(async () => {
    try {
      const data = await getFeedbackMetrics();
      setMetrics(data);
    } catch {
      toast.error("Failed to load feedback metrics");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  const pct = (rate: number) => `${(rate * 100).toFixed(1)}%`;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Loading quality metrics...</p>
      </div>
    );
  }

  if (!metrics || metrics.total_decisions === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Quality Dashboard</h1>
          <p className="text-muted-foreground">
            Feedback metrics from your resume tailoring sessions.
          </p>
        </div>
        <div className="rounded-lg border border-dashed p-8 text-center">
          <BarChart3 className="mx-auto h-8 w-8 text-muted-foreground" />
          <p className="mt-2 text-muted-foreground">
            No feedback data yet. Complete a review session and provide bullet
            feedback to see quality metrics here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Quality Dashboard</h1>
        <p className="text-muted-foreground">
          Feedback metrics from your resume tailoring sessions.
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Decisions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{metrics.total_decisions}</p>
            <p className="text-xs text-muted-foreground">
              across {metrics.sessions_with_feedback} session
              {metrics.sessions_with_feedback !== 1 ? "s" : ""}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Approval Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">
              {pct(metrics.approval_rate)}
            </p>
            <p className="text-xs text-muted-foreground">
              {metrics.approved_count} bullets approved
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Rejection Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-600">
              {pct(metrics.rejection_rate)}
            </p>
            <p className="text-xs text-muted-foreground">
              {metrics.rejected_count} bullets rejected
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Edit Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-amber-600">
              {pct(metrics.edit_rate)}
            </p>
            <p className="text-xs text-muted-foreground">
              {metrics.edited_count} bullets edited
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Per-session breakdown */}
      <div>
        <h2 className="mb-3 text-lg font-semibold">Per-Session Breakdown</h2>
        <div className="grid gap-3">
          {metrics.per_session.map((s) => (
            <Card key={s.session_id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-medium">
                      {s.role_title || "Untitled Role"}
                    </span>
                    {s.company_name && (
                      <span className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Building2 className="h-3 w-3" />
                        {s.company_name}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    <Briefcase className="mr-1 inline h-3 w-3" />
                    {s.total} decisions &middot;{" "}
                    {new Date(s.created_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </p>
                </div>
                <div className="ml-4 flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className="gap-1 bg-green-50 text-green-700"
                  >
                    <CheckCircle className="h-3 w-3" />
                    {s.approved}
                  </Badge>
                  <Badge
                    variant="outline"
                    className="gap-1 bg-red-50 text-red-700"
                  >
                    <XCircle className="h-3 w-3" />
                    {s.rejected}
                  </Badge>
                  <Badge
                    variant="outline"
                    className="gap-1 bg-amber-50 text-amber-700"
                  >
                    <Pencil className="h-3 w-3" />
                    {s.edited}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
