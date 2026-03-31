"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { FullDraftView } from "@/components/session/FullDraftView";
import { GateApprovalBar } from "@/components/session/GateApprovalBar";
import {
  approveGate,
  getSession,
  reviewResume,
  submitFeedback,
  type BulletDecision,
} from "@/lib/api/session";
import type { EnhancedResume, ReviewAnnotation, ReviewReport, SessionResponse } from "@/types/session";

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [session, setSession] = useState<SessionResponse | null>(null);
  const [resume, setResume] = useState<EnhancedResume | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [bulletStatuses, setBulletStatuses] = useState<
    Record<string, "pending" | "approved" | "rejected">
  >({});
  const [feedbackTexts, setFeedbackTexts] = useState<Record<string, string>>(
    {}
  );
  const [reviewReport, setReviewReport] = useState<ReviewReport | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [annotations, setAnnotations] = useState<
    Record<string, ReviewAnnotation[]>
  >({});

  const fetchSession = useCallback(async () => {
    try {
      const data = await getSession(sessionId);
      setSession(data);
      if (data.enhanced_resume) {
        setResume(data.enhanced_resume);
        const statuses: Record<string, "pending"> = {};
        for (const section of data.enhanced_resume.sections) {
          for (const entry of section.entries) {
            for (const bullet of entry.bullets) {
              statuses[bullet.id] = "pending";
            }
          }
        }
        setBulletStatuses(statuses);
      }
    } catch {
      toast.error("Failed to load session");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  const handleRunReview = async () => {
    setReviewing(true);
    try {
      const result = await reviewResume(sessionId);
      setReviewReport(result.report);
      // Group annotations by bullet_id
      const grouped: Record<string, ReviewAnnotation[]> = {};
      for (const ann of result.report.annotations) {
        if (!grouped[ann.bullet_id]) grouped[ann.bullet_id] = [];
        grouped[ann.bullet_id].push(ann);
      }
      setAnnotations(grouped);
      toast.success(
        `Review complete: ${result.report.strong_count} strong, ${result.report.adequate_count} adequate, ${result.report.weak_count} weak`
      );
    } catch {
      toast.error("Failed to run review");
    } finally {
      setReviewing(false);
    }
  };

  const handleBulletApprove = (bulletId: string) => {
    setBulletStatuses((prev) => ({
      ...prev,
      [bulletId]: prev[bulletId] === "approved" ? "pending" : "approved",
    }));
  };

  const handleBulletReject = (bulletId: string) => {
    setBulletStatuses((prev) => ({
      ...prev,
      [bulletId]: prev[bulletId] === "rejected" ? "pending" : "rejected",
    }));
  };

  const handleBulletEdit = (bulletId: string, text: string) => {
    // Apply edit directly to the resume state
    if (!resume) return;
    const updated = { ...resume };
    updated.sections = updated.sections.map((s) => ({
      ...s,
      entries: s.entries.map((e) => ({
        ...e,
        bullets: e.bullets.map((b) =>
          b.id === bulletId ? { ...b, enhanced_text: text } : b
        ),
      })),
    }));
    setResume(updated);
    setBulletStatuses((prev) => ({ ...prev, [bulletId]: "approved" }));
  };

  const handleSkillsChange = (skills: string[]) => {
    if (resume) {
      setResume({ ...resume, skills });
    }
  };

  const handleSubmitFeedback = async () => {
    setSubmittingFeedback(true);
    try {
      const decisions: BulletDecision[] = Object.entries(bulletStatuses)
        .filter(([, status]) => status !== "pending")
        .map(([bulletId, status]) => ({
          bullet_id: bulletId,
          decision: status as "approved" | "rejected",
          feedback_text:
            status === "rejected" ? feedbackTexts[bulletId] : undefined,
        }));

      const result = await submitFeedback(sessionId, decisions);
      const updatedResume = result.resume as unknown as EnhancedResume;
      setResume(updatedResume);

      // Reset rejected bullets to pending (they've been revised)
      setBulletStatuses((prev) => {
        const next = { ...prev };
        for (const id of result.revised_bullet_ids) {
          next[id] = "pending";
        }
        return next;
      });

      toast.success(
        `Feedback submitted. ${result.revised_bullet_ids.length} bullets revised.`
      );
    } catch {
      toast.error("Failed to submit feedback");
    } finally {
      setSubmittingFeedback(false);
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      await approveGate(sessionId, "review");
      toast.success("Review approved! Moving to final...");
      router.push(`/dashboard/sessions/${sessionId}/final`);
    } catch {
      toast.error("Failed to approve review");
    } finally {
      setApproving(false);
    }
  };

  const approvedCount = Object.values(bulletStatuses).filter(
    (s) => s === "approved"
  ).length;
  const rejectedCount = Object.values(bulletStatuses).filter(
    (s) => s === "rejected"
  ).length;
  const totalCount = Object.keys(bulletStatuses).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Loading review...</p>
      </div>
    );
  }

  if (!session || !resume) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">
          No resume draft available. Complete calibration first.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-4xl space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-2xl font-bold">Review Draft</h1>
            <p className="text-muted-foreground">
              Review each bullet point. Approve, reject, or edit individual
              bullets before finalizing.
            </p>
          </div>

          {/* Status bar */}
          <div className="flex items-center gap-4 rounded-lg bg-muted/50 p-3 text-sm">
            <span>
              <strong>{totalCount}</strong> bullets total
            </span>
            <span className="text-green-600">
              <strong>{approvedCount}</strong> approved
            </span>
            <span className="text-red-600">
              <strong>{rejectedCount}</strong> rejected
            </span>
            <span className="text-muted-foreground">
              <strong>{totalCount - approvedCount - rejectedCount}</strong>{" "}
              pending
            </span>

            {rejectedCount > 0 && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleSubmitFeedback}
                disabled={submittingFeedback}
                className="ml-auto"
              >
                {submittingFeedback
                  ? "Revising..."
                  : `Submit Feedback (${rejectedCount} rejected)`}
              </Button>
            )}

            <Button
              size="sm"
              variant="secondary"
              onClick={handleRunReview}
              disabled={reviewing}
              className={rejectedCount > 0 ? "" : "ml-auto"}
            >
              {reviewing ? "Reviewing..." : "Run AI Review"}
            </Button>
          </div>

          {/* Review summary */}
          {reviewReport && (
            <div className="space-y-2 rounded-lg border border-border bg-muted/30 p-4">
              <h3 className="text-sm font-semibold">AI Review Summary</h3>
              <div className="flex gap-4 text-xs">
                <span className="text-green-600">
                  <strong>{reviewReport.strong_count}</strong> strong
                </span>
                <span className="text-yellow-600">
                  <strong>{reviewReport.adequate_count}</strong> adequate
                </span>
                <span className="text-red-600">
                  <strong>{reviewReport.weak_count}</strong> weak
                </span>
              </div>
              <div className="space-y-1 text-xs text-muted-foreground">
                <p>
                  <strong>Recruiter:</strong> {reviewReport.recruiter_summary}
                </p>
                <p>
                  <strong>Hiring Manager:</strong>{" "}
                  {reviewReport.hiring_manager_summary}
                </p>
              </div>
            </div>
          )}

          {/* Full draft */}
          <FullDraftView
            resume={resume}
            bulletStatuses={bulletStatuses}
            annotations={annotations}
            showControls
            onBulletApprove={handleBulletApprove}
            onBulletReject={handleBulletReject}
            onBulletEdit={handleBulletEdit}
            onSkillsChange={handleSkillsChange}
          />
        </div>
      </div>

      {/* Approval Bar */}
      <GateApprovalBar
        onApprove={handleApprove}
        loading={approving}
        disabled={rejectedCount > 0 || submittingFeedback}
        label={
          rejectedCount > 0
            ? `${rejectedCount} rejected — submit feedback first`
            : "Approve & Finalize"
        }
      />
    </div>
  );
}
