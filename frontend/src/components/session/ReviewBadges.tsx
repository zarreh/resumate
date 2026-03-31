"use client";

import { cn } from "@/lib/utils";
import type { ReviewAnnotation } from "@/types/session";

interface ReviewBadgesProps {
  annotations: ReviewAnnotation[];
}

const RATING_STYLES = {
  strong: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  adequate:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  weak: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
} as const;

const PERSPECTIVE_LABELS = {
  recruiter: "Recruiter",
  hiring_manager: "Hiring Mgr",
} as const;

export function ReviewBadges({ annotations }: ReviewBadgesProps) {
  if (annotations.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {annotations.map((ann, idx) => (
        <span
          key={`${ann.perspective}-${idx}`}
          title={ann.comment}
          className={cn(
            "inline-flex cursor-help items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium",
            RATING_STYLES[ann.rating]
          )}
        >
          <span>{PERSPECTIVE_LABELS[ann.perspective]}</span>
          <span className="opacity-60">|</span>
          <span className="capitalize">{ann.rating}</span>
        </span>
      ))}
    </div>
  );
}
