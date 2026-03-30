"use client";

import { useRef, useState } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { uploadResume } from "@/lib/api/career";

interface ImportDialogProps {
  open: boolean;
  onClose: () => void;
  onImported: (text: string) => void;
}

const ACCEPTED = ".pdf,.docx,.txt";

export function ImportDialog({ open, onClose, onImported }: ImportDialogProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [filename, setFilename] = useState("");

  async function handleFile(file: File) {
    setUploading(true);
    setError("");
    setFilename(file.name);

    try {
      const result = await uploadResume(file);
      onImported(result.text);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Import Resume</DialogTitle>
        </DialogHeader>
        <div
          className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <Upload className="h-8 w-8 mx-auto mb-3 text-muted-foreground" />
          <p className="text-sm font-medium">
            {uploading
              ? `Uploading ${filename}...`
              : "Drop your resume here or click to browse"}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            PDF, DOCX, or TXT (max 10 MB)
          </p>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPTED}
          onChange={handleChange}
          className="hidden"
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex justify-end">
          <Button variant="ghost" onClick={onClose} disabled={uploading}>
            Cancel
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
