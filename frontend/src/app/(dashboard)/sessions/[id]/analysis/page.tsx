"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { AnalysisView } from "@/components/session/AnalysisView";
import { ContextInput } from "@/components/session/ContextInput";
import { EntryToggle } from "@/components/session/EntryToggle";
import { GateApprovalBar } from "@/components/session/GateApprovalBar";
import { MatchOverview } from "@/components/session/MatchOverview";
import { approveGate, getMatch, getSession } from "@/lib/api/session";
import type { MatchResponse, SessionResponse } from "@/types/session";

export default function AnalysisPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [session, setSession] = useState<SessionResponse | null>(null);
  const [matchData, setMatchData] = useState<MatchResponse | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [contextText, setContextText] = useState("");
  const [loading, setLoading] = useState(true);
  const [matchLoading, setMatchLoading] = useState(false);
  const [approving, setApproving] = useState(false);

  // Fetch session data
  const fetchSession = useCallback(async () => {
    try {
      const data = await getSession(sessionId);
      setSession(data);

      // Pre-populate selected entries from session
      if (data.selected_entry_ids.length > 0) {
        setSelectedIds(new Set(data.selected_entry_ids));
      }
      if (data.context_text) {
        setContextText(data.context_text);
      }
    } catch {
      toast.error("Failed to load session");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Fetch match data
  const fetchMatch = useCallback(async () => {
    setMatchLoading(true);
    try {
      const data = await getMatch(sessionId);
      setMatchData(data);

      // Auto-select all entries initially if none selected
      if (data.ranked_entries.length > 0 && selectedIds.size === 0) {
        setSelectedIds(
          new Set(data.ranked_entries.map((e) => e.entry_id))
        );
      }
    } catch {
      // Match may fail if no entries or embeddings - that's okay
      setMatchData(null);
    } finally {
      setMatchLoading(false);
    }
  }, [sessionId, selectedIds.size]);

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  useEffect(() => {
    if (session) {
      fetchMatch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.id]);

  const handleToggle = (entryId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(entryId)) {
        next.delete(entryId);
      } else {
        next.add(entryId);
      }
      return next;
    });
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      await approveGate(
        sessionId,
        "analysis",
        Array.from(selectedIds),
        contextText || undefined
      );
      toast.success("Analysis approved! Moving to calibration...");
      router.push(`/sessions/${sessionId}/calibration`);
    } catch {
      toast.error("Failed to approve analysis");
    } finally {
      setApproving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Loading analysis...</p>
      </div>
    );
  }

  if (!session || !session.analysis) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">No analysis available.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-5xl space-y-8">
          {/* Page Header */}
          <div>
            <h1 className="text-2xl font-bold">JD Analysis</h1>
            <p className="text-muted-foreground">
              Review the analysis, select relevant entries, and approve to
              continue.
            </p>
          </div>

          <div className="grid gap-8 lg:grid-cols-2">
            {/* Left column: Analysis */}
            <div className="space-y-6">
              <AnalysisView analysis={session.analysis} companyResearch={session.company_research} />
            </div>

            {/* Right column: Match + Entries */}
            <div className="space-y-6">
              {/* Match Overview */}
              {matchLoading ? (
                <div className="flex items-center justify-center py-8">
                  <p className="text-sm text-muted-foreground">
                    Computing match scores...
                  </p>
                </div>
              ) : matchData ? (
                <MatchOverview matchResult={matchData.match_result} />
              ) : (
                <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                  No career entries found for matching. Add entries in your
                  Career History first.
                </div>
              )}

              {/* Entry Selection */}
              {matchData && matchData.ranked_entries.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                    Select Entries to Include
                  </h3>
                  <EntryToggle
                    entries={matchData.ranked_entries}
                    selectedIds={selectedIds}
                    onToggle={handleToggle}
                  />
                </div>
              )}

              {/* Context Input */}
              <ContextInput value={contextText} onChange={setContextText} />
            </div>
          </div>
        </div>
      </div>

      {/* Approval Bar */}
      <GateApprovalBar
        onApprove={handleApprove}
        loading={approving}
        disabled={selectedIds.size === 0 && !matchLoading}
      />
    </div>
  );
}
