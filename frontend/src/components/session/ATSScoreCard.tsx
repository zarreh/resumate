"use client";

import { cn } from "@/lib/utils";
import type { ATSScore } from "@/types/session";

interface ATSScoreCardProps {
  score: ATSScore;
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span>{label}</span>
        <span className="font-medium">{Math.round(value)}%</span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div
          className={cn(
            "h-2 rounded-full transition-all",
            value >= 80
              ? "bg-green-500"
              : value >= 60
                ? "bg-yellow-500"
                : "bg-red-500"
          )}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  );
}

export function ATSScoreCard({ score }: ATSScoreCardProps) {
  return (
    <div className="space-y-4 rounded-lg border border-border bg-muted/30 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">ATS Compatibility Score</h3>
        <span
          className={cn(
            "text-2xl font-bold",
            score.overall_score >= 80
              ? "text-green-600"
              : score.overall_score >= 60
                ? "text-yellow-600"
                : "text-red-600"
          )}
        >
          {Math.round(score.overall_score)}
        </span>
      </div>

      <div className="space-y-2">
        <ScoreBar label="Keyword Match" value={score.keyword_score} />
        <ScoreBar label="Skills Coverage" value={score.skills_score} />
        <ScoreBar label="Format" value={score.format_score} />
      </div>

      {score.missing_keywords.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground">
            Missing Keywords
          </p>
          <div className="mt-1 flex flex-wrap gap-1">
            {score.missing_keywords.map((kw) => (
              <span
                key={kw}
                className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-medium text-red-700 dark:bg-red-900/30 dark:text-red-300"
              >
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {score.suggestions.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground">
            Suggestions
          </p>
          <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
            {score.suggestions.map((s, i) => (
              <li key={i} className="flex gap-1">
                <span className="text-muted-foreground/60">-</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
