"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { BulletDiff, type DiffMode } from "@/components/session/BulletDiff";
import { ReviewBadges } from "@/components/session/ReviewBadges";
import type { EnhancedBullet, ReviewAnnotation } from "@/types/session";

interface BulletCardProps {
  bullet: EnhancedBullet;
  status?: "pending" | "approved" | "rejected";
  annotations?: ReviewAnnotation[];
  diffMode?: DiffMode;
  onApprove?: () => void;
  onReject?: () => void;
  onEdit?: (text: string) => void;
  showControls?: boolean;
}

export function BulletCard({
  bullet,
  status = "pending",
  annotations = [],
  diffMode = "unified",
  onApprove,
  onReject,
  onEdit,
  showControls = false,
}: BulletCardProps) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(bullet.enhanced_text);

  const handleSave = () => {
    if (onEdit && editText.trim()) {
      onEdit(editText.trim());
    }
    setEditing(false);
  };

  const handleCancel = () => {
    setEditText(bullet.enhanced_text);
    setEditing(false);
  };

  return (
    <div
      className={cn(
        "rounded-lg border p-4 transition-colors",
        status === "approved" && "border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-900/10",
        status === "rejected" && "border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-900/10",
        status === "pending" && "border-border"
      )}
    >
      {editing ? (
        <div className="space-y-2">
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            rows={3}
            autoFocus
          />
          <div className="flex items-center gap-2">
            <button
              onClick={handleSave}
              className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-green-700"
            >
              Save
            </button>
            <button
              onClick={handleCancel}
              className="rounded bg-muted px-3 py-1 text-xs font-medium transition-colors hover:bg-muted/80"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <BulletDiff
          original={bullet.original_text}
          enhanced={bullet.enhanced_text}
          mode={diffMode}
        />
      )}

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

        {showControls && !editing && (
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
                onClick={() => {
                  setEditText(bullet.enhanced_text);
                  setEditing(true);
                }}
                className="rounded bg-muted px-3 py-1 text-xs font-medium transition-colors hover:bg-muted/80"
              >
                Edit
              </button>
            )}
          </div>
        )}
      </div>

      <ReviewBadges annotations={annotations} />
    </div>
  );
}
