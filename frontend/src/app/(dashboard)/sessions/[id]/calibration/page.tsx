"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { CalibrationView } from "@/components/session/CalibrationView";
import { StyleFeedback } from "@/components/session/StyleFeedback";
import { GateApprovalBar } from "@/components/session/GateApprovalBar";
import {
  approveGate,
  generateResume,
  getSession,
} from "@/lib/api/session";
import type { EnhancedResume, SessionResponse } from "@/types/session";

type StrengthOption = "conservative" | "moderate" | "aggressive";

const STRENGTH_OPTIONS: {
  value: StrengthOption;
  label: string;
  description: string;
}[] = [
  {
    value: "conservative",
    label: "Conservative",
    description: "Minimal changes — preserves your original wording",
  },
  {
    value: "moderate",
    label: "Moderate",
    description: "Balanced rephrasing with ATS optimization",
  },
  {
    value: "aggressive",
    label: "Aggressive",
    description: "Maximum rewrite for JD alignment and impact",
  },
];

export default function CalibrationPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [session, setSession] = useState<SessionResponse | null>(null);
  const [resume, setResume] = useState<EnhancedResume | null>(null);
  const [styleFeedback, setStyleFeedback] = useState("");
  const [strength, setStrength] = useState<StrengthOption>("moderate");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [approving, setApproving] = useState(false);

  // Fetch session
  const fetchSession = useCallback(async () => {
    try {
      const data = await getSession(sessionId);
      setSession(data);

      // Restore saved style preference if present
      if (
        data.style_preference &&
        ["conservative", "moderate", "aggressive"].includes(
          data.style_preference
        )
      ) {
        setStrength(data.style_preference as StrengthOption);
      }

      // If the session already has an enhanced resume, use it
      if (data.enhanced_resume) {
        setResume(data.enhanced_resume);
        setLoading(false);
        return;
      }

      // Otherwise, generate the initial preview
      setGenerating(true);
      try {
        const result = await generateResume(
          sessionId,
          "full",
          "",
          strength
        );
        setResume(result.resume);
      } catch {
        toast.error("Failed to generate resume preview");
      } finally {
        setGenerating(false);
      }
    } catch {
      toast.error("Failed to load session");
    } finally {
      setLoading(false);
    }
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  const handleRegenerate = async () => {
    setGenerating(true);
    try {
      const result = await generateResume(
        sessionId,
        styleFeedback.trim() ? "calibration" : "full",
        styleFeedback,
        strength
      );
      setResume(result.resume);
      toast.success("Resume regenerated");
    } catch {
      toast.error("Failed to regenerate resume");
    } finally {
      setGenerating(false);
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      // If there's style feedback, do a final calibrated generation
      if (styleFeedback.trim() && resume) {
        await generateResume(
          sessionId,
          "calibration",
          styleFeedback,
          strength
        );
      }

      await approveGate(sessionId, "calibration");
      toast.success("Calibration approved! Moving to review...");
      router.push(`/sessions/${sessionId}/review`);
    } catch {
      toast.error("Failed to approve calibration");
    } finally {
      setApproving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Loading calibration...</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Session not found.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-4xl space-y-8">
          {/* Header */}
          <div>
            <h1 className="text-2xl font-bold">Calibration</h1>
            <p className="text-muted-foreground">
              Review the sample bullets and summary. Adjust the enhancement
              strength, provide feedback on the style, then approve to generate
              the full resume.
            </p>
          </div>

          {generating ? (
            <div className="flex items-center justify-center py-12">
              <p className="text-muted-foreground">
                Generating resume preview...
              </p>
            </div>
          ) : resume ? (
            <div className="grid gap-8 lg:grid-cols-5">
              {/* Left: Preview (3 cols) */}
              <div className="lg:col-span-3">
                <CalibrationView resume={resume} />
              </div>

              {/* Right: Controls (2 cols) */}
              <div className="space-y-6 lg:col-span-2">
                {/* Strength of change */}
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                    Enhancement Strength
                  </h3>
                  <div className="space-y-1.5">
                    {STRENGTH_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => setStrength(opt.value)}
                        className={cn(
                          "w-full rounded-md border px-3 py-2 text-left text-sm transition-colors",
                          strength === opt.value
                            ? "border-primary bg-primary/5 font-medium"
                            : "border-border hover:bg-muted"
                        )}
                      >
                        <span className="block">{opt.label}</span>
                        <span className="block text-xs text-muted-foreground">
                          {opt.description}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                <StyleFeedback
                  value={styleFeedback}
                  onChange={setStyleFeedback}
                />

                <button
                  onClick={handleRegenerate}
                  disabled={generating}
                  className="w-full rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:opacity-50"
                >
                  {generating ? "Regenerating..." : "Regenerate Preview"}
                </button>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed p-8 text-center">
              <p className="text-muted-foreground">
                No resume preview available. Please go back to the analysis step
                and ensure entries are selected.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Approval Bar */}
      <GateApprovalBar
        onApprove={handleApprove}
        loading={approving}
        disabled={!resume || generating}
        label="Approve & Generate Full Resume"
      />
    </div>
  );
}
