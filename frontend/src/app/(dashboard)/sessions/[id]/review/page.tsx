"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { FullDraftView } from "@/components/session/FullDraftView";
import { GateApprovalBar } from "@/components/session/GateApprovalBar";
import { approveGate, getSession } from "@/lib/api/session";
import type { EnhancedResume, SessionResponse } from "@/types/session";

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [session, setSession] = useState<SessionResponse | null>(null);
  const [resume, setResume] = useState<EnhancedResume | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [bulletStatuses, setBulletStatuses] = useState<
    Record<string, "pending" | "approved" | "rejected">
  >({});

  const fetchSession = useCallback(async () => {
    try {
      const data = await getSession(sessionId);
      setSession(data);
      if (data.enhanced_resume) {
        setResume(data.enhanced_resume);
        // Default all bullets to "pending"
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

  const handleSkillsChange = (skills: string[]) => {
    if (resume) {
      setResume({ ...resume, skills });
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

  // Count statuses
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
          </div>

          {/* Full draft */}
          <FullDraftView
            resume={resume}
            bulletStatuses={bulletStatuses}
            showControls
            onBulletApprove={handleBulletApprove}
            onBulletReject={handleBulletReject}
            onSkillsChange={handleSkillsChange}
          />
        </div>
      </div>

      {/* Approval Bar */}
      <GateApprovalBar
        onApprove={handleApprove}
        loading={approving}
        disabled={rejectedCount > 0}
        label={
          rejectedCount > 0
            ? `${rejectedCount} rejected — submit feedback first`
            : "Approve & Finalize"
        }
      />
    </div>
  );
}
