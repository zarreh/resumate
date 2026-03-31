"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { entryTypeLabel } from "@/types/career";
import type { RankedEntry } from "@/types/session";

interface EntryToggleProps {
  entries: RankedEntry[];
  selectedIds: Set<string>;
  onToggle: (entryId: string) => void;
}

export function EntryToggle({
  entries,
  selectedIds,
  onToggle,
}: EntryToggleProps) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No matching career entries found. Add more entries in your career history
        to improve matching.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {entries.map((entry) => {
        const isSelected = selectedIds.has(entry.entry_id);
        return (
          <Card
            key={entry.entry_id}
            className={`cursor-pointer p-3 transition-colors ${
              isSelected
                ? "border-primary bg-primary/5"
                : "opacity-60 hover:opacity-80"
            }`}
            onClick={() => onToggle(entry.entry_id)}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => onToggle(entry.entry_id)}
                    className="h-4 w-4 rounded border-input"
                    onClick={(e) => e.stopPropagation()}
                  />
                  <span className="font-medium">{entry.title}</span>
                  <Badge variant="outline" className="text-xs">
                    {entryTypeLabel(entry.entry_type)}
                  </Badge>
                </div>
                {entry.organization && (
                  <p className="mt-0.5 pl-6 text-sm text-muted-foreground">
                    {entry.organization}
                    {entry.start_date && ` \u2022 ${entry.start_date}`}
                    {entry.end_date && ` \u2013 ${entry.end_date}`}
                    {!entry.end_date && entry.start_date && " \u2013 Present"}
                  </p>
                )}
                {entry.tags.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1 pl-6">
                    {entry.tags.slice(0, 6).map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                    {entry.tags.length > 6 && (
                      <span className="text-xs text-muted-foreground">
                        +{entry.tags.length - 6} more
                      </span>
                    )}
                  </div>
                )}
              </div>
              <span className="flex-shrink-0 font-mono text-sm text-muted-foreground">
                {Math.round(entry.similarity_score * 100)}%
              </span>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
