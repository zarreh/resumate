"use client";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { MatchResult } from "@/types/session";

interface MatchOverviewProps {
  matchResult: MatchResult;
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const color =
    score >= 75
      ? "bg-green-500"
      : score >= 50
        ? "bg-yellow-500"
        : "bg-red-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span>{label}</span>
        <span className="font-mono font-semibold">{score}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
    </div>
  );
}

export function MatchOverview({ matchResult }: MatchOverviewProps) {
  const gap = matchResult.gap_analysis;
  const hasGaps =
    gap.unmatched_required.length > 0 ||
    gap.unmatched_preferred.length > 0 ||
    gap.missing_tech.length > 0;

  return (
    <div className="space-y-6">
      {/* Overall Score */}
      <Card className="p-6">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-full border-4 border-primary text-xl font-bold">
            {Math.round(matchResult.overall_score)}
          </div>
          <div>
            <h3 className="text-lg font-semibold">Match Score</h3>
            <p className="text-sm text-muted-foreground">
              Based on your career history entries
            </p>
          </div>
        </div>
      </Card>

      {/* Score Breakdown */}
      <Card className="space-y-4 p-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Score Breakdown
        </h3>
        <ScoreBar
          label="Required Skills"
          score={matchResult.required_skills_score}
        />
        <ScoreBar
          label="Tech Stack"
          score={matchResult.tech_stack_score}
        />
        <ScoreBar
          label="Preferred Skills"
          score={matchResult.preferred_skills_score}
        />
      </Card>

      {/* Gap Analysis */}
      {hasGaps && (
        <Card className="p-4">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Gaps Identified
          </h3>
          <div className="space-y-3">
            {gap.unmatched_required.length > 0 && (
              <div>
                <p className="mb-1 text-sm font-medium text-destructive">
                  Missing Required Skills
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {gap.unmatched_required.map((s) => (
                    <Badge key={s} variant="destructive">
                      {s}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {gap.missing_tech.length > 0 && (
              <div>
                <p className="mb-1 text-sm font-medium text-orange-600 dark:text-orange-400">
                  Missing Tech Stack
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {gap.missing_tech.map((t) => (
                    <Badge key={t} variant="outline">
                      {t}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {gap.unmatched_preferred.length > 0 && (
              <div>
                <p className="mb-1 text-sm font-medium text-muted-foreground">
                  Missing Preferred Skills
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {gap.unmatched_preferred.map((s) => (
                    <Badge key={s} variant="secondary">
                      {s}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Recommended Section Order */}
      {matchResult.recommended_section_order.length > 0 && (
        <Card className="p-4">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Recommended Resume Sections
          </h3>
          <ol className="list-inside list-decimal space-y-1 text-sm capitalize">
            {matchResult.recommended_section_order.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}
