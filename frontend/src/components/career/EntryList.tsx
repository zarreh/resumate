"use client";

import { EntryCard } from "@/components/career/EntryCard";
import type { CareerEntry } from "@/types/career";

interface EntryListProps {
  entries: CareerEntry[];
  onEdit: (entry: CareerEntry) => void;
  onDelete: (id: string) => void;
}

export function EntryList({ entries, onEdit, onDelete }: EntryListProps) {
  if (entries.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p className="text-lg font-medium">No career entries yet</p>
        <p className="text-sm mt-1">
          Import a resume or add entries manually to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {entries.map((entry) => (
        <EntryCard
          key={entry.id}
          entry={entry}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
