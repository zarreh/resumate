"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { GitFork, Plus, Eye, Building2, Briefcase } from "lucide-react";
import { listSessions, forkSession } from "@/lib/api/session";
import type { SessionListItem } from "@/types/session";

const GATE_LABELS: Record<string, string> = {
  analysis: "Analysis",
  calibration: "Calibration",
  review: "Review",
  final: "Final",
};

const GATE_COLORS: Record<string, string> = {
  analysis: "bg-blue-100 text-blue-800",
  calibration: "bg-yellow-100 text-yellow-800",
  review: "bg-purple-100 text-purple-800",
  final: "bg-green-100 text-green-800",
};

export default function SessionsPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [forkingId, setForkingId] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await listSessions();
      setSessions(data);
    } catch {
      toast.error("Failed to load sessions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleFork = async (sessionId: string) => {
    setForkingId(sessionId);
    try {
      const newSession = await forkSession(sessionId);
      toast.success("Session forked successfully");
      router.push(`/sessions/${newSession.id}/analysis`);
    } catch {
      toast.error("Failed to fork session");
    } finally {
      setForkingId(null);
    }
  };

  const formatDate = (iso: string) => {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Sessions</h1>
          <p className="text-muted-foreground">
            Manage your resume tailoring sessions.
          </p>
        </div>
        <Button onClick={() => router.push("/sessions/new")}>
          <Plus className="mr-2 h-4 w-4" />
          New Session
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading sessions...</p>
        </div>
      ) : sessions.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <p className="text-muted-foreground">
            No sessions yet. Start a new session by pasting a job description.
          </p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => router.push("/sessions/new")}
          >
            <Plus className="mr-2 h-4 w-4" />
            Start New Session
          </Button>
        </div>
      ) : (
        <div className="grid gap-4">
          {sessions.map((s) => (
            <Card key={s.id} className="transition-colors hover:bg-muted/50">
              <CardContent className="flex items-center justify-between p-5">
                <div className="min-w-0 flex-1 space-y-1">
                  {/* Title line */}
                  <div className="flex items-center gap-2">
                    <span className="truncate font-medium">
                      {s.role_title || "Untitled Role"}
                    </span>
                    <Badge
                      variant="outline"
                      className={GATE_COLORS[s.current_gate] || ""}
                    >
                      {GATE_LABELS[s.current_gate] || s.current_gate}
                    </Badge>
                    {s.has_resume && (
                      <Badge variant="secondary" className="text-xs">
                        Resume Ready
                      </Badge>
                    )}
                  </div>

                  {/* Meta line */}
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    {s.company_name && (
                      <span className="flex items-center gap-1">
                        <Building2 className="h-3 w-3" />
                        {s.company_name}
                      </span>
                    )}
                    {s.industry && (
                      <span className="flex items-center gap-1">
                        <Briefcase className="h-3 w-3" />
                        {s.industry}
                      </span>
                    )}
                    {s.seniority_level && (
                      <span className="capitalize">{s.seniority_level}</span>
                    )}
                    <span>{formatDate(s.created_at)}</span>
                  </div>

                  {/* Fork indicator */}
                  {s.forked_from_id && (
                    <p className="text-xs text-muted-foreground">
                      <GitFork className="mr-1 inline h-3 w-3" />
                      Forked from a previous session
                    </p>
                  )}
                </div>

                {/* Actions */}
                <div className="ml-4 flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      router.push(`/sessions/${s.id}`)
                    }
                    className="gap-1"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    View
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleFork(s.id)}
                    disabled={forkingId === s.id}
                    className="gap-1"
                  >
                    <GitFork className="h-3.5 w-3.5" />
                    {forkingId === s.id ? "Forking..." : "Fork"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
