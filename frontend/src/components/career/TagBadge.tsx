"use client";

import { Badge } from "@/components/ui/badge";

interface TagBadgeProps {
  tag: string;
  onRemove?: () => void;
}

export function TagBadge({ tag, onRemove }: TagBadgeProps) {
  return (
    <Badge variant="secondary" className="text-xs">
      {tag}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="ml-1 hover:text-destructive"
          aria-label={`Remove ${tag}`}
        >
          &times;
        </button>
      )}
    </Badge>
  );
}
