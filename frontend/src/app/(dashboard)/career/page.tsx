"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, Upload, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EntryList } from "@/components/career/EntryList";
import { EntryForm } from "@/components/career/EntryForm";
import { ImportDialog } from "@/components/career/ImportDialog";
import {
  listEntries,
  createEntry,
  updateEntry,
  deleteEntry,
  confirmAllEntries,
  parseResume,
} from "@/lib/api/career";
import type {
  CareerEntry,
  CareerEntryCreate,
  CareerEntryUpdate,
} from "@/types/career";
import { toast } from "sonner";

export default function CareerPage() {
  const [entries, setEntries] = useState<CareerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [editEntry, setEditEntry] = useState<CareerEntry | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showImport, setShowImport] = useState(false);

  const fetchEntries = useCallback(async () => {
    try {
      const data = await listEntries();
      setEntries(data);
    } catch {
      toast.error("Failed to load career entries");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  async function handleCreate(data: CareerEntryCreate | CareerEntryUpdate) {
    await createEntry(data as CareerEntryCreate);
    toast.success("Entry created");
    fetchEntries();
  }

  async function handleUpdate(data: CareerEntryCreate | CareerEntryUpdate) {
    if (!editEntry) return;
    await updateEntry(editEntry.id, data as CareerEntryUpdate);
    toast.success("Entry updated");
    setEditEntry(null);
    fetchEntries();
  }

  async function handleDelete(id: string) {
    try {
      await deleteEntry(id);
      toast.success("Entry deleted");
      fetchEntries();
    } catch {
      toast.error("Failed to delete entry");
    }
  }

  async function handleConfirmAll() {
    try {
      const result = await confirmAllEntries();
      if (result.confirmed > 0) {
        toast.success(`Confirmed ${result.confirmed} entries`);
        fetchEntries();
      } else {
        toast.info("No entries to confirm");
      }
    } catch {
      toast.error("Failed to confirm entries");
    }
  }

  async function handleImported(text: string) {
    toast.loading("Parsing resume with AI...", { id: "parse" });
    try {
      const parsed = await parseResume(text);
      await Promise.all(
        parsed.entries.map((e) =>
          createEntry({
            entry_type: e.entry_type,
            title: e.title,
            organization: e.organization,
            start_date: e.start_date,
            end_date: e.end_date,
            bullet_points: e.bullet_points.map((b) => b.text),
            tags: e.tags,
            raw_text: e.raw_text,
          })
        )
      );
      toast.success(`Imported ${parsed.entry_count} entries`, { id: "parse" });
      fetchEntries();
    } catch {
      toast.error("Failed to parse resume", { id: "parse" });
    }
  }

  const hasParsedEntries = entries.some((e) => e.source === "parsed_resume");

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Career History</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {entries.length} {entries.length === 1 ? "entry" : "entries"}
          </p>
        </div>
        <div className="flex gap-2">
          {hasParsedEntries && (
            <Button variant="outline" size="sm" onClick={handleConfirmAll}>
              <CheckCircle className="h-4 w-4 mr-1" />
              Confirm All
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => setShowImport(true)}>
            <Upload className="h-4 w-4 mr-1" />
            Import
          </Button>
          <Button size="sm" onClick={() => setShowForm(true)}>
            <Plus className="h-4 w-4 mr-1" />
            Add Entry
          </Button>
        </div>
      </div>

      <EntryList
        entries={entries}
        onEdit={(entry) => {
          setEditEntry(entry);
          setShowForm(true);
        }}
        onDelete={handleDelete}
      />

      <EntryForm
        open={showForm}
        onClose={() => {
          setShowForm(false);
          setEditEntry(null);
        }}
        onSave={editEntry ? handleUpdate : handleCreate}
        entry={editEntry}
      />

      <ImportDialog
        open={showImport}
        onClose={() => setShowImport(false)}
        onImported={handleImported}
      />
    </div>
  );
}
