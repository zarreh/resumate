"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle, Download, FileText, GitFork, Mail } from "lucide-react";
import { generateCoverLetter, getCoverLetter, getSession, completeSession, forkSession } from "@/lib/api/session";
import { getAccessToken } from "@/lib/api";
import type { CoverLetterResponse, EnhancedResume, SessionResponse } from "@/types/session";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function FinalPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [session, setSession] = useState<SessionResponse | null>(null);
  const [resume, setResume] = useState<EnhancedResume | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [coverLetter, setCoverLetter] = useState<CoverLetterResponse | null>(
    null
  );
  const [generatingCoverLetter, setGeneratingCoverLetter] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [forking, setForking] = useState(false);

  const fetchSession = useCallback(async () => {
    try {
      const data = await getSession(sessionId);
      setSession(data);
      if (data.enhanced_resume) {
        setResume(data.enhanced_resume);
      }
      // Load existing cover letter
      try {
        const cl = await getCoverLetter(sessionId);
        if (cl) setCoverLetter(cl);
      } catch {
        // Cover letter not found is fine
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

  const handleGenerateCoverLetter = async () => {
    setGeneratingCoverLetter(true);
    try {
      const result = await generateCoverLetter(sessionId);
      setCoverLetter(result);
      toast.success("Cover letter generated!");
    } catch {
      toast.error("Failed to generate cover letter");
    } finally {
      setGeneratingCoverLetter(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const token = getAccessToken();
      const resp = await fetch(
        `${API_URL}/api/v1/resumes/${sessionId}/pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!resp.ok) {
        const data = await resp.json().catch(() => null);
        throw new Error(data?.detail || "Failed to generate PDF");
      }

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "resume.pdf";
      a.click();
      URL.revokeObjectURL(url);

      toast.success("PDF downloaded successfully");
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : "Failed to download PDF"
      );
    } finally {
      setDownloading(false);
    }
  };

  const handleCompleteSession = async () => {
    setCompleting(true);
    try {
      await completeSession(sessionId);
      setCompleted(true);
      toast.success("Session completed! Your decisions are saved for future sessions.");
    } catch {
      toast.error("Failed to complete session");
    } finally {
      setCompleting(false);
    }
  };

  const handleFork = async () => {
    setForking(true);
    try {
      const newSession = await forkSession(sessionId);
      toast.success("Session forked — starting fresh tailoring");
      router.push(`/dashboard/sessions/${newSession.id}/analysis`);
    } catch {
      toast.error("Failed to fork session");
    } finally {
      setForking(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (!session || !resume) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">
          No finalized resume available. Complete the review step first.
        </p>
      </div>
    );
  }

  const totalBullets = resume.sections.reduce(
    (acc, s) => acc + s.entries.reduce((a, e) => a + e.bullets.length, 0),
    0
  );

  return (
    <div className="mx-auto max-w-3xl space-y-8 p-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold">Your Resume is Ready</h1>
        <p className="text-muted-foreground">
          Download your tailored resume as a PDF.
        </p>
      </div>

      {/* Stats */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Resume Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold">{resume.sections.length}</p>
              <p className="text-sm text-muted-foreground">Sections</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{totalBullets}</p>
              <p className="text-sm text-muted-foreground">Bullets</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{resume.skills.length}</p>
              <p className="text-sm text-muted-foreground">Skills</p>
            </div>
          </div>

          <div className="pt-2">
            <p className="text-sm font-medium">Professional Summary</p>
            <p className="text-sm text-muted-foreground">{resume.summary}</p>
          </div>
        </CardContent>
      </Card>

      {/* Download */}
      <div className="flex flex-col items-center gap-4">
        <Button
          size="lg"
          onClick={handleDownload}
          disabled={downloading}
          className="gap-2"
        >
          {downloading ? (
            <>Generating PDF...</>
          ) : (
            <>
              <Download className="h-5 w-5" />
              Download PDF
            </>
          )}
        </Button>

        <p className="flex items-center gap-1 text-xs text-muted-foreground">
          <FileText className="h-3 w-3" />
          ATS-friendly professional template
        </p>
      </div>

      {/* Cover Letter */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Mail className="h-4 w-4" />
              Cover Letter
            </CardTitle>
            <Button
              size="sm"
              variant={coverLetter ? "outline" : "default"}
              onClick={handleGenerateCoverLetter}
              disabled={generatingCoverLetter}
            >
              {generatingCoverLetter
                ? "Generating..."
                : coverLetter
                  ? "Regenerate"
                  : "Generate Cover Letter"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {coverLetter ? (
            <div className="whitespace-pre-wrap text-sm leading-relaxed">
              {coverLetter.content}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Generate a personalized cover letter based on your tailored resume
              and the job description.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Complete Session */}
      <Card>
        <CardContent className="flex flex-col items-center gap-3 pt-6">
          {completed ? (
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-5 w-5" />
              <span className="font-medium">
                Session completed — your preferences are saved for future sessions
              </span>
            </div>
          ) : (
            <>
              <p className="text-center text-sm text-muted-foreground">
                Mark this session as complete to save your decisions. Future
                sessions for similar roles will learn from your preferences.
              </p>
              <Button
                variant="outline"
                onClick={handleCompleteSession}
                disabled={completing}
                className="gap-2"
              >
                {completing ? (
                  "Saving..."
                ) : (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    Complete Session
                  </>
                )}
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {/* Fork Session */}
      <Card>
        <CardContent className="flex flex-col items-center gap-3 pt-6">
          <p className="text-center text-sm text-muted-foreground">
            Want to refine this resume? Fork it as a new session to start
            from the same job description and selections.
          </p>
          <Button
            variant="outline"
            onClick={handleFork}
            disabled={forking}
            className="gap-2"
          >
            {forking ? (
              "Forking..."
            ) : (
              <>
                <GitFork className="h-4 w-4" />
                Fork as New Session
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
