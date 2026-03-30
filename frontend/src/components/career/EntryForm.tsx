"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ENTRY_TYPES } from "@/types/career";
import type { CareerEntry, CareerEntryCreate, CareerEntryUpdate } from "@/types/career";

interface EntryFormProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: CareerEntryCreate | CareerEntryUpdate) => Promise<void>;
  entry?: CareerEntry | null;
}

export function EntryForm({ open, onClose, onSave, entry }: EntryFormProps) {
  const isEdit = !!entry;
  const [entryType, setEntryType] = useState(entry?.entry_type ?? "work_experience");
  const [title, setTitle] = useState(entry?.title ?? "");
  const [organization, setOrganization] = useState(entry?.organization ?? "");
  const [startDate, setStartDate] = useState(entry?.start_date ?? "");
  const [endDate, setEndDate] = useState(entry?.end_date ?? "");
  const [bulletText, setBulletText] = useState(
    entry?.bullet_points.join("\n") ?? "",
  );
  const [tagsText, setTagsText] = useState(entry?.tags.join(", ") ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setError("Title is required");
      return;
    }

    setSaving(true);
    setError("");

    const bullets = bulletText
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    const tags = tagsText
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    const data = {
      entry_type: entryType,
      title: title.trim(),
      organization: organization.trim() || null,
      start_date: startDate.trim() || null,
      end_date: endDate.trim() || null,
      bullet_points: bullets,
      tags,
    };

    try {
      await onSave(data);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Edit Entry" : "Add Career Entry"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="entry_type">Type</Label>
            <select
              id="entry_type"
              value={entryType}
              onChange={(e) => setEntryType(e.target.value)}
              className="w-full mt-1 rounded-md border px-3 py-2 text-sm bg-background"
            >
              {ENTRY_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Senior Software Engineer"
            />
          </div>
          <div>
            <Label htmlFor="organization">Organization</Label>
            <Input
              id="organization"
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
              placeholder="e.g., Acme Corp"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="start_date">Start Date</Label>
              <Input
                id="start_date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                placeholder="YYYY or YYYY-MM"
              />
            </div>
            <div>
              <Label htmlFor="end_date">End Date</Label>
              <Input
                id="end_date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                placeholder="YYYY or YYYY-MM"
              />
            </div>
          </div>
          <div>
            <Label htmlFor="bullets">
              Bullet Points (one per line)
            </Label>
            <Textarea
              id="bullets"
              value={bulletText}
              onChange={(e) => setBulletText(e.target.value)}
              rows={4}
              placeholder="Built scalable APIs&#10;Led migration to microservices"
            />
          </div>
          <div>
            <Label htmlFor="tags">Tags (comma-separated)</Label>
            <Input
              id="tags"
              value={tagsText}
              onChange={(e) => setTagsText(e.target.value)}
              placeholder="Python, FastAPI, AWS"
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : isEdit ? "Update" : "Create"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
