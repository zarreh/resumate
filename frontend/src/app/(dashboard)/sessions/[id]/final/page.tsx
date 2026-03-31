"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Download, FileText } from "lucide-react";
import { getSession } from "@/lib/api/session";
import { getAccessToken } from "@/lib/api";
import type { EnhancedResume, SessionResponse } from "@/types/session";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function FinalPage() {
  const params = useParams();
  const sessionId = params.id as string;

  const [session, setSession] = useState<SessionResponse | null>(null);
  const [resume, setResume] = useState<EnhancedResume | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  const fetchSession = useCallback(async () => {
    try {
      const data = await getSession(sessionId);
      setSession(data);
      if (data.enhanced_resume) {
        setResume(data.enhanced_resume);
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
    </div>
  );
}
