"use client";

import { cn } from "@/lib/utils";
import { BulletDiff } from "@/components/session/BulletDiff";
import type { EnhancedBullet } from "@/types/session";

interface BulletCardProps {
  bullet: EnhancedBullet;
  status?: "pending" | "approved" | "rejected";
  onApprove?: () => void;
  onReject?: () => void;
  onEdit?: (text: string) => void;
  showControls?: boolean;
}

export function BulletCard({
  bullet,
  status = "pending",
  onApprove,
  onReject,
  onEdit,
  showControls = false,
}: BulletCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border p-4 transition-colors",
        status === "approved" && "border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-900/10",
        status === "rejected" && "border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-900/10",
        status === "pending" && "border-border"
      )}
    >
      <BulletDiff
        original={bullet.original_text}
        enhanced={bullet.enhanced_text}
      />

      <div className="mt-3 flex items-center justify-between">
        <span
          className={cn(
            "text-xs font-medium",
            bullet.relevance_score >= 0.8
              ? "text-green-600"
              : bullet.relevance_score >= 0.5
                ? "text-yellow-600"
                : "text-muted-foreground"
          )}
        >
          Relevance: {Math.round(bullet.relevance_score * 100)}%
        </span>

        {showControls && (
          <div className="flex items-center gap-2">
            <button
              onClick={onApprove}
              className={cn(
                "rounded px-3 py-1 text-xs font-medium transition-colors",
                status === "approved"
                  ? "bg-green-600 text-white"
                  : "bg-muted hover:bg-green-100 dark:hover:bg-green-900/30"
              )}
            >
              Approve
            </button>
            <button
              onClick={onReject}
              className={cn(
                "rounded px-3 py-1 text-xs font-medium transition-colors",
                status === "rejected"
                  ? "bg-red-600 text-white"
                  : "bg-muted hover:bg-red-100 dark:hover:bg-red-900/30"
              )}
            >
              Reject
            </button>
            {onEdit && (
              <button
                onClick={() => onEdit(bullet.enhanced_text)}
                className="rounded bg-muted px-3 py-1 text-xs font-medium transition-colors hover:bg-muted/80"
              >
                Edit
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
