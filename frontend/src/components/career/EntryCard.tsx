"use client";

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TagBadge } from "@/components/career/TagBadge";
import { entryTypeLabel } from "@/types/career";
import type { CareerEntry } from "@/types/career";

interface EntryCardProps {
  entry: CareerEntry;
  onEdit: (entry: CareerEntry) => void;
  onDelete: (id: string) => void;
}

function formatDateRange(start: string | null, end: string | null): string {
  if (!start && !end) return "";
  const s = start ?? "?";
  const e = end ?? "Present";
  return `${s} — ${e}`;
}

export function EntryCard({ entry, onEdit, onDelete }: EntryCardProps) {
  const [confirming, setConfirming] = useState(false);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1">
            <CardTitle className="text-base">{entry.title}</CardTitle>
            {entry.organization && (
              <p className="text-sm text-muted-foreground">
                {entry.organization}
              </p>
            )}
            {(entry.start_date || entry.end_date) && (
              <p className="text-xs text-muted-foreground">
                {formatDateRange(entry.start_date, entry.end_date)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-1">
            <Badge variant="outline" className="text-xs whitespace-nowrap">
              {entryTypeLabel(entry.entry_type)}
            </Badge>
            {entry.source === "parsed_resume" && (
              <Badge variant="secondary" className="text-xs">
                Parsed
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {entry.bullet_points.length > 0 && (
          <ul className="space-y-1 text-sm">
            {entry.bullet_points.map((bp, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-muted-foreground mt-0.5">•</span>
                <span>{bp}</span>
              </li>
            ))}
          </ul>
        )}
        {entry.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {entry.tags.map((tag) => (
              <TagBadge key={tag} tag={tag} />
            ))}
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2 border-t">
          <Button variant="ghost" size="sm" onClick={() => onEdit(entry)}>
            <Pencil className="h-3.5 w-3.5 mr-1" />
            Edit
          </Button>
          {confirming ? (
            <div className="flex gap-1">
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  onDelete(entry.id);
                  setConfirming(false);
                }}
              >
                Confirm
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setConfirming(false)}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setConfirming(true)}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              Delete
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
