"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Link2, FileText } from "lucide-react";

type InputMode = "text" | "url";

interface JDInputProps {
  onSubmit: (params: { text?: string; url?: string }) => void;
  loading?: boolean;
}

export function JDInput({ onSubmit, loading = false }: JDInputProps) {
  const [mode, setMode] = useState<InputMode>("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");

  const handleSubmit = () => {
    if (mode === "text") {
      const trimmed = text.trim();
      if (trimmed) onSubmit({ text: trimmed });
    } else {
      const trimmed = url.trim();
      if (trimmed) onSubmit({ url: trimmed });
    }
  };

  const isValid =
    mode === "text" ? text.trim().length > 0 : url.trim().length > 0;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Job Description</h2>
        <p className="text-sm text-muted-foreground">
          Paste the full job description text or provide a URL to start a new
          tailoring session.
        </p>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-1 rounded-md border border-border p-1 w-fit">
        <button
          type="button"
          onClick={() => setMode("text")}
          className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-sm font-medium transition-colors ${
            mode === "text"
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
          disabled={loading}
        >
          <FileText className="h-3.5 w-3.5" />
          Paste Text
        </button>
        <button
          type="button"
          onClick={() => setMode("url")}
          className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-sm font-medium transition-colors ${
            mode === "url"
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
          disabled={loading}
        >
          <Link2 className="h-3.5 w-3.5" />
          From URL
        </button>
      </div>

      {mode === "text" ? (
        <Textarea
          placeholder="Paste the job description here..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={12}
          className="font-mono text-sm"
          disabled={loading}
        />
      ) : (
        <Input
          type="url"
          placeholder="https://www.example.com/jobs/software-engineer"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={loading}
        />
      )}

      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          {mode === "text" && text.length > 0 ? `${text.length} characters` : ""}
          {mode === "url" && url.length > 0 ? "URL provided" : ""}
        </span>
        <Button onClick={handleSubmit} disabled={!isValid || loading} size="lg">
          {loading ? "Analyzing..." : "Analyze Job Description"}
        </Button>
      </div>
    </div>
  );
}
